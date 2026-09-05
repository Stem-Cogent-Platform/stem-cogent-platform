# Controlled fresh staging pilot input

User delegated selection of a suitable company and pilot email. This is a
controlled staging acceptance profile, not a real Paystack customer account.
Do not create this profile in production or send an external invitation.

Sign in using the existing authorized operator and MFA at
https://app.staging.stem-cogent.com/internal/login.
Do not share passwords, MFA codes, session tokens or invitation tokens in chat.

## Provisioning fields

| Field | Value |
|---|---|
| Company display name | Paystack |
| Website | https://paystack.com/ |
| Pilot owner | Stem acceptance operator |
| Business categories | Payment processing |
| Operating markets | Nigeria |
| Products | Online payments, Recurring payments, Invoicing |
| Dependencies / competitors | Leave empty: no unsupported company relationships are asserted |
| Strategic priorities | Monitor changes affecting payment processing in Nigeria |
| Internal notes | CONTROLLED STAGING ACCEPTANCE ONLY. Not an actual Paystack customer or representative. Public product context; monitoring priority is a test preference, not a claim about company strategy. No external email delivery. Acceptance reference: funded-phase5-20260905. |
| Invitation email, only after readiness passes | phase5-paystack-20260905@example.invalid |

Product/market context is supported by
[Paystack's public product description](https://support.paystack.com/en/articles/2130562).
The `.invalid` recipient is intentionally non-deliverable. The invitation API
returns a link; it does not send mail. Keep the link private in the staging UI.

## Operator hand-off

1. Create the tenant once through the internal admin form.
2. Report only its tenant ID (not any credential or invitation token).
3. Do not override readiness or issue an invitation yet. Entity resolution,
   bounded activation, meaningful first value and the remaining acceptance
   checks must be verified first.

This input sheet is not evidence that provisioning, invitation, onboarding or
the fresh-tenant production gate has passed.
