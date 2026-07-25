# Terraform Backend Bootstrap

The environment roots cannot create the remote backend on which their own
state depends. These bootstrap roots independently create, per environment:

- a versioned, private S3 state bucket encrypted by a dedicated rotating CMK;
- a DynamoDB state-lock table encrypted by the same CMK; and
- outputs that map directly to the infrastructure CD workflow variables.

Bootstrap starts with local state. After the first apply, migrate that state
into the newly created backend using the emitted bucket, KMS key, and lock
table outputs. Never commit the local bootstrap state; repository ignore rules
exclude all `*.tfstate` files.
