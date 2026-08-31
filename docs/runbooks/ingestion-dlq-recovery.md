# Ingestion DLQ recovery

Treat a non-empty ingestion dead-letter queue as a release blocker. Do not purge it:
the messages are recoverable operational evidence.

1. Confirm the collector services are stable and inspect `/sc/pipeline/ingestion/<environment>`
   for the bounded source failure.
2. Aggregate failed `pipeline.collection_jobs` by `config.sources.source_code`. Retire a
   source from the reviewed manifest when it has no successful collections and cannot be
   accessed without bypassing the publisher's controls.
3. Deploy the collector resilience fix before moving messages. Expected remote HTTP,
   DNS, and transport failures must be recorded on the collection job and acknowledged;
   unexpected storage, database, and event-publication failures must still reach the DLQ.
4. Use SQS `start-message-move-task` from each ingestion DLQ ARN back to its configured
   source queue. Never copy message bodies through an operator workstation.
5. Wait for the move task and both queues to settle. Verify the DLQ has zero visible,
   in-flight, and delayed messages, the related CloudWatch alarm is `OK`, and successful
   collection jobs continue to produce raw signals.

Queued work for a retired source is intentionally acknowledged as `SKIPPED`. Work for a
temporarily unavailable active source is retried by the fetcher's bounded policy and then
recorded as `FAILED` without creating a poison-message loop. Internal failures remain
unacknowledged so SQS can quarantine them for investigation.
