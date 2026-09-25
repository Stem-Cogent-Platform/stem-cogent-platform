"""Build and roll out the regulatory engine exclusively in the staging account."""
from __future__ import annotations

import argparse
import base64
import copy
import json
import subprocess
from pathlib import Path

import boto3

from app.ops.regulatory_gap_staging import ACCOUNT, CLUSTER

ROOT = Path(__file__).resolve().parents[3]
BUCKET = 'sc-enterprise-uploads-staging-437040615141'


def clients():
    session = boto3.Session(profile_name='staging',region_name='eu-west-1')
    if session.client('sts').get_caller_identity()['Account'] != ACCOUNT:
        raise RuntimeError('Wrong AWS account: refusing release')
    return session


def discover(session):
    ecs = session.client('ecs')
    arns = []
    for page in ecs.get_paginator('list_services').paginate(cluster=CLUSTER):
        arns.extend(page['serviceArns'])
    result = {}
    for offset in range(0,len(arns),10):
        services = ecs.describe_services(cluster=CLUSTER,services=arns[offset:offset+10])['services']
        for service in services:
            name = service['serviceName']
            kind = next((kind for kind,part in [('api','api-service'),('worker','normalization'),('scheduler','scheduler'),('frontend','frontend')] if part in name),None)
            if kind:
                definition = ecs.describe_task_definition(taskDefinition=service['taskDefinition'])['taskDefinition']
                main = next(c for c in definition['containerDefinitions'] if c['name'] != 'xray-daemon')
                result[kind] = {'service':name,'definition':definition,'container':main['name'],
                                'image':main['image'],'previous_definition':definition['taskDefinitionArn']}
    if set(result) != {'api','worker','scheduler','frontend'}:
        raise RuntimeError('Required staging services not found')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=['discover','configure','prepare','deploy'])
    parser.add_argument('--tag',default='regulatory-gap-20260925-v1')
    parser.add_argument('--manifest',type=Path,default=ROOT/'scratch/regulatory-gap-release.json')
    args = parser.parse_args()
    session = clients()
    ecs = session.client('ecs')
    services = discover(session)
    if args.action == 'discover':
        s3 = session.client('s3')
        report = {'services':{key:{'service':value['service'],'image':value['image'],
                   'role':value['definition']['taskRoleArn'],
                   'platform':value['definition'].get('runtimePlatform')} for key,value in services.items()},
                  'bucket_encryption':s3.get_bucket_encryption(Bucket=BUCKET)['ServerSideEncryptionConfiguration'],
                  'bucket_public_access':s3.get_public_access_block(Bucket=BUCKET)['PublicAccessBlockConfiguration'],
                  'bucket_versioning':s3.get_bucket_versioning(Bucket=BUCKET).get('Status')}
        path = ROOT/'scratch/regulatory-gap-infrastructure.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2))
        return
    if args.action == 'deploy':
        manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
        if manifest['account'] != ACCOUNT:
            raise RuntimeError('Release manifest account mismatch')
        for key,value in manifest['services'].items():
            if value['service'] != services[key]['service'] or f':{ACCOUNT}:' not in value['task_definition']:
                raise RuntimeError('Release manifest scope mismatch')
            ecs.update_service(cluster=CLUSTER,service=value['service'],taskDefinition=value['task_definition'])
            print(f"Deployed {key}: {value['task_definition']}",flush=True)
        return

    built = {kind: services[kind]['image'] for kind in ['api','worker','frontend']}
    if args.action == 'prepare':
        if not args.tag.replace('-','').replace('.','').isalnum():
            raise RuntimeError('Invalid image tag')
        auth = session.client('ecr').get_authorization_token()['authorizationData'][0]
        username,password = base64.b64decode(auth['authorizationToken']).decode().split(':',1)
        subprocess.run(['docker','login','--username',username,'--password-stdin',auth['proxyEndpoint']],
                       input=password,text=True,check=True)
        built = {}
        for kind in ['api','worker','frontend']:
            service = services[kind]
            repo = service['image'].split('@',1)[0].rsplit(':',1)[0]
            if not repo.startswith(f'{ACCOUNT}.dkr.ecr.eu-west-1.amazonaws.com/'):
                raise RuntimeError('Refusing non-staging registry')
            image = f'{repo}:{args.tag}'
            architecture = service['definition'].get('runtimePlatform',{}).get('cpuArchitecture','X86_64')
            platform = 'linux/arm64' if architecture == 'ARM64' else 'linux/amd64'
            dockerfile = {'api':'backend','worker':'worker','frontend':'frontend'}[kind]
            command = ['docker','build','--platform',platform,'-f',str(ROOT/f'infrastructure/docker/{dockerfile}.Dockerfile'),'-t',image]
            if kind == 'frontend':
                command.extend(['--build-arg','NEXT_PUBLIC_API_URL=https://api.staging.stem-cogent.com',
                                '--build-arg','NEXT_PUBLIC_WS_URL=wss://api.staging.stem-cogent.com'])
            command.append(str(ROOT/('frontend' if kind=='frontend' else 'backend')))
            print(f'Building {kind} {image}',flush=True)
            subprocess.run(command,check=True,cwd=ROOT)
            subprocess.run(['docker','push',image],check=True,cwd=ROOT)
            built[kind] = image

    encryption = session.client('s3').get_bucket_encryption(Bucket=BUCKET)
    kms_key = encryption['ServerSideEncryptionConfiguration']['Rules'][0]['ApplyServerSideEncryptionByDefault']['KMSMasterKeyID']
    manifest = {'account':ACCOUNT,'tag':args.tag,'services':{}}
    allowed = {'family','taskRoleArn','executionRoleArn','networkMode','containerDefinitions','volumes',
               'placementConstraints','requiresCompatibilities','cpu','memory','runtimePlatform','ephemeralStorage',
               'pidMode','ipcMode','proxyConfiguration'}
    for kind,value in services.items():
        definition = copy.deepcopy(value['definition'])
        main = next(c for c in definition['containerDefinitions'] if c['name']==value['container'])
        main['image'] = built['worker' if kind=='scheduler' else kind]
        if kind != 'frontend':
            environment = {item['name']:item['value'] for item in main.get('environment',[])}
            environment['REGULATORY_GAP_ENABLED'] = 'true'
            main['environment'] = [{'name':key,'value':value} for key,value in environment.items()]
            queue_name = environment['SQS_PIPELINE_VALIDATED_URL'].rsplit('/',1)[-1]
            statements = [{'Effect':'Allow','Action':['sqs:SendMessage','sqs:GetQueueUrl','sqs:GetQueueAttributes'],
                'Resource':f'arn:aws:sqs:eu-west-1:{ACCOUNT}:{queue_name}'}]
            if kind in {'api','worker'}:
                statements.extend([
                    {'Effect':'Allow','Action':['s3:GetObject','s3:GetObjectVersion'],
                     'Resource':f'arn:aws:s3:::{BUCKET}/tenant/*/policies/*'},
                    {'Effect':'Allow','Action':['kms:Decrypt','kms:DescribeKey'],'Resource':kms_key},
                ])
            role = definition['taskRoleArn'].rsplit('/',1)[-1]
            if not role.startswith('sc-') or '-staging' not in role:
                raise RuntimeError('Refusing non-staging role')
            session.client('iam').put_role_policy(RoleName=role,PolicyName='regulatory-gap-storage-queues',
                PolicyDocument=json.dumps({'Version':'2012-10-17','Statement':statements}))
        registered = ecs.register_task_definition(**{key:value for key,value in definition.items() if key in allowed})['taskDefinition']['taskDefinitionArn']
        manifest['services'][kind] = {'service':value['service'],'task_definition':registered,
                                     'previous_definition':value['previous_definition'],'image':main['image']}
    args.manifest.parent.mkdir(parents=True,exist_ok=True)
    args.manifest.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2),flush=True)


if __name__ == '__main__':
    main()
