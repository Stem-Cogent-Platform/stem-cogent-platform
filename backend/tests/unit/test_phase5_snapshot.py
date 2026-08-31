from types import SimpleNamespace
from unittest.mock import MagicMock

from app.ops import create_phase5_baseline_snapshot as snapshot


def test_snapshot_is_created_once_and_waited_for(monkeypatch) -> None:
    client = MagicMock()
    client.exceptions.DBSnapshotNotFoundFault = type("MissingSnapshot", (Exception,), {})
    client.describe_db_instances.return_value = {
        "DBInstances": [{"DBInstanceStatus": "available"}]
    }
    client.describe_db_snapshots.side_effect = [
        client.exceptions.DBSnapshotNotFoundFault(),
        {
            "DBSnapshots": [
                {
                    "DBInstanceIdentifier": "sc-postgres-staging",
                    "DBSnapshotIdentifier": "baseline",
                    "Status": "available",
                    "Encrypted": True,
                }
            ]
        },
    ]
    client.create_db_snapshot.return_value = {"DBSnapshot": {}}
    session = SimpleNamespace(client=lambda service: client)
    monkeypatch.setattr(snapshot.boto3, "Session", lambda **kwargs: session)

    result = snapshot.ensure_snapshot(
        profile="staging",
        region="eu-west-1",
        database_id="sc-postgres-staging",
        snapshot_id="baseline",
    )

    assert result == {
        "database_id": "sc-postgres-staging",
        "snapshot_id": "baseline",
        "status": "available",
        "encrypted": "true",
    }
    client.create_db_snapshot.assert_called_once()
    client.get_waiter.return_value.wait.assert_called_once()
