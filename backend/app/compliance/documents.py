from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass


TERMS_VERSION = "2026-08-24"
PRIVACY_POLICY_VERSION = "2026-08-24"
NDPA_CONSENT_VERSION = "NDPA-2023-GAID-2025-2026-08-24"

TERMS_OF_SERVICE = """Stem Cogent Terms of Service

Stem Cogent provides evidence-backed decision-intelligence software. The service supports human investigation and decision-making; it does not make, approve, or execute business, legal, regulatory, investment, credit, or operational decisions for a customer.

You confirm that you are authorised by your organisation to create or use its workspace and to submit the business information you provide. You must not submit personal data, confidential information, credentials, payment-card data, or third-party material unless your organisation has a lawful basis and authority to do so. You must not attempt to cross tenant boundaries, bypass access controls, disrupt the service, reverse engineer protected components, or use outputs unlawfully.

Customer workspace content remains isolated to the customer tenant under the platform access-control model. Stem Cogent may process that content only to operate, secure, support, and improve the contracted service, subject to the applicable agreement and privacy policy. Evidence and derived outputs may contain uncertainty; users must review cited sources and exercise independent professional judgment.

Access may be limited or suspended to protect customers, the platform, or comply with law. Subscription fees, renewal, cancellation, and plan limits are governed by the selected plan and checkout terms. Mandatory rights and liabilities under applicable Nigerian law are not excluded. Continued use after a notified version change requires fresh acceptance when the platform marks that change as material."""

PRIVACY_POLICY = """Stem Cogent Privacy Notice

Stem Cogent processes account identifiers, authentication and security records, workspace configuration, Decision Lens and Focus Area preferences, audit events, service usage, support communications, and customer-provided business context. The purposes are to provide and secure the service, isolate tenant workspaces, personalise authorised decision intelligence, maintain evidence and audit records, administer subscriptions, respond to support or rights requests, and meet legal obligations.

Processing is limited to data necessary for those purposes and is based on contract performance, legal obligations, legitimate interests in operating and securing the service, and consent where consent is the appropriate lawful basis. Customer administrators control workspace membership and business context. Authorised processors may support hosting, communications, payments, monitoring, and model inference under contractual and technical safeguards. Tenant-private content is disclosed to an inference provider only when product configuration, contract, privacy controls, and retrieval authorisation permit it.

Records are retained according to contractual, security, audit, and legal requirements and are then deleted or irreversibly de-identified. Security controls include encryption in transit and at rest, tenant-scoped authorisation, row-level controls, audit logging, restricted secrets, and incident response. No security measure eliminates all risk.

Subject to the Nigeria Data Protection Act 2023 and other applicable law, individuals may request information, access, correction, deletion, restriction, portability, or objection, withdraw consent where processing relies on consent, and complain to the Nigeria Data Protection Commission. Requests may be submitted through the authenticated support channel or the published Stem Cogent privacy contact. Identity and authority will be verified before a request is fulfilled."""

NDPA_CONSENT_NOTICE = """Nigeria data-protection consent checkpoint

I explicitly opt in to Stem Cogent processing the account details, role preferences, Focus Areas, security metadata, and authorised business context that I submit for tenant-isolated decision intelligence, evidence retrieval, service security, auditability, and support. I understand that optional tenant-private content may be sent to an approved inference provider only after tenant authorisation and retrieval controls permit it. I confirm that I am authorised to provide the submitted business context and will not submit personal data or third-party confidential information without a lawful basis.

I understand that consent may be withdrawn for future consent-based processing without affecting processing already performed lawfully, and that contract, security, audit, or legal obligations may require retention of specified records. This checkpoint is implemented under the Nigeria Data Protection Act 2023 and the Nigeria Data Protection Commission's applicable implementation framework, including the General Application and Implementation Directive 2025."""

TERMS_ACCEPTANCE_TEXT = (
    f"I have read and agree to the Stem Cogent Terms of Service version {TERMS_VERSION}."
)
PRIVACY_ACCEPTANCE_TEXT = (
    f"I have read the Stem Cogent Privacy Notice version {PRIVACY_POLICY_VERSION}."
)
NDPA_ACCEPTANCE_TEXT = (
    "I explicitly consent to the processing described in the Nigeria data-protection "
    f"checkpoint version {NDPA_CONSENT_VERSION}."
)


@dataclass(frozen=True, slots=True)
class LegalDocument:
    code: str
    title: str
    version: str
    body: str
    acceptance_text: str
    sha256: str


def _document(code: str, title: str, version: str, body: str, acceptance_text: str) -> LegalDocument:
    return LegalDocument(
        code=code,
        title=title,
        version=version,
        body=body,
        acceptance_text=acceptance_text,
        sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
    )


def current_legal_documents() -> dict[str, LegalDocument]:
    return {
        "terms": _document(
            "TERMS_OF_SERVICE", "Terms of Service", TERMS_VERSION, TERMS_OF_SERVICE, TERMS_ACCEPTANCE_TEXT
        ),
        "privacy": _document(
            "PRIVACY_NOTICE",
            "Privacy Notice",
            PRIVACY_POLICY_VERSION,
            PRIVACY_POLICY,
            PRIVACY_ACCEPTANCE_TEXT,
        ),
        "ndpa": _document(
            "NDPA_CONSENT",
            "Nigeria data-protection consent",
            NDPA_CONSENT_VERSION,
            NDPA_CONSENT_NOTICE,
            NDPA_ACCEPTANCE_TEXT,
        ),
    }


def serialise_legal_documents() -> list[dict[str, str]]:
    return [asdict(document) for document in current_legal_documents().values()]
