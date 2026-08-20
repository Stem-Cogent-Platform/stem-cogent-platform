# Terraform Bootstrap

The environment roots cannot create the durable global resources on which
their own plans depend. The `staging` and `prod` bootstrap roots independently
create, per environment:

- a versioned, private S3 state bucket encrypted by a dedicated rotating CMK;
- native S3 lockfile support on the versioned state bucket; and
- bucket and KMS outputs that map directly to infrastructure CD workflow
  variables, plus the legacy lock-table output retained for migration audits.

The bootstrap module currently retains the previously provisioned DynamoDB
lock table as a protected migration resource. Terraform 1.15 and the
infrastructure workflow use `use_lockfile=true`; no new workflow depends on
the deprecated `dynamodb_table` backend parameter. Decommissioning the legacy
table must be a separate reviewed change after all clients have reinitialized.

The `dns` bootstrap root owns the single public Route 53 hosted zone shared by
staging and production. It uses a separate remote-state key, protects the zone
from Terraform destruction, and emits the exact nameservers that must be
configured at the domain registrar. Application environment roots create
records in this zone but never own or duplicate the zone itself.

Bootstrap starts with local state. After the first apply, migrate that state
into the newly created backend using the emitted bucket and KMS key outputs
with `use_lockfile=true`. The lock-table output is required only by legacy
backend clients during the migration window. Never commit the local bootstrap
state; repository ignore rules exclude all `*.tfstate` files.
