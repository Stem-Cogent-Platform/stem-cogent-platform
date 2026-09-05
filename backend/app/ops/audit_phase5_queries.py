"""Execute candidate SELECTs from canonical source against staging, read-only."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from app.ops import audit_phase4_live_api as audit


def select_sql(path: Path, marker: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    matches = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and marker in node.value
        and node.value.strip().startswith("SELECT")
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one SELECT matching {marker!r}, found {len(matches)}"
        )
    return matches[0]


REMOTE = r"""
import asyncio,json
from sqlalchemy import text
from app.core.database import get_engine

async def main():
 engine=get_engine(); result={}
 async with engine.connect() as c:
  target=(await c.execute(text("SELECT u.id,u.tenant_id FROM auth.users u JOIN context.company_profiles p ON p.tenant_id=u.tenant_id WHERE u.status='ACTIVE' ORDER BY u.created_at DESC LIMIT 1"))).mappings().one()
  await c.rollback()
  params={'tenant_id':target['tenant_id'],'user_id':target['id'],'limit':50,'lookback_days':45}
  for name,query in QUERIES.items():
   try:
    await c.execute(text('SET TRANSACTION READ ONLY'))
    await c.execute(text("SET LOCAL statement_timeout='30s'"))
    await c.execute(text("SET LOCAL ROLE sc_app_runtime"))
    await c.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"),{'tenant':str(target['tenant_id'])})
    rows=(await c.execute(text(query),params)).mappings().all()
    result[name]={'status':'PASS','rows':len(rows)}
    if name=='trial_readiness' and rows: result[name]['readiness']=dict(rows[0])
    if name=='admin_readiness' and rows:
     result[name]['counts']={key:rows[0][key] for key in ('company_briefs','meaningful_monitoring_count','company_context_version')}
   except Exception as exc:
    result[name]={'status':'FAIL','error_type':type(exc).__name__,'sqlstate':getattr(getattr(exc,'orig',None),'sqlstate',None)}
   finally:
    await c.rollback()
 await engine.dispose()
 print('PHASE4_LIVE_AUDIT='+json.dumps(result,default=str))

asyncio.run(main())
"""


if __name__ == "__main__":
    app = Path(__file__).resolve().parents[1]
    queries = {
        "activation_candidates": select_sql(
            app / "workers/tasks/pilot_activation.py", "output.id AS global_output_id"
        ),
        "monitoring": select_sql(app / "api/v1/product.py", ") visible_monitoring"),
        "admin_readiness": select_sql(
            app / "api/v1/admin.py", "AS meaningful_monitoring_count"
        ),
        "trial_readiness": select_sql(
            app / "workers/tasks/pilot_activation.py", ")) first_value"
        ),
    }
    audit._REMOTE_AUDIT = f"QUERIES={queries!r}\n" + REMOTE
    print(json.dumps(audit._run("staging", "staging", "eu-west-1", 600), indent=2))
