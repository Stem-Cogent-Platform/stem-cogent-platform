"""Authenticated, versioned policy uploads and evidence downloads."""
from __future__ import annotations

import asyncio
import hashlib
from uuid import UUID, uuid4

import boto3
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import text

from app.api.auth import RequestContext, get_request_context, require_permission
from app.context.policy_service import PolicyInputError, store_file, validate_document
from app.core.config import get_settings
from app.workers.tasks.regulatory_gap import dispatch

router = APIRouter(prefix='/api/v1/policies', tags=['policy-vault'])


async def enabled(context: RequestContext):
    if not get_settings().REGULATORY_GAP_ENABLED:
        raise HTTPException(503, 'Evidence audits are not enabled in this environment')
    expired = (await context.session.execute(text('''SELECT subscription_tier='pilot'
        AND pilot_expires_at<=now() FROM auth.tenants WHERE id=:org'''),
        {'org': context.principal.tenant_id})).scalar_one_or_none()
    if expired:
        raise HTTPException(402, 'The pilot trial has expired. Upgrade to continue evidence audits.')


@router.get('')
async def list_policies(context: RequestContext = Depends(get_request_context)):
    await enabled(context)
    require_permission(context, 'READ_INTELLIGENCE')
    rows = (await context.session.execute(text('''SELECT id,document_family_id,document_title,version,
        policy_category,processing_status,error_code,embedded_chunks_count,active,created_at,updated_at
        FROM organizations.tenant_policies WHERE organization_id=:org ORDER BY created_at DESC LIMIT 200'''),
        {'org': context.principal.tenant_id})).mappings().all()
    health = (await context.session.execute(text('''SELECT count(*) assessed_obligations,
        round(avg(a.compliance_score),2) policy_evidence_score,
        count(*) FILTER (WHERE EXISTS (
            (SELECT p.id::text FROM organizations.tenant_policies p
                WHERE p.organization_id=:org AND p.active
             EXCEPT SELECT s->>'id' FROM jsonb_array_elements(r.policy_snapshot) s)
            UNION ALL
            (SELECT s->>'id' FROM jsonb_array_elements(r.policy_snapshot) s
             EXCEPT SELECT p.id::text FROM organizations.tenant_policies p
                WHERE p.organization_id=:org AND p.active)
        )) stale_obligations
        FROM pipeline.compliance_gap_audits a JOIN pipeline.compliance_gap_runs r ON r.id=a.run_id
        WHERE a.organization_id=:org AND r.processing_status='completed'
        AND NOT EXISTS (SELECT 1 FROM pipeline.compliance_gap_runs newer
            WHERE newer.organization_id=:org AND newer.signal_id=r.signal_id
            AND newer.processing_status='completed' AND (newer.created_at,newer.id)>(r.created_at,r.id))'''),
        {'org': context.principal.tenant_id})).mappings().one()
    return {'items': [dict(row) for row in rows], 'health': dict(health)}


@router.post('/upload', status_code=202)
async def upload_policy(file: UploadFile = File(...), document_title: str = Form(...),
                        policy_category: str = Form(...), version: str = Form('1.0'),
                        document_family_id: UUID | None = Form(None),
                        context: RequestContext = Depends(get_request_context)):
    await enabled(context)
    require_permission(context, 'MANAGE_POLICIES')
    if not document_title.strip() or len(document_title)>255 or not version.strip() or len(version)>20:
        raise HTTPException(422, 'A title (1–255 characters) and version (1–20 characters) are required')
    if policy_category not in {'aml_kyc','data_privacy','payment_ops','dispute_resolution','other'}:
        raise HTTPException(422, 'Unknown policy category')
    org, identifier = context.principal.tenant_id, uuid4()
    family = document_family_id or identifier
    if document_family_id:
        exists = (await context.session.execute(text('''SELECT id FROM organizations.tenant_policies
            WHERE organization_id=:org AND document_family_id=:family LIMIT 1'''),
            {'org': org, 'family': family})).scalar_one_or_none()
        if not exists:
            raise HTTPException(404, 'Policy family not found')
    duplicate = (await context.session.execute(text('''SELECT id FROM organizations.tenant_policies
        WHERE organization_id=:org AND document_family_id=:family AND version=:version'''),
        {'org': org, 'family': family, 'version': version.strip()})).scalar_one_or_none()
    if duplicate:
        raise HTTPException(409, 'This policy version already exists')
    try:
        body = await file.read(min(get_settings().POLICY_MAX_UPLOAD_BYTES, 20971520)+1)
        content_type = validate_document(body, file.filename or '')
    except PolicyInputError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        await file.close()
    extension = 'pdf' if content_type == 'application/pdf' else 'docx'
    key = f'tenant/{org}/policies/{identifier}/document.{extension}'
    file_version = await store_file(body, key, content_type)
    await context.session.execute(text('''INSERT INTO organizations.tenant_policies
        (id,organization_id,document_family_id,document_title,version,file_s3_key,file_s3_version,
         content_type,content_sha256,file_size,policy_category,created_by)
        VALUES(:id,:org,:family,:title,:version,:key,:file_version,:mime,:sha,:size,:category,:user)'''),
        {'id': identifier,'org': org,'family': family,'title': document_title.strip(),'version': version.strip(),
         'key': key,'file_version': file_version,'mime': content_type,'sha': hashlib.sha256(body).hexdigest(),
         'size': len(body),'category': policy_category,'user': context.principal.user_id})
    await context.session.commit()
    dispatch('policy', org, identifier)
    return {'id': identifier, 'processing_status': 'queued'}


@router.get('/{policy_id}/download')
async def download_policy(policy_id: UUID, context: RequestContext = Depends(get_request_context)):
    await enabled(context)
    require_permission(context, 'READ_INTELLIGENCE')
    row = (await context.session.execute(text('''SELECT file_s3_key,file_s3_version
        FROM organizations.tenant_policies WHERE id=:id AND organization_id=:org'''),
        {'id': policy_id,'org': context.principal.tenant_id})).mappings().one_or_none()
    if not row:
        raise HTTPException(404, 'Policy not found')
    settings = get_settings()
    params = {'Bucket': settings.S3_ENTERPRISE_UPLOADS_BUCKET,'Key': row['file_s3_key'],
              'ResponseContentDisposition': 'attachment'}
    if row['file_s3_version']:
        params['VersionId'] = row['file_s3_version']
    client = boto3.client('s3', region_name=settings.AWS_REGION)
    url = await asyncio.to_thread(client.generate_presigned_url,'get_object',Params=params,ExpiresIn=300)
    return {'url': url, 'expires_in': 300}


@router.post('/{policy_id}/retry', status_code=202)
async def retry_policy(policy_id: UUID, context: RequestContext = Depends(get_request_context)):
    await enabled(context)
    require_permission(context,'MANAGE_POLICIES')
    row = (await context.session.execute(text('''UPDATE organizations.tenant_policies
        SET processing_status='queued',attempts=0,error_code=NULL,lease_until=NULL,updated_at=now()
        WHERE id=:id AND organization_id=:org AND processing_status='failed' RETURNING id'''),
        {'id': policy_id,'org': context.principal.tenant_id})).scalar_one_or_none()
    if row is None:
        raise HTTPException(409,'Only failed documents can be retried; scanned PDFs require a text-readable replacement')
    await context.session.commit()
    dispatch('policy',context.principal.tenant_id,policy_id)
    return {'id': policy_id,'processing_status':'queued'}
