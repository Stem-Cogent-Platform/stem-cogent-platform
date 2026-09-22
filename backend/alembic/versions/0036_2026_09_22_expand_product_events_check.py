"""Expand product_events_name_check to include INTELLIGENCE_VIEWED and INTELLIGENCE_TAB_CHANGED.

Revision ID: 0036
Revises: 0035
"""

from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE feedback.product_events
        DROP CONSTRAINT IF EXISTS product_events_name_check
    """)
    op.execute("""
        ALTER TABLE feedback.product_events
        ADD CONSTRAINT product_events_name_check CHECK (event_name IN (
            'SESSION_STARTED','BRIEFING_VIEWED','BRIEF_OPENED','BRIEF_UPDATED_VIEWED',
            'EVIDENCE_PANEL_OPENED','CIL_OPENED','CIL_QUERY_SUBMITTED',
            'BRIEF_ACKNOWLEDGED','BRIEF_WATCHED','BRIEF_ESCALATED','BRIEF_ACTED_ON',
            'BRIEF_DISMISSED','WIDER_INTELLIGENCE_VIEWED','INTELLIGENCE_VIEWED',
            'INTELLIGENCE_TAB_CHANGED','WATCHLIST_ITEM_VIEWED',
            'FOCUS_AREA_ADDED','FOCUS_AREA_UPDATED','SEARCH_PERFORMED','ALERT_OPENED',
            'DIGEST_OPENED','DECISION_PATHS_VIEWED'
        ))
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE feedback.product_events
        DROP CONSTRAINT IF EXISTS product_events_name_check
    """)
    op.execute("""
        ALTER TABLE feedback.product_events
        ADD CONSTRAINT product_events_name_check CHECK (event_name IN (
            'SESSION_STARTED','BRIEFING_VIEWED','BRIEF_OPENED','BRIEF_UPDATED_VIEWED',
            'EVIDENCE_PANEL_OPENED','CIL_OPENED','CIL_QUERY_SUBMITTED',
            'BRIEF_ACKNOWLEDGED','BRIEF_WATCHED','BRIEF_ESCALATED','BRIEF_ACTED_ON',
            'BRIEF_DISMISSED','WIDER_INTELLIGENCE_VIEWED','WATCHLIST_ITEM_VIEWED',
            'FOCUS_AREA_ADDED','FOCUS_AREA_UPDATED','SEARCH_PERFORMED','ALERT_OPENED',
            'DIGEST_OPENED','DECISION_PATHS_VIEWED'
        ))
    """)
