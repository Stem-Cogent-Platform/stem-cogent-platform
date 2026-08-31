from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

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


@pytest.mark.parametrize(
    "instances",
    ([], [{"DBInstanceStatus": "backing-up"}]),
)
def test_snapshot_requires_one_available_database(monkeypatch, instances) -> None:
    client = MagicMock()
    client.describe_db_instances.return_value = {"DBInstances": instances}
    session = SimpleNamespace(client=lambda service: client)
    monkeypatch.setattr(snapshot.boto3, "Session", lambda **kwargs: session)

    with pytest.raises(RuntimeError, match="not available"):
        snapshot.ensure_snapshot(
            profile="staging",
            region="eu-west-1",
            database_id="sc-postgres-staging",
            snapshot_id="baseline",
        )


def test_existing_snapshot_must_belong_to_requested_database(monkeypatch) -> None:
    client = MagicMock()
    client.exceptions.DBSnapshotNotFoundFault = type("MissingSnapshot", (Exception,), {})
    client.describe_db_instances.return_value = {
        "DBInstances": [{"DBInstanceStatus": "available"}]
    }
    client.describe_db_snapshots.return_value = {
        "DBSnapshots": [{"DBInstanceIdentifier": "different-database"}]
    }
    session = SimpleNamespace(client=lambda service: client)
    monkeypatch.setattr(snapshot.boto3, "Session", lambda **kwargs: session)

    with pytest.raises(RuntimeError, match="different database"):
        snapshot.ensure_snapshot(
            profile="staging",
            region="eu-west-1",
            database_id="sc-postgres-staging",
            snapshot_id="baseline",
        )


def test_snapshot_cli_prints_machine_readable_result(monkeypatch, capsys) -> None:
    import sys

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "snapshot",
            "--profile",
            "staging",
            "--database-id",
            "sc-postgres-staging",
            "--snapshot-id",
            "baseline",
        ],
    )
    monkeypatch.setattr(
        snapshot,
        "ensure_snapshot",
        lambda **kwargs: {"snapshot_id": kwargs["snapshot_id"], "status": "available"},
    )
    snapshot.main()
    assert capsys.readouterr().out.strip() == '{"snapshot_id": "baseline", "status": "available"}'
