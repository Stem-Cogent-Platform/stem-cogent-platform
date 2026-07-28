# ElastiCache Redis module

This module provisions Redis OSS 7.1 in private-data subnets with cluster mode
disabled, TLS required, Redis AUTH required, encryption at rest, daily RDB
snapshots, encrypted engine and slow logs, and no public endpoint.

Staging may use one `cache.t4g.medium` node to control cost. Production must pass
at least two nodes; the module then enables cross-AZ placement support,
automatic failover, and Multi-AZ.

The architecture documents describe different eviction policies for Redis
logical databases. Redis cannot do that: `maxmemory-policy` is process-wide.
This module therefore uses `noeviction` because scheduler locks, sessions,
rate-limit counters, and broker metadata must not be silently evicted. Cache
keys must use their specified TTLs and capacity alarms must fire before memory
is exhausted.

ElastiCache for Redis OSS does not support AOF. A replica provides live
availability and daily RDB snapshots provide recovery; durable pipeline work
must use the SQS queues introduced by Task 1.3.8.
