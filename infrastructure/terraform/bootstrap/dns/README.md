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
