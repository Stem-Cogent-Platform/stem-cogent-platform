"""Disambiguate invitation acceptance conflict targets.

Revision ID: 0026
Revises: 0025
Create Date: 2026-09-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _accept_function(*, qualified_conflicts: bool) -> str:
    user_conflict = (
        "ON CONFLICT ON CONSTRAINT users_tenant_email_key"
        if qualified_conflicts
        else "ON CONFLICT (tenant_id, email)"
    )
    identity_conflict = (
        "ON CONFLICT ON CONSTRAINT login_identities_pkey"
        if qualified_conflicts
        else "ON CONFLICT (email)"
    )
    statement = """
        CREATE OR REPLACE FUNCTION auth.accept_tenant_invitation(
            p_token_hash TEXT, p_password_hash TEXT, p_display_name TEXT
        ) RETURNS TABLE (user_id UUID, tenant_id UUID, email VARCHAR)
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, auth, audit
        AS $$
        DECLARE invitation auth.tenant_invitations%ROWTYPE;
        DECLARE accepted_user_id UUID;
        BEGIN
            UPDATE auth.tenant_invitations
               SET status = CASE WHEN expires_at <= NOW() THEN 'EXPIRED' ELSE 'ACCEPTED' END,
                   accepted_at = CASE WHEN expires_at > NOW() THEN NOW() ELSE NULL END
             WHERE token_hash = p_token_hash AND status = 'PENDING'
             RETURNING * INTO invitation;
            IF invitation.id IS NULL OR invitation.status <> 'ACCEPTED' THEN
                RAISE EXCEPTION 'invitation is unavailable' USING ERRCODE = 'P0002';
            END IF;
            INSERT INTO auth.users (
                tenant_id, email, display_name, permission_role, status, password_hash
            ) VALUES (
                invitation.tenant_id, invitation.email, p_display_name,
                invitation.permission_role, 'ACTIVE', p_password_hash
            ) __USER_CONFLICT__ DO UPDATE SET
                display_name = EXCLUDED.display_name,
                permission_role = EXCLUDED.permission_role,
                password_hash = EXCLUDED.password_hash,
                status = 'ACTIVE', updated_at = NOW()
            RETURNING id INTO accepted_user_id;
            INSERT INTO auth.login_identities (email, tenant_id, user_id)
            VALUES (invitation.email, invitation.tenant_id, accepted_user_id)
            __IDENTITY_CONFLICT__ DO NOTHING;
            INSERT INTO audit.events (
                tenant_id, actor_user_id, event_type, entity_type,
                entity_id, event_data, occurred_at
            ) VALUES (
                invitation.tenant_id, accepted_user_id, 'INVITE_ACCEPTED',
                'TENANT_INVITATION', invitation.id, '{}'::JSONB, NOW()
            );
            RETURN QUERY SELECT accepted_user_id, invitation.tenant_id, invitation.email;
        END;
        $$
    """
    return statement.replace("__USER_CONFLICT__", user_conflict).replace(
        "__IDENTITY_CONFLICT__", identity_conflict
    )


def upgrade() -> None:
    # OUT parameters are PL/pgSQL variables. Named conflict columns such as
    # ``tenant_id`` and ``email`` are therefore ambiguous inside the function.
    # Constraint names select the same keys without colliding with OUT params.
    op.execute(_accept_function(qualified_conflicts=True))


def downgrade() -> None:
    op.execute(_accept_function(qualified_conflicts=False))
