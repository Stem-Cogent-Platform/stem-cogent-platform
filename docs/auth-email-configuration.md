# Authentication email configuration — 2026-09-27

Sender: `Stem Cogent <noreply@login.stem-cogent.com>`.

The domain `stem-cogent.com` is registered through Hostinger, but its public DNS
is delegated to Route 53. The single authoritative zone is
`Z049652226HBJOQNSBONC` in AWS account `437040615141`; it serves both staging and
production. DNS records are managed in `infrastructure/terraform/bootstrap/dns`.

Resend domain `login.stem-cogent.com`, ID
`62c08fac-6f12-430f-98cb-ce228104a035`, was created in region `eu-west-1` and
verified. Both environments' existing managed API keys can access that domain.
Keys were not printed or copied into repository files.

The final DNS records follow the Resend API response, not the earlier manually
supplied values. In particular, `send.login` has MX and TXT records, not a CNAME.
The DKIM key was updated to the key generated for the newly registered domain.
Route 53 change `C0093877OZ1Y89FOVFKD` reconciled these records and reached INSYNC.

| Record name within stem-cogent.com | Type | Value |
| --- | --- | --- |
| resend._domainkey.login | TXT | Public key in `bootstrap/dns/auth_email.tf` |
| send.login | MX | `10 feedback-smtp.eu-west-1.amazonses.com` |
| send.login | TXT | `v=spf1 include:amazonses.com ~all` |
| rsend.login | CNAME | `send.forge.rmta.net` |
| _dmarc | TXT | `v=DMARC1; p=none;` |

All TTLs are 300 seconds. Both environment tfvars files persist the sender in
`auth_email_from`, which supplies `AUTH_EMAIL_FROM` to the API task definition.
The existing secrets are `sc/staging/email/resend/api-key` and
`sc/prod/email/resend/api-key`, each held in its respective AWS account.

The email configuration rollout uses the existing application images. It does
not release the uncommitted passwordless-login implementation. A configuration
test email is separate from an end-to-end test of the deployed OTP endpoints.

Resend reported the requested test message delivered to
`stemsystem883@gmail.com`, message ID `01a0e0d3-469c-706d-a65f-9a1cba4188d7`.
The sender configuration revisions are staging `sc-api-service-staging:92`
(previously 91) and production `sc-api-service-prod:23` (previously 22).

Both ECS deployments completed with two desired and two running tasks, zero
pending tasks, and HTTP 200 from their `/health/ready` endpoints. Both deployed
task definitions contain the sender above. All five DNS records were imported
into the shared DNS Terraform state.

Runtime permission verification found that both API task roles initially lacked
`secretsmanager:GetSecretValue` for their Resend secret. The administrator-led
delivery test did not exercise that application permission. Each role's existing
`ReadAssignedSecrets` policy now includes only its own environment's exact Resend
secret ARN; the shared IAM module preserves this change. AWS IAM simulation
returned `allowed` for both roles after the correction. Existing KMS decrypt
permission was already allowed and was not broadened. This verifies policy
evaluation, not an end-to-end login request from the application.

Validation: the IAM module's `terraform test -no-color` completed with 9 passed
and 0 failed, including the new Resend permission regression and checks that
unrelated service roles do not receive the key. The fixture now includes the
existing search-provider secrets and the API's validated queue used by onboarding
bootstrap jobs. Terraform formatting checks passed for the IAM module changes.
