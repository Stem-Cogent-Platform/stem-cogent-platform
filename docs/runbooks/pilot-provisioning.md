# Pilot provisioning

Use the production operator task only after the deployed API image has passed its health
and protected-route checks. The task creates an invite-only 21-day Trial workspace, its
administrator, the pilot engagement, and days 7, 14, and 21 checkpoints in one database
transaction.

Create the initial password as a dedicated AWS Secrets Manager scalar secret named under
`sc/<environment>/pilots/<pilot-slug>/initial-password`. The API task role is restricted to
that exact namespace. Do not place the password in a shell command, GitHub variable, issue,
log, or source file. Authorised operators retrieve the secret value through IAM and deliver
it to the pilot through a separate secure channel. Record the returned workspace UUID; it
is required at sign-in.

For the approved first pilot, run the current production API task with:

```text
python -m app.authn.provision_pilot
  --workspace-name "Odion Alex"
  --workspace-slug odion-alex-pilot
  --email marcoalex201804@gmail.com
  --display-name "Odion Alex"
  --password-secret-arn <dedicated-secret-arn>
  --cohort-code GUIDED_PILOT_2026_08
```

The command prints only the workspace UUID, normalised email, and pilot state. It never
prints the password. It can be safely re-run with the returned `--workspace-id` when an
operator must resume the same workspace; re-running does not extend the 21-day trial.

The pilot must sign in, accept the current legal documents, then complete the first
onboarding workflow. If it converts, the Billing screen displays the USD plan price and
locks the current CBN NFEM USD/NGN reference quote for the Paystack NGN checkout. Paid
access lasts one month; each renewal deliberately starts a new checkout and uses a new
live quote. Each successful payment is reconciled against that immutable quote and written
once to the invoice ledger.
