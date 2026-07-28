# RDS PostgreSQL module

This module provisions the Stem Cogent PostgreSQL 16 primary in private-data
subnets. The primary is always Multi-AZ, encrypted with the RDS customer-managed
KMS key, protected by the application-to-data security group, backed up for at
least seven days, and configured for encrypted CloudWatch log export, Enhanced
Monitoring, and Performance Insights.

Production can additionally enable a queryable asynchronous read replica. This
replica is not the Multi-AZ standby: the standby supplies synchronous failover,
while the read replica supplies `DATABASE_REPLICA_HOST`.

The master password input is ephemeral and is written to RDS through the AWS
provider's `password_wo` argument. The environment root owns the Secrets Manager
secret version and must increment the same credential revision in both places
when rotating it.

`pgvector` is deliberately absent from `shared_preload_libraries`; it is a
PostgreSQL extension and must be enabled by a database migration with
`CREATE EXTENSION vector`. `pg_stat_statements` and `pgaudit` are preloadable
libraries and are configured here.
