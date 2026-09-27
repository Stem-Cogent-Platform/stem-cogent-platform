# Global DNS bootstrap

This root owns the single Route 53 public hosted zone shared by staging and
production. It is deliberately separate from both environment states so that
destroying or rebuilding an application environment cannot delete the apex
domain's authoritative DNS zone.

The root uses the protected S3 backend under a dedicated
`stem-cogent/global/dns/terraform.tfstate` key. After its first apply, configure
the exact `name_servers` output at the domain registrar. Do not copy
nameservers from an older hosted zone: every public hosted zone receives its
own delegation set.

The hosted zone has Terraform `prevent_destroy` protection. Removing it is a
separate, explicitly reviewed recovery operation.

## Authentication email

`auth_email.tf` owns the Resend sending records for `login.stem-cogent.com` and
the apex DMARC policy. These shared records serve both application environments;
do not duplicate their ownership in the staging and production Terraform states.
The DNS owner is account `437040615141`, zone `Z049652226HBJOQNSBONC`.

The Resend domain ID is `62c08fac-6f12-430f-98cb-ce228104a035`, in `eu-west-1`.
The records match the domain creation API response, reconciled through Route 53
change `C0093877OZ1Y89FOVFKD`. Import blocks bring the directly created records
under this state. TTL is 300 seconds, and DMARC uses monitoring policy `p=none`.

| Name relative to stem-cogent.com | Type | Purpose |
| --- | --- | --- |
| resend._domainkey.login | TXT | Resend-generated DKIM public key |
| send.login | MX | Resend sending feedback endpoint |
| send.login | TXT | SPF authorization |
| rsend.login | CNAME | Resend sending record |
| _dmarc | TXT | DMARC monitoring policy |

Both environment tfvars files set `auth_email_from` to
`Stem Cogent <noreply@login.stem-cogent.com>`. Each environment retains its own
managed Resend API-key secret; both keys were checked for access to this domain.
Resend verification and actual receipt of a test message are separate checks
from DNS publication and ECS deployment health.
