export const legalCopy = {
  terms: {
    title: "Terms of Service",
    version: "2026-08-24",
    sections: [
      ["Decision-support service", "Stem Cogent provides evidence-backed decision-intelligence software. It supports human investigation and decision-making; it does not make, approve, or execute business, legal, regulatory, investment, credit, or operational decisions for a customer."],
      ["Authorised use", "You confirm that you are authorised by your organisation to create or use its workspace and to submit the business information you provide. Do not submit personal data, confidential information, credentials, payment-card data, or third-party material unless your organisation has a lawful basis and authority to do so."],
      ["Workspace protection", "You must not attempt to cross tenant boundaries, bypass access controls, disrupt the service, reverse engineer protected components, or use outputs unlawfully. Customer workspace content remains isolated under the platform access-control model."],
      ["Evidence and judgment", "Evidence and derived outputs may contain uncertainty. Users must review cited sources and exercise independent professional judgment. Access may be limited or suspended to protect customers, the platform, or comply with law."],
      ["Plans and changes", "Subscription fees, renewal, cancellation, and limits are governed by the selected plan and checkout terms. Mandatory rights and liabilities under applicable Nigerian law are not excluded. Material changes require fresh acceptance when the platform identifies them as material."]
    ]
  },
  privacy: {
    title: "Privacy Notice",
    version: "2026-08-24",
    sections: [
      ["Information processed", "Stem Cogent processes account identifiers, authentication and security records, workspace configuration, Decision Lens and Focus Area preferences, audit events, service usage, support communications, and authorised customer-provided business context."],
      ["Purposes and lawful bases", "Processing provides and secures the service, isolates tenant workspaces, personalises authorised decision intelligence, maintains evidence and audit records, administers subscriptions, responds to support or rights requests, and meets legal obligations. Lawful bases include contract, legal obligation, legitimate interests, and consent where appropriate."],
      ["Processors and inference", "Authorised processors may support hosting, communications, payments, monitoring, and model inference under safeguards. Tenant-private content is disclosed to an inference provider only when product configuration, contract, privacy controls, and retrieval authorisation permit it."],
      ["Retention and security", "Records are retained according to contractual, security, audit, and legal requirements and are then deleted or irreversibly de-identified. Controls include encryption, tenant-scoped authorisation, row-level controls, audit logging, restricted secrets, and incident response."],
      ["Your rights", "Subject to the Nigeria Data Protection Act 2023 and applicable law, individuals may request information, access, correction, deletion, restriction, portability, or objection; withdraw consent for future consent-based processing; and complain to the Nigeria Data Protection Commission."]
    ]
  }
} as const;
