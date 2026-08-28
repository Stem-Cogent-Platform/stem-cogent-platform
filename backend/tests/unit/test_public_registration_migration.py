from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_public_identity_migration_is_exact_match_and_least_privilege() -> None:
    source = (
        ROOT / "alembic" / "versions" / "0021_2026_08_28_create_login_identities.py"
    ).read_text()

    assert 'revision: str = "0021"' in source
    assert 'down_revision: str | None = "0020"' in source
    assert "CREATE TABLE auth.login_identities" in source
    assert "email VARCHAR(320) PRIMARY KEY" in source
    assert "GRANT SELECT, INSERT ON auth.login_identities TO sc_app_runtime" in source
    assert "REVOKE UPDATE, DELETE, TRUNCATE" in source
