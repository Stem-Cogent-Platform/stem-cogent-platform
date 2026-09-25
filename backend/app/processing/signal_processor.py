"""Signal processing and normalization worker engine."""

from __future__ import annotations

import datetime
import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.processing.extractor import ExtractionError, SignalExtractor
from app.processing.models import NormalizedSignalPayload

logger = logging.getLogger(__name__)


async def process_incoming_signals_batch(
    session: AsyncSession,
    extractor: SignalExtractor | None = None,
    batch_size: int = 20,
) -> dict[str, Any]:
    """Process a batch of pending incoming signals with FOR UPDATE SKIP LOCKED concurrency."""
    owns_extractor = False
    if extractor is None:
        extractor = SignalExtractor()
        owns_extractor = True

    try:
        # 1. Fetch batch using FOR UPDATE SKIP LOCKED to prevent concurrent worker contention
        result = await session.execute(
            text(
                """
                SELECT id, source_name, source_url, raw_title, raw_content, published_at
                FROM pipeline.incoming_signals
                WHERE status = 'pending_processing'
                ORDER BY created_at ASC
                LIMIT :batch_size
                FOR UPDATE SKIP LOCKED;
                """
            ),
            {"batch_size": batch_size},
        )
        rows = result.mappings().all()

        if not rows:
            logger.info("No pending incoming signals available for processing")
            return {
                "fetched": 0,
                "promoted": 0,
                "failed": 0,
                "promoted_signal_ids": [],
                "failed_signal_ids": [],
            }

        promoted_ids: list[str] = []
        failed_ids: list[str] = []

        for row in rows:
            signal_id: UUID = row["id"]
            source_name: str = row["source_name"]
            source_url: str = row["source_url"]
            title: str | None = row["raw_title"]
            content: str | None = row["raw_content"]
            published_at = row["published_at"]

            try:
                # 2. Extract structured payload with LLM and schema enforcement
                extracted: NormalizedSignalPayload = await extractor.extract(
                    title=title,
                    content=content,
                    source_name=source_name,
                    source_url=source_url,
                )

                # Parse statutory deadline to date object if present
                deadline_date: datetime.date | None = None
                if extracted.statutory_deadline:
                    try:
                        deadline_date = datetime.date.fromisoformat(extracted.statutory_deadline)
                    except ValueError:
                        deadline_date = None

                # 3. Transactional Promotion: Insert into pipeline.signals & update incoming_signals
                async with session.begin_nested():
                    insert_res = await session.execute(
                        text(
                            """
                            INSERT INTO pipeline.signals (
                                incoming_signal_id,
                                signal_type,
                                urgency,
                                sentiment,
                                primary_entity,
                                secondary_entities,
                                affected_sectors,
                                executive_summary,
                                statutory_deadline,
                                financial_impact_indicator,
                                normalized_payload,
                                title,
                                body_text,
                                source_url,
                                published_at,
                                detected_at,
                                pipeline_stage,
                                dedup_status,
                                is_proprietary,
                                normalized_at
                            ) VALUES (
                                :incoming_signal_id,
                                :signal_type,
                                :urgency,
                                :sentiment,
                                :primary_entity,
                                :secondary_entities,
                                :affected_sectors,
                                :executive_summary,
                                :statutory_deadline,
                                :financial_impact_indicator,
                                CAST(:normalized_payload AS JSONB),
                                :title,
                                :body_text,
                                :source_url,
                                :published_at,
                                NOW(),
                                'NORMALIZED',
                                'UNIQUE',
                                FALSE,
                                NOW()
                            )
                            RETURNING id;
                            """
                        ),
                        {
                            "incoming_signal_id": signal_id,
                            "signal_type": extracted.signal_type,
                            "urgency": extracted.urgency,
                            "sentiment": extracted.sentiment,
                            "primary_entity": extracted.primary_entity,
                            "secondary_entities": extracted.secondary_entities,
                            "affected_sectors": extracted.affected_sectors,
                            "executive_summary": extracted.executive_summary,
                            "statutory_deadline": deadline_date,
                            "financial_impact_indicator": extracted.financial_impact_indicator,
                            "normalized_payload": json.dumps(extracted.model_dump()),
                            "title": title or extracted.primary_entity,
                            "body_text": content or extracted.executive_summary,
                            "source_url": source_url,
                            "published_at": published_at,
                        },
                    )
                    created_signal_id = insert_res.scalar_one()

                    await session.execute(
                        text(
                            """
                            UPDATE pipeline.incoming_signals
                            SET status = 'promoted', updated_at = NOW(), error_message = NULL
                            WHERE id = :id;
                            """
                        ),
                        {"id": signal_id},
                    )

                promoted_ids.append(str(created_signal_id))
                logger.info(
                    "Promoted signal %s -> pipeline.signals %s (%s, %s)",
                    signal_id,
                    created_signal_id,
                    extracted.signal_type,
                    extracted.primary_entity,
                )


            except (ExtractionError, Exception) as exc:
                # 4. Resilient failure isolation: never block other signals in the batch
                logger.error(
                    "Failed to process signal %s (%s): %s",
                    signal_id,
                    source_name,
                    exc,
                    extra={"signal_id": str(signal_id), "source": source_name},
                )
                try:
                    async with session.begin_nested():
                        await session.execute(
                            text(
                                """
                                UPDATE pipeline.incoming_signals
                                SET status = 'failed', updated_at = NOW(), error_message = :err
                                WHERE id = :id;
                                """
                            ),
                            {"id": signal_id, "err": str(exc)[:1000]},
                        )
                except Exception as inner_exc:
                    logger.error("Failed to update status to failed for %s: %s", signal_id, inner_exc)

                failed_ids.append(str(signal_id))

        await session.commit()
        # Publish only committed signals; workers must never race the promotion transaction.
        from app.workers.celery_app import celery_app
        for promoted_id in promoted_ids:
            try:
                celery_app.send_task('app.workers.tasks.context_matching.route_signal_to_tenant_contexts', args=[promoted_id])
                celery_app.send_task('app.workers.tasks.regulatory_gap.extract_signal', args=[promoted_id])
            except Exception:
                logger.warning('Post-commit signal dispatch failed', extra={'signal_id': promoted_id})

        return {
            "fetched": len(rows),
            "promoted": len(promoted_ids),
            "failed": len(failed_ids),
            "promoted_signal_ids": promoted_ids,
            "failed_signal_ids": failed_ids,
        }

    finally:
        if owns_extractor:
            await extractor.aclose()


async def run_signal_processing(batch_size: int = 20) -> dict[str, Any]:
    """Execute one batch processing cycle against the configured database session."""
    async for session in get_session():
        return await process_incoming_signals_batch(session, batch_size=batch_size)
    return {
        "fetched": 0,
        "promoted": 0,
        "failed": 0,
        "promoted_signal_ids": [],
        "failed_signal_ids": [],
    }
