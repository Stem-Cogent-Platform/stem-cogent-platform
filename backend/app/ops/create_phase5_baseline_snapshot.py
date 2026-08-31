"""Create or verify the manual RDS snapshot required before Phase 5 migrations."""

from __future__ import annotations

import argparse
import json

import boto3


def ensure_snapshot(
    *, profile: str, region: str, database_id: str, snapshot_id: str
) -> dict[str, str]:
    client = boto3.Session(profile_name=profile, region_name=region).client("rds")
    databases = client.describe_db_instances(DBInstanceIdentifier=database_id)[
        "DBInstances"
    ]
    if len(databases) != 1 or databases[0]["DBInstanceStatus"] != "available":
        raise RuntimeError(f"Database {database_id} is not available")
    try:
        snapshots = client.describe_db_snapshots(DBSnapshotIdentifier=snapshot_id)[
            "DBSnapshots"
        ]
        snapshot = snapshots[0]
        if snapshot["DBInstanceIdentifier"] != database_id:
            raise RuntimeError("Existing snapshot belongs to a different database")
    except client.exceptions.DBSnapshotNotFoundFault:
        snapshot = client.create_db_snapshot(
            DBSnapshotIdentifier=snapshot_id,
            DBInstanceIdentifier=database_id,
            Tags=[
                {"Key": "Project", "Value": "stem-cogent"},
                {"Key": "Purpose", "Value": "phase5-baseline"},
            ],
        )["DBSnapshot"]
    client.get_waiter("db_snapshot_available").wait(
        DBSnapshotIdentifier=snapshot_id,
        WaiterConfig={"Delay": 30, "MaxAttempts": 40},
    )
    snapshot = client.describe_db_snapshots(DBSnapshotIdentifier=snapshot_id)[
        "DBSnapshots"
    ][0]
    return {
        "database_id": snapshot["DBInstanceIdentifier"],
        "snapshot_id": snapshot["DBSnapshotIdentifier"],
        "status": snapshot["Status"],
        "encrypted": str(snapshot["Encrypted"]).lower(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--region", default="eu-west-1")
    parser.add_argument("--database-id", required=True)
    parser.add_argument("--snapshot-id", required=True)
    args = parser.parse_args()
    result = ensure_snapshot(
        profile=args.profile,
        region=args.region,
        database_id=args.database_id,
        snapshot_id=args.snapshot_id,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
