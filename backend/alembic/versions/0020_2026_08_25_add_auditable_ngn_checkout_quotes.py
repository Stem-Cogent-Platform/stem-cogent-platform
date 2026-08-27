"""Record the canonical display price and the locked CBN settlement quote.

Revision ID: 0020
Revises: 0019
Create Date: 2026-08-25
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE billing.checkout_intents "
        "ADD COLUMN display_amount_cents INTEGER"
    )
    op.execute(
        "ALTER TABLE billing.checkout_intents "
        "ADD COLUMN display_currency VARCHAR(3)"
    )
    op.execute("ALTER TABLE billing.checkout_intents ADD COLUMN fx_rate NUMERIC(16, 6)")
    op.execute("ALTER TABLE billing.checkout_intents ADD COLUMN fx_source VARCHAR(100)")
    op.execute("ALTER TABLE billing.checkout_intents ADD COLUMN fx_source_url TEXT")
    op.execute("ALTER TABLE billing.checkout_intents ADD COLUMN fx_quoted_at TIMESTAMPTZ")
    op.execute(
        "ALTER TABLE billing.checkout_intents "
        "ADD CONSTRAINT checkout_intents_display_amount_check "
        "CHECK (display_amount_cents IS NULL OR display_amount_cents > 0)"
    )
    op.execute(
        "ALTER TABLE billing.checkout_intents "
        "ADD CONSTRAINT checkout_intents_display_currency_check "
        "CHECK (display_currency IS NULL OR display_currency ~ '^[A-Z]{3}$')"
    )
    op.execute(
        "ALTER TABLE billing.checkout_intents "
        "ADD CONSTRAINT checkout_intents_fx_rate_check CHECK (fx_rate IS NULL OR fx_rate > 0)"
    )
    op.execute(
        "ALTER TABLE billing.checkout_intents "
        "ADD CONSTRAINT checkout_intents_fx_quote_complete_check CHECK ("
        "(fx_rate IS NULL AND fx_source IS NULL AND fx_source_url IS NULL AND fx_quoted_at IS NULL) "
        "OR (fx_rate IS NOT NULL AND fx_source IS NOT NULL AND fx_source_url IS NOT NULL AND fx_quoted_at IS NOT NULL)"
        ")"
    )
    op.execute(
        "UPDATE billing.checkout_intents AS intent "
        "SET display_amount_cents = plan.monthly_price_cents, display_currency = plan.currency "
        "FROM billing.plans AS plan "
        "WHERE plan.plan_code = intent.plan_code "
        "AND intent.display_amount_cents IS NULL"
    )


def downgrade() -> None:
    for constraint in (
        "checkout_intents_fx_quote_complete_check",
        "checkout_intents_fx_rate_check",
        "checkout_intents_display_currency_check",
        "checkout_intents_display_amount_check",
    ):
        op.execute(f"ALTER TABLE billing.checkout_intents DROP CONSTRAINT {constraint}")
    for column in (
        "fx_quoted_at",
        "fx_source_url",
        "fx_source",
        "fx_rate",
        "display_currency",
        "display_amount_cents",
    ):
        op.execute(f"ALTER TABLE billing.checkout_intents DROP COLUMN {column}")
