import json

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.api.auth import RequestContext, get_request_context, require_permission
from app.api.v1.policies import enabled
from app.billing.gates import enforce_workspace_access
from app.context.gap_models import MarketingRequest
from app.context.marketing_checker import RULES_VERSION, check_copy

router = APIRouter(prefix='/api/v1/workspace/marketing',tags=['marketing-compliance'])


@router.post('/check')
async def check_campaign(payload: MarketingRequest,context: RequestContext=Depends(get_request_context)):
    await enabled(context)
    require_permission(context,'USE_CIL')
    await enforce_workspace_access(context)
    licenses = (await context.session.execute(text('SELECT operating_licenses FROM context.company_profiles WHERE tenant_id=:org'),
        {'org':context.principal.tenant_id})).scalar_one_or_none() or []
    result = check_copy(payload.campaign_copy,payload.channel,list(licenses))
    identifier = (await context.session.execute(text('''INSERT INTO pipeline.marketing_checks
        (organization_id,created_by,campaign_copy,channel,result,rules_version)
        VALUES(:org,:user,:copy,:channel,CAST(:result AS jsonb),:version) RETURNING id'''),
        {'org':context.principal.tenant_id,'user':context.principal.user_id,'copy':payload.campaign_copy,
         'channel':payload.channel,'result':json.dumps(result),'version':RULES_VERSION})).scalar_one()
    await context.session.commit()
    return {'id':identifier,**result}
