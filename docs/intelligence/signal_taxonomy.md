# STEM COGENT — V2 SIGNAL TAXONOMY & DECISION RULES SEED SPECIFICATION

**Document ID:** SC-SEED-002  
**Document Version:** 2.0.0  
**Status:** Canonical MVP Seed Specification  
**Classification:** Internal Engineering — Restricted  
**Primary Product Scope:** Nigeria-first fintech decision intelligence  
**Depends On:** SC-DOC-001 v2.0.0, SC-DOC-003 v2.0.0, SC-DOC-004 v2.0.0, SC-DOC-005 v2.0.0, SC-DOC-010 v2.0.0  
**Supersedes:** `signal_taxonomy.md` v1.0.0 taxonomy section and its old `0004_signal_taxonomy_seed` instruction  
**Migration Target:** **Migration 0003 — Config Tables**  
**Tables Seeded:** `config.signal_taxonomy`, `config.decision_rules`

---

# 0. GOVERNING PRODUCT RULE

The V2 taxonomy must support the Stem Cogent product loop:

**Global Signal → Verified Event → Company Relevance → Business Exposure → Stakes → Decision Required → Decision Lens Priority → Decision Brief**

The Signal Taxonomy answers **what happened**.

It does **not** decide:
- whether the event matters to every fintech;
- what exact business exposure exists for a specific tenant;
- what exact monetary loss/revenue is at stake;
- which user must see it;
- what final action a human must take.

Those tenant/user-specific responsibilities belong to `decision.assessments`, `config.decision_rules`, Company Context, Decision Lens and Focus Areas.

---

# 1. NON-NEGOTIABLE TAXONOMY PRINCIPLES

1. **Eight canonical top-level domains only at MVP.**
2. **Event Type is the primary unit of classification precision.**
3. **Global urgency is event-based, not tenant-based.**
4. **Company relevance is computed after classification.**
5. **User relevance is computed after tenant relevance using Decision Lens + Focus Areas.**
6. **Strategic interpretation is derived intelligence, not a raw signal domain.**
7. **Technology, inclusion and general ecosystem concepts are primarily tags unless the observable event belongs to a canonical domain.**
8. **No advanced ML is required for launch.** Rules-first classification is canonical.
9. **LLMs do not assign authoritative domain, event type, confidence, urgency, tenant relevance or decision requirement.**
10. **All rules are versioned and hot-reloadable.**

---

# 2. CANONICAL V2 MACRO DOMAINS

| ID | domain_code | Label | Purpose | Default fallback weight |
|---|---|---|---|---|
| D01 | REGULATORY_POLICY | Regulatory & Policy | Rules, directives, enforcement, licensing, data protection, taxation, identity requirements and regulatory operating changes. | 0.72 |
| D02 | COMPETITIVE_PRODUCT | Competitive & Product Movement | Competitor product, pricing, feature, distribution, positioning and commercial movements. | 0.55 |
| D03 | INFRASTRUCTURE_RELIABILITY | Infrastructure & Ecosystem Reliability | Payment rails, banks, switches, cloud, telco, identity and operational dependencies affecting service continuity. | 0.72 |
| D04 | CUSTOMER_MARKET | Customer & Market Behaviour | Customer complaints, demand, switching, adoption, trust, usage and market-behaviour changes. | 0.45 |
| D05 | FINANCIAL_ECONOMIC | Financial & Economic Conditions | Revenue/margin signals, pricing pressure, liquidity, FX, inflation, rates and other economic conditions affecting fintech economics. | 0.58 |
| D06 | CAPITAL_PARTNERSHIP | Capital, Funding & Partnerships | Funding, debt, M&A, strategic investment, alliances, commercial partnerships and ecosystem relationships. | 0.42 |
| D07 | MARKET_EXPANSION | Market Expansion & Cross-Border | Country entry, regional expansion, distribution growth, remittance corridors and cross-border operating developments. | 0.48 |
| D08 | FRAUD_RISK_TRUST | Fraud, Risk & Trust | Fraud patterns, cyber incidents, identity abuse, chargebacks, scams, trust erosion and risk-control developments. | 0.72 |

**Important:** `Default fallback weight` is used only when no Event Type-specific base urgency is available. Normal V2 urgency starts from the Event Type base urgency.

---

# 3. EVENT TYPE CATALOGUE

Each Event Type is stored as a row in `config.signal_taxonomy`:

- `domain_code` = canonical V2 domain
- `subcategory_code` = Event Type code
- `keyword_patterns` = deterministic launch rules
- `entity_rules` = entity/type constraints
- `urgency_weight` = Event Type base urgency
- `version` = `2026.08-v2`
- `active` = true

Event Type codes are immutable identifiers after production release. Labels/keywords may evolve by version.


## 3.1 REGULATORY_POLICY — Regulatory & Policy

| subcategory_code / Event Type | Observable event | Base urgency |
|---|---|---|
| CIRCULAR_ISSUED | New circular/directive formally issued | 0.72 |
| CIRCULAR_AMENDED | Existing circular/directive amended | 0.68 |
| CIRCULAR_WITHDRAWN | Circular/directive withdrawn or superseded | 0.62 |
| CONSULTATION_PAPER | Consultation or draft framework published | 0.40 |
| COMPLIANCE_DEADLINE_ANNOUNCED | Compliance or implementation deadline announced | 0.88 |
| COMPLIANCE_DEADLINE_CHANGED | Compliance deadline accelerated, extended or changed | 0.86 |
| ENFORCEMENT_ACTION | Regulatory enforcement action, penalty or formal sanction | 0.95 |
| REGULATORY_WARNING | Formal regulatory warning or supervisory notice | 0.85 |
| LICENSE_CATEGORY_CREATED | New licence or authorisation category introduced | 0.66 |
| LICENSE_APPROVED | Licence or authorisation approved | 0.58 |
| LICENSE_SUSPENDED | Licence suspended | 0.96 |
| LICENSE_REVOKED | Licence revoked | 0.98 |
| KYC_REQUIREMENT_CHANGED | KYC threshold/process requirement changed | 0.86 |
| AML_REQUIREMENT_CHANGED | AML/reporting requirement changed | 0.86 |
| IDENTITY_REQUIREMENT_CHANGED | BVN/NIN/identity verification requirement changed | 0.88 |
| TRANSACTION_LIMIT_CHANGED | Wallet/transfer/transaction limit changed | 0.84 |
| CONSUMER_PROTECTION_RULE_CHANGED | Consumer rights, complaints or reimbursement rule changed | 0.78 |
| FRAUD_LIABILITY_RULE_CHANGED | Fraud liability or reimbursement responsibility changed | 0.90 |
| OPEN_BANKING_STANDARD_CHANGED | Open-banking/API standard or participation rule changed | 0.72 |
| DATA_PROTECTION_RULE_CHANGED | Privacy/data protection requirement changed | 0.82 |
| DATA_PROTECTION_ENFORCEMENT | Privacy/data enforcement or audit action | 0.90 |
| CROSS_BORDER_RULE_CHANGED | International transfer/cross-border payment rule changed | 0.80 |
| FX_POLICY_CHANGED | FX access, settlement or market policy changed | 0.82 |
| TAX_POLICY_CHANGED | Taxation affecting fintech products/services changed | 0.72 |
| USSD_TELECOM_RULE_CHANGED | USSD/telco rule affecting fintech changed | 0.72 |
| AGENT_BANKING_RULE_CHANGED | Agent-banking framework or compliance requirement changed | 0.76 |
| CBDC_POLICY_CHANGED | eNaira/CBDC policy or operating model changed | 0.58 |
| REGULATORY_FRAMEWORK_UPDATED | Broader framework/guideline updated without immediate enforcement | 0.60 |

## 3.2 COMPETITIVE_PRODUCT — Competitive & Product Movement

| subcategory_code / Event Type | Observable event | Base urgency |
|---|---|---|
| PRODUCT_LAUNCH | Competitor launches a new product | 0.60 |
| FEATURE_LAUNCH | Competitor launches a material feature | 0.50 |
| FEATURE_ENHANCEMENT | Competitor meaningfully improves an existing feature | 0.42 |
| PRODUCT_DISCONTINUATION | Competitor retires or withdraws a product | 0.48 |
| PRICING_INCREASE | Competitor increases fees/pricing | 0.56 |
| PRICING_REDUCTION | Competitor reduces fees/pricing | 0.70 |
| FX_SPREAD_CHANGED | Competitor changes FX spread or conversion pricing | 0.66 |
| API_LAUNCH | Competitor launches public API/developer platform | 0.52 |
| EMBEDDED_FINANCE_LAUNCH | Embedded-finance/BaaS product rollout | 0.54 |
| CREDIT_PRODUCT_LAUNCH | Credit/lending product launch | 0.56 |
| SAVINGS_PRODUCT_LAUNCH | Savings/investment product launch | 0.48 |
| BNPL_LAUNCH | BNPL product rollout | 0.50 |
| SME_PRODUCT_LAUNCH | SME/business product launch | 0.56 |
| MOBILE_APP_RELAUNCH | Major app redesign/relaunch | 0.38 |
| MERCHANT_EXPANSION | Material merchant acquisition/distribution expansion | 0.52 |
| AGENT_NETWORK_EXPANSION | Material agent/POS network expansion | 0.52 |
| ENTERPRISE_CUSTOMER_WIN | Material enterprise onboarding/customer win | 0.48 |
| USER_ACQUISITION_CAMPAIGN | Large acquisition/incentive/referral campaign | 0.36 |
| COMPETITOR_INFRA_INVESTMENT | Competitor invests materially in payments/switching/data infrastructure | 0.48 |
| STRATEGIC_REALIGNMENT_ANNOUNCED | Company publicly changes strategic direction | 0.60 |
| EXECUTIVE_APPOINTMENT | Material executive appointment relevant to competitive direction | 0.38 |
| EXECUTIVE_DEPARTURE | Material executive departure relevant to competitive direction | 0.42 |
| LAYOFF_OR_RESTRUCTURE | Material layoffs or organisational restructure | 0.44 |

## 3.3 INFRASTRUCTURE_RELIABILITY — Infrastructure & Ecosystem Reliability

| subcategory_code / Event Type | Observable event | Base urgency |
|---|---|---|
| ACTIVE_OUTAGE | Active outage affecting a critical provider/rail | 0.95 |
| SERVICE_DEGRADATION | Material service degradation | 0.82 |
| INTERMITTENT_FAILURE | Intermittent failures affecting reliability | 0.76 |
| SETTLEMENT_DELAY | Settlement delays or clearing disruption | 0.90 |
| TRANSACTION_FAILURE_SPIKE | Broad transaction failure spike | 0.90 |
| PAYMENT_RAIL_OUTAGE | NIBSS/PAPSS/instant-payment rail outage | 0.96 |
| SWITCH_OUTAGE | Payment switch downtime | 0.93 |
| CARD_NETWORK_INCIDENT | Card processing/scheme incident | 0.90 |
| BANK_INTEGRATION_FAILURE | Bank integration/API connection failure | 0.86 |
| API_INSTABILITY | External provider/API instability | 0.78 |
| LATENCY_SPIKE | External dependency latency increase | 0.68 |
| WEBHOOK_FAILURE | Webhook/callback failure trend | 0.66 |
| USSD_DEGRADATION | USSD channel degradation | 0.82 |
| TELCO_INCIDENT | Mobile-network incident affecting fintech access | 0.78 |
| CLOUD_INCIDENT | Cloud provider incident affecting services | 0.88 |
| IDENTITY_INFRA_INCIDENT | BVN/NIN/identity infrastructure outage or degradation | 0.90 |
| AGENT_LIQUIDITY_STRESS | Material agent-liquidity shortage | 0.72 |
| POS_FAILURE_SPIKE | Material POS/device failure spike | 0.78 |
| PLANNED_MAINTENANCE | Planned maintenance on a dependency | 0.35 |
| PAYMENT_RAIL_STANDARD_CHANGE | ISO 20022/interoperability/rail operating change | 0.58 |
| INFRA_CAPACITY_EXPANSION | New infrastructure capacity or interoperability improvement | 0.38 |

## 3.4 CUSTOMER_MARKET — Customer & Market Behaviour

| subcategory_code / Event Type | Observable event | Base urgency |
|---|---|---|
| COMPLAINT_VOLUME_SPIKE | Material increase in customer complaints | 0.68 |
| RATING_DECLINE | Material app-store rating decline | 0.52 |
| TRANSACTION_FAILURE_COMPLAINTS | Customer complaints about failed transactions | 0.72 |
| SETTLEMENT_DELAY_COMPLAINTS | Customer complaints about delayed settlement | 0.70 |
| ONBOARDING_FRICTION | Onboarding friction materially increases | 0.60 |
| IDENTITY_VERIFICATION_FRICTION | KYC/identity verification complaints increase | 0.62 |
| WITHDRAWAL_FRICTION | Withdrawal/cash-out friction increases | 0.62 |
| SUPPORT_SENTIMENT_DECLINE | Support sentiment/trust declines | 0.52 |
| FRAUD_COMPLAINT_SPIKE | Customer fraud/scam complaints spike | 0.78 |
| FEATURE_DEMAND_EMERGING | Repeated demand for a new feature/use case | 0.44 |
| PAYMENT_PREFERENCE_SHIFT | Payment-method preference changes | 0.50 |
| WALLET_SWITCHING | Customers show switching behaviour between providers | 0.56 |
| MERCHANT_PREFERENCE_SHIFT | Merchant payment preference changes | 0.54 |
| SAVINGS_BEHAVIOUR_SHIFT | Savings/investment behaviour changes | 0.42 |
| CREDIT_USAGE_SHIFT | Credit usage/repayment behaviour changes | 0.50 |
| AGENT_USAGE_SHIFT | Agent-channel usage changes | 0.44 |
| REMITTANCE_BEHAVIOUR_SHIFT | Remittance/corridor usage changes | 0.46 |
| TRUST_EROSION | Material trust/confidence deterioration | 0.68 |
| PUBLIC_BACKLASH | Material public backlash/controversy | 0.66 |
| CUSTOMER_CONFIDENCE_IMPROVEMENT | Meaningful improvement in customer confidence/adoption | 0.34 |

## 3.5 FINANCIAL_ECONOMIC — Financial & Economic Conditions

| subcategory_code / Event Type | Observable event | Base urgency |
|---|---|---|
| REVENUE_GROWTH_SIGNAL | Publicly observable material revenue growth signal | 0.42 |
| TRANSACTION_VOLUME_CHANGE | Material transaction-volume change | 0.48 |
| GMV_CHANGE | Material GMV/payment-volume change | 0.48 |
| DEPOSIT_GROWTH_CHANGE | Material deposit-balance/growth signal | 0.46 |
| CREDIT_DEFAULT_TREND | Material change in default/delinquency trend | 0.72 |
| LOAN_REPAYMENT_TREND | Material repayment behaviour change | 0.62 |
| INTERCHANGE_FEE_CHANGE | Interchange/scheme fee economics change | 0.72 |
| LIQUIDITY_STRESS | Liquidity stress affecting institutions/market | 0.82 |
| PRICING_COMPRESSION | Market pricing compression intensifies | 0.64 |
| MARGIN_PRESSURE | Observable margin pressure intensifies | 0.70 |
| FX_EXPOSURE_CHANGE | FX conditions materially change exposure | 0.76 |
| INFLATION_CHANGE | Inflation materially changes operating/customer economics | 0.62 |
| INTEREST_RATE_CHANGE | Policy/market rate change | 0.66 |
| CURRENCY_DEVALUATION | Material currency devaluation | 0.82 |
| CASH_SCARCITY | Material cash scarcity/liquidity constraint | 0.74 |
| CONSUMER_SPENDING_PRESSURE | Consumer spending pressure changes | 0.56 |
| SME_LIQUIDITY_STRESS | SME liquidity conditions deteriorate/improve materially | 0.58 |
| FUEL_OR_ENERGY_COST_SHOCK | Fuel/energy price shock affecting operating/distribution costs | 0.56 |

## 3.6 CAPITAL_PARTNERSHIP — Capital, Funding & Partnerships

| subcategory_code / Event Type | Observable event | Base urgency |
|---|---|---|
| VC_FUNDING | Equity funding round announced | 0.44 |
| DEBT_FINANCING | Debt facility/financing announced | 0.46 |
| BRIDGE_ROUND | Bridge financing announced | 0.44 |
| DOWN_ROUND | Down round announced | 0.56 |
| STRATEGIC_INVESTMENT | Strategic corporate/institutional investment | 0.52 |
| ACQUISITION | Acquisition announced/completed | 0.68 |
| MERGER | Merger announced/completed | 0.70 |
| IPO_SIGNAL | Formal IPO filing/preparation/public-market milestone | 0.50 |
| BANK_PARTNERSHIP | Bank partnership announced | 0.50 |
| FINTECH_PARTNERSHIP | Fintech-fintech partnership announced | 0.46 |
| TELCO_PARTNERSHIP | Telco partnership announced | 0.50 |
| GOVERNMENT_PARTNERSHIP | Government/public-sector partnership announced | 0.54 |
| INFRASTRUCTURE_PARTNERSHIP | Infrastructure-provider partnership announced | 0.52 |
| INTERNATIONAL_PARTNERSHIP | International strategic partnership announced | 0.48 |
| DISTRIBUTION_PARTNERSHIP | Distribution/channel partnership announced | 0.50 |
| MERCHANT_PARTNERSHIP | Material merchant/network partnership announced | 0.44 |
| ENTERPRISE_PARTNERSHIP | Material enterprise partnership announced | 0.46 |

## 3.7 MARKET_EXPANSION — Market Expansion & Cross-Border

| subcategory_code / Event Type | Observable event | Base urgency |
|---|---|---|
| COUNTRY_ENTRY | Fintech enters a new country | 0.62 |
| COUNTRY_EXIT | Fintech exits/suspends a country market | 0.66 |
| REGIONAL_EXPANSION | Multi-market/regional expansion announced | 0.58 |
| CITY_EXPANSION | Expansion into additional cities/regions | 0.42 |
| RURAL_EXPANSION | Rural/offline expansion | 0.42 |
| FRANCOPHONE_EXPANSION | Expansion into Francophone market(s) | 0.52 |
| DIASPORA_CORRIDOR_EXPANSION | New remittance/diaspora corridor launched | 0.54 |
| CROSS_BORDER_PRODUCT_EXPANSION | Cross-border product/corridor expansion | 0.56 |
| SME_SEGMENT_EXPANSION | Material push into SME/business segment | 0.48 |
| SECTOR_EXPANSION | Expansion into new industry vertical | 0.46 |
| DISTRIBUTION_EXPANSION | New distribution/channel footprint expansion | 0.48 |
| PAPSS_ADOPTION | PAPSS adoption/interoperability milestone | 0.52 |
| LOCAL_CURRENCY_SETTLEMENT | Local-currency settlement capability/milestone | 0.58 |
| REGIONAL_INTEROPERABILITY | New regional payment interoperability capability | 0.56 |
| COUNTRY_GM_HIRE | Country GM/market leader hired ahead of expansion | 0.40 |

## 3.8 FRAUD_RISK_TRUST — Fraud, Risk & Trust

| subcategory_code / Event Type | Observable event | Base urgency |
|---|---|---|
| FRAUD_PATTERN_EMERGING | New fraud pattern or scheme emerging | 0.88 |
| FRAUD_SPIKE | Material fraud-volume/loss spike | 0.94 |
| ACCOUNT_TAKEOVER_SPIKE | Account takeover trend increases | 0.92 |
| SOCIAL_ENGINEERING_SPIKE | Social engineering/phishing spike | 0.86 |
| KYC_ABUSE_PATTERN | KYC/verification abuse pattern detected | 0.88 |
| SYNTHETIC_IDENTITY_PATTERN | Synthetic identity abuse pattern detected | 0.90 |
| SUSPICIOUS_TRANSACTION_CLUSTER | Material suspicious-transaction pattern emerges | 0.88 |
| CHARGEBACK_SPIKE | Chargeback/dispute spike | 0.82 |
| MERCHANT_FRAUD_PATTERN | Merchant fraud pattern emerges | 0.88 |
| CREDIT_ABUSE_PATTERN | Credit/loan abuse pattern emerges | 0.82 |
| AML_RISK_CLUSTER | AML-risk pattern/cluster emerges | 0.90 |
| CYBERSECURITY_INCIDENT | Cybersecurity incident affecting ecosystem participant | 0.92 |
| DATA_BREACH | Confirmed material data breach | 0.96 |
| SCAM_CAMPAIGN | Scam campaign targets customers/ecosystem | 0.86 |
| BRAND_TRUST_INCIDENT | Trust-impacting incident with material business relevance | 0.72 |

# 4. SECONDARY TAG TAXONOMY

Tags provide extra context without creating additional top-level domains.

## 4.1 Capability / Technology Tags

`AI`  
`MACHINE_LEARNING`  
`BLOCKCHAIN`  
`STABLECOIN`  
`OPEN_BANKING`  
`API`  
`CLOUD`  
`BIOMETRICS`  
`DIGITAL_IDENTITY`  
`CYBERSECURITY`  
`FRAUD_TECH`  
`USSD`  
`POS`  
`QR`  
`CARDS`  
`REAL_TIME_PAYMENTS`

## 4.2 Product / Business Model Tags

`WALLET`  
`MERCHANT_ACQUIRING`  
`PAYMENT_PROCESSING`  
`MOBILE_MONEY`  
`DIGITAL_BANKING`  
`LENDING`  
`SME_LENDING`  
`BNPL`  
`SAVINGS_INVESTMENT`  
`REMITTANCE`  
`CROSS_BORDER_PAYMENTS`  
`OPEN_BANKING_INFRA`  
`BaaS`  
`CARD_INFRASTRUCTURE`  
`AGENT_BANKING`  
`CREDIT_INFRASTRUCTURE`

## 4.3 Customer / Segment Tags

`CONSUMER`  
`SME`  
`MERCHANT`  
`ENTERPRISE`  
`AGENT`  
`DIASPORA`  
`RURAL`  
`WOMEN`  
`YOUTH`  
`INFORMAL_ECONOMY`

## 4.4 Geographic / Market Tags

Use canonical entity IDs from the Entity Registry wherever possible. String tags are only secondary convenience labels.

Examples:

`NG` `GH` `KE` `ZA` `EG` `WAF` `EAF`

---

# 5. GLOBAL URGENCY MODEL

## 5.1 Separation of Concepts

**Confidence** answers: *How strongly supported is the factual event?*

**Global Urgency** answers: *How time-sensitive or disruptive is the event in the external fintech environment?*

**Tenant Relevance** answers: *Does this event apply to this fintech?*

**Personal Priority** answers: *Does this event deserve this user's attention given their Decision Lens and Focus Areas?*

Never collapse these four concepts into one score.

## 5.2 Event-Level Urgency

The Event Type row provides `urgency_weight`.

Global urgency may then be adjusted deterministically using:
- authoritative-source confidence;
- corroboration;
- active/in-progress status;
- deadline proximity;
- incident severity/status where known.

Global urgency must not use tenant business context.

## 5.3 Example

`PAYMENT_RAIL_OUTAGE` may have global urgency `0.96`.

Tenant A may have relevance `0.95` because NIBSS is a configured dependency.

Tenant B may have relevance `0.18` because the affected rail is not part of its configured stack.

The event remains globally urgent while business relevance differs by tenant.

---

# 6. DECISION TAXONOMY

Decision Taxonomy is not part of `config.signal_taxonomy`. It is used by `config.decision_rules` and persisted in `decision.assessments`.

## 6.1 Canonical Exposure Types

- `PRODUCT`
- `MARKET`
- `INFRASTRUCTURE_DEPENDENCY`
- `CUSTOMER_SEGMENT`
- `REGULATORY_OBLIGATION`
- `ACTIVE_INITIATIVE`
- `PARTNER`
- `REVENUE_STREAM`
- `PRICING`
- `DISTRIBUTION`
- `OPERATIONS`
- `CAPITAL`


## 6.2 Canonical Stakes Types

- `REVENUE`
- `COST`
- `MARGIN`
- `CUSTOMER`
- `REGULATORY`
- `OPERATIONAL`
- `EXECUTION`
- `PRODUCT`
- `MARKET`
- `PARTNERSHIP`
- `REPUTATION`
- `CAPITAL`
- `SECURITY`
- `TRUST`


## 6.3 Canonical Decision Types

- `REGULATORY_IMPLEMENTATION`
- `PRODUCT_CHANGE`
- `PRODUCT_LAUNCH_GO_NO_GO`
- `PRICING_RESPONSE`
- `REROUTE_OR_FAILOVER`
- `CUSTOMER_COMMUNICATION`
- `PARTNER_ESCALATION`
- `MARKET_ENTRY`
- `MARKET_EXIT`
- `COMPETITOR_RESPONSE`
- `ROADMAP_REPRIORITISATION`
- `VENDOR_REVIEW`
- `PARTNERSHIP_ASSESSMENT`
- `CAPITAL_ALLOCATION`
- `RISK_CONTROL_CHANGE`
- `INCIDENT_RESPONSE`
- `COMPLIANCE_ESCALATION`
- `MONITOR_ONLY`


## 6.4 Canonical Owner Role Codes

- `CEO`
- `CSO`
- `COO`
- `CFO`
- `PRODUCT`
- `GROWTH`
- `COMPLIANCE_RISK`
- `RESEARCH`
- `LEGAL`
- `OTHER`

## 6.5 Decision Ownership Rule

`owner_role_codes` are **suggested responsible functions**, not an autonomous assignment.

The human organisation remains responsible for ownership, escalation and final action.

A signal may produce:
- `decision_required = FALSE` and `decision_type = MONITOR_ONLY`; or
- `decision_required = TRUE` with one primary `decision_type`.

---

# 7. INITIAL MVP DECISION RULES

The following rules seed `config.decision_rules`. They are intentionally conservative.

They require Company Context matches before a global event becomes a tenant Decision Brief.


## DR-REG-001 — REGULATORY_PRODUCT_APPLICABILITY

**Domain:** `REGULATORY_POLICY`

**Conditions:**
```json
{
  "event_types": [
    "KYC_REQUIREMENT_CHANGED",
    "IDENTITY_REQUIREMENT_CHANGED",
    "TRANSACTION_LIMIT_CHANGED",
    "CONSUMER_PROTECTION_RULE_CHANGED"
  ],
  "requires_any_context_match": [
    "PRODUCT",
    "REGULATORY_CATEGORY",
    "MARKET"
  ]
}
```

**Output contract:**
```json
{
  "exposure_types": [
    "PRODUCT",
    "REGULATORY_OBLIGATION"
  ],
  "stakes_types": [
    "REGULATORY",
    "EXECUTION",
    "CUSTOMER"
  ],
  "decision_required": true,
  "decision_type": "REGULATORY_IMPLEMENTATION",
  "owner_role_codes": [
    "PRODUCT",
    "COMPLIANCE_RISK",
    "COO"
  ]
}
```

## DR-INF-001 — CRITICAL_DEPENDENCY_INCIDENT

**Domain:** `INFRASTRUCTURE_RELIABILITY`

**Conditions:**
```json
{
  "event_types": [
    "ACTIVE_OUTAGE",
    "PAYMENT_RAIL_OUTAGE",
    "SETTLEMENT_DELAY",
    "SWITCH_OUTAGE",
    "BANK_INTEGRATION_FAILURE",
    "CLOUD_INCIDENT"
  ],
  "requires_context_match": "INFRASTRUCTURE_DEPENDENCY"
}
```

**Output contract:**
```json
{
  "exposure_types": [
    "INFRASTRUCTURE_DEPENDENCY",
    "OPERATIONS"
  ],
  "stakes_types": [
    "OPERATIONAL",
    "REVENUE",
    "CUSTOMER"
  ],
  "decision_required": true,
  "decision_type": "REROUTE_OR_FAILOVER",
  "owner_role_codes": [
    "COO",
    "PRODUCT",
    "CFO",
    "CEO"
  ]
}
```

## DR-COMP-001 — DIRECT_COMPETITOR_PRICING_MOVE

**Domain:** `COMPETITIVE_PRODUCT`

**Conditions:**
```json
{
  "event_types": [
    "PRICING_REDUCTION",
    "PRICING_INCREASE",
    "FX_SPREAD_CHANGED"
  ],
  "requires_context_match": "COMPETITOR"
}
```

**Output contract:**
```json
{
  "exposure_types": [
    "PRICING",
    "REVENUE_STREAM",
    "CUSTOMER_SEGMENT"
  ],
  "stakes_types": [
    "REVENUE",
    "MARGIN",
    "MARKET",
    "CUSTOMER"
  ],
  "decision_required": true,
  "decision_type": "PRICING_RESPONSE",
  "owner_role_codes": [
    "CFO",
    "CSO",
    "CEO",
    "PRODUCT"
  ]
}
```

## DR-EXP-001 — FOCUS_MARKET_ENTRY_SIGNAL

**Domain:** `MARKET_EXPANSION`

**Conditions:**
```json
{
  "event_types": [
    "COUNTRY_ENTRY",
    "REGIONAL_EXPANSION",
    "CROSS_BORDER_PRODUCT_EXPANSION"
  ],
  "requires_any_context_match": [
    "FOCUS_AREA",
    "MARKET",
    "COMPETITOR"
  ]
}
```

**Output contract:**
```json
{
  "exposure_types": [
    "MARKET",
    "ACTIVE_INITIATIVE"
  ],
  "stakes_types": [
    "MARKET",
    "EXECUTION",
    "CAPITAL"
  ],
  "decision_required": true,
  "decision_type": "MARKET_ENTRY",
  "owner_role_codes": [
    "CSO",
    "CEO",
    "CFO",
    "PRODUCT"
  ]
}
```

## DR-RISK-001 — MATERIAL_FRAUD_OR_SECURITY_SIGNAL

**Domain:** `FRAUD_RISK_TRUST`

**Conditions:**
```json
{
  "event_types": [
    "FRAUD_SPIKE",
    "DATA_BREACH",
    "CYBERSECURITY_INCIDENT",
    "ACCOUNT_TAKEOVER_SPIKE",
    "KYC_ABUSE_PATTERN"
  ],
  "requires_any_context_match": [
    "PRODUCT",
    "MARKET",
    "CUSTOMER_SEGMENT",
    "INFRASTRUCTURE_DEPENDENCY"
  ]
}
```

**Output contract:**
```json
{
  "exposure_types": [
    "PRODUCT",
    "CUSTOMER_SEGMENT",
    "OPERATIONS"
  ],
  "stakes_types": [
    "SECURITY",
    "TRUST",
    "REPUTATION",
    "REVENUE"
  ],
  "decision_required": true,
  "decision_type": "RISK_CONTROL_CHANGE",
  "owner_role_codes": [
    "COMPLIANCE_RISK",
    "COO",
    "PRODUCT",
    "CEO"
  ]
}
```

# 8. DECISION RELEVANCE PROCESSING CONTRACT

For every sufficiently trusted Global Intelligence Output:

```text
1. Read signal domain + Event Type + entities + region + confidence + global urgency.
2. Load tenant Company Context.
3. Evaluate applicability:
   - product matches
   - market matches
   - infrastructure dependency matches
   - competitor matches
   - customer segment matches
   - regulatory category matches
   - active initiative matches
4. Evaluate active config.decision_rules.
5. Create/update decision.assessments.
6. If relevance threshold and/or decision-rule threshold is met:
   - create company-level Decision Brief;
   - evaluate user Decision Lenses;
   - generate user-personalised Decision Briefs where personal priority threshold is met.
7. Preserve rationale, rule version, matched business objects and uncertainty codes.
```

No Decision Brief may claim tenant-specific financial exposure that has not been provided or derived from authorised tenant data.

---

# 9. DECISION LENS MAPPING

The Signal Taxonomy does not encode fixed roles. Role relevance is computed later.

Suggested V1 default interests:

| Role | Default high-interest decision areas |
|---|---|
| CEO | Material revenue/risk, strategic competitor moves, expansion, major regulatory/infrastructure events |
| CSO | Competition, expansion, partnerships, market structure, strategic regulatory implications |
| COO | Infrastructure reliability, partners, payment rails, execution and incident response |
| CFO | Pricing, margin, cost, FX, transaction economics, capital/funding |
| PRODUCT | Product regulation, competitor products, customer behaviour, infrastructure affecting UX/launch |
| GROWTH | Distribution, acquisition, customer shifts, competitive campaigns, market expansion |
| COMPLIANCE_RISK | Regulatory implementation, fraud/risk, identity, enforcement and controls |
| RESEARCH | Wider market intelligence, historical patterns, evidence collection |

These are onboarding defaults only. Users may override them.

---

# 10. LEGACY TAXONOMY → V2 MIGRATION MAP

| Legacy domain | V2 destination | Migration rule |
|---|---|---|
| D01 Regulatory Signals | REGULATORY_POLICY | Preserve event catalogue; code as regulatory Event Types. |
| D02 Competitive Signals | COMPETITIVE_PRODUCT | Merge with old Product signals; retain pricing, launches, expansion and competitive movement. |
| D03 Consumer Signals | CUSTOMER_MARKET | Merge with behavioural and selected reputation signals. |
| D04 Operational Signals | INFRASTRUCTURE_RELIABILITY | Merge outage/degradation/settlement/API reliability events. |
| D05 Financial Signals | FINANCIAL_ECONOMIC | Keep economic/financial conditions; tenant-specific economics remain outside global taxonomy. |
| D06 Infrastructure Signals | INFRASTRUCTURE_RELIABILITY | Merge with Operational and Payment Rail. |
| D07 Ecosystem Signals | Secondary tags / event families | Do not use as a primary domain unless event fits Capital/Partnership, Market Expansion or Competitive/Product. |
| D08 Market Expansion Signals | MARKET_EXPANSION | Keep and merge with Cross-Border/Distribution. |
| D09 Fraud & Risk Signals | FRAUD_RISK_TRUST | Keep and merge selected identity/trust/reputation events. |
| D10 Partnership Signals | CAPITAL_PARTNERSHIP | Merge with Capital & Funding. |
| D11 Product Signals | COMPETITIVE_PRODUCT | Merge with Competitive; feature/product changes become Event Types. |
| D12 Talent & Organization Signals | Secondary event family | Route material executive/restructure events to Competitive/Product; keep other talent items as tags. |
| D13 Capital & Funding Signals | CAPITAL_PARTNERSHIP | Keep and merge partnerships. |
| D14 Macroeconomic Signals | FINANCIAL_ECONOMIC | Merge. |
| D15 Cross-Border Signals | MARKET_EXPANSION | Merge. |
| D16 Technology Signals | Tags, not primary domain | AI/cloud/blockchain/biometric become capability tags attached to the actual business event. |
| D17 Reputation Signals | CUSTOMER_MARKET or FRAUD_RISK_TRUST | Route based on underlying event. |
| D18 Behavioral Signals | CUSTOMER_MARKET | Merge. |
| D19 Distribution Signals | MARKET_EXPANSION or COMPETITIVE_PRODUCT | Route based on event. |
| D20 Strategic Signals | Derived interpretation only | Remove as raw primary domain. Strategic conclusions come from clustering/synthesis of observable events. |
| D21 Financial Inclusion Signals | Tags / customer-market subcategory | Use inclusion segment tags such as RURAL, WOMEN, YOUTH, SME, INFORMAL_ECONOMY. |
| D22 Identity & Trust Signals | REGULATORY_POLICY or FRAUD_RISK_TRUST | Route rule changes to Regulatory; abuse/failure/trust incidents to Fraud/Risk/Trust. |
| D23 Payment Rail Signals | INFRASTRUCTURE_RELIABILITY | Merge. |

# 11. RAW-DOMAIN REMOVALS / DEPRECATIONS

The following codes must not be used as V2 primary domains:

`OPERATIONAL`  
`INFRASTRUCTURE`  
`PAYMENT_RAIL`  
`CONSUMER`  
`BEHAVIORAL`  
`REPUTATION`  
`PRODUCT`  
`PARTNERSHIP`  
`CAPITAL_FUNDING`  
`MACROECONOMIC`  
`CROSS_BORDER`  
`DISTRIBUTION`  
`TECHNOLOGY`  
`ECOSYSTEM`  
`STRATEGIC`  
`FINANCIAL_INCLUSION`  
`IDENTITY_TRUST`

They may remain as migration aliases/tags only.

Historical signals should be reclassified lazily or via one-time migration where practical.

---

# 12. DATABASE / MIGRATION INSTRUCTIONS

## 12.1 Canonical Migration Number

This seed belongs to:

**Migration 0003 — Config Tables**

It must not use the old `0004_signal_taxonomy_seed` name.

SC-DOC-010 v2.0.0 reserves:
- `0001` — schema namespaces
- `0002` — auth tables
- `0003` — config tables + V2 taxonomy / decision rules
- `0004` — pipeline tables
- `0005` — intelligence tables
- `0006` — Company Context tables
- later migrations — Decision, delivery, CIL, feedback, billing and audit

## 12.2 Required Tables

This file assumes these canonical schemas from SC-DOC-003 v2.0.0:

```sql
CREATE TABLE config.signal_taxonomy (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_code      VARCHAR(50) NOT NULL,
    subcategory_code VARCHAR(100) NOT NULL,
    keyword_patterns JSONB NOT NULL DEFAULT '[]',
    entity_rules     JSONB NOT NULL DEFAULT '{}',
    urgency_weight   NUMERIC(4,3) NOT NULL DEFAULT 0.50,
    version          VARCHAR(20) NOT NULL,
    active           BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(domain_code, subcategory_code, version)
);

CREATE TABLE config.decision_rules (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_code          VARCHAR(100) NOT NULL UNIQUE,
    name               VARCHAR(255) NOT NULL,
    domain_code        VARCHAR(50),
    conditions         JSONB NOT NULL,
    output_contract    JSONB NOT NULL,
    priority           INTEGER NOT NULL DEFAULT 100,
    version            VARCHAR(20) NOT NULL,
    active             BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

# 13. SQL SEED — CANONICAL DOMAIN / EVENT ROWS

The application should generate the final migration from the canonical catalogue above.

At minimum the seed format is:

```sql
INSERT INTO config.signal_taxonomy
(domain_code, subcategory_code, keyword_patterns, entity_rules, urgency_weight, version, active)
VALUES
('REGULATORY_POLICY', 'CIRCULAR_ISSUED', '[]'::jsonb, '{}'::jsonb, 0.72, '2026.08-v2', TRUE),
('REGULATORY_POLICY', 'ENFORCEMENT_ACTION', '[]'::jsonb, '{}'::jsonb, 0.95, '2026.08-v2', TRUE),
('COMPETITIVE_PRODUCT', 'PRICING_REDUCTION', '[]'::jsonb, '{}'::jsonb, 0.70, '2026.08-v2', TRUE),
('INFRASTRUCTURE_RELIABILITY', 'PAYMENT_RAIL_OUTAGE', '[]'::jsonb, '{}'::jsonb, 0.96, '2026.08-v2', TRUE),
('CUSTOMER_MARKET', 'COMPLAINT_VOLUME_SPIKE', '[]'::jsonb, '{}'::jsonb, 0.68, '2026.08-v2', TRUE),
('FINANCIAL_ECONOMIC', 'MARGIN_PRESSURE', '[]'::jsonb, '{}'::jsonb, 0.70, '2026.08-v2', TRUE),
('CAPITAL_PARTNERSHIP', 'ACQUISITION', '[]'::jsonb, '{}'::jsonb, 0.68, '2026.08-v2', TRUE),
('MARKET_EXPANSION', 'COUNTRY_ENTRY', '[]'::jsonb, '{}'::jsonb, 0.62, '2026.08-v2', TRUE),
('FRAUD_RISK_TRUST', 'DATA_BREACH', '[]'::jsonb, '{}'::jsonb, 0.96, '2026.08-v2', TRUE);
```

**Important:** Production migration must seed every Event Type listed in Section 3, not only the examples above.

Keyword and entity rules are intentionally not fabricated in this document. They should be added from validated source examples during the rules-first classifier implementation.

---

# 14. INITIAL DECISION-RULE SQL FORMAT

Example:

```sql
INSERT INTO config.decision_rules
(rule_code, name, domain_code, conditions, output_contract, priority, version, active)
VALUES
(
  'DR-INF-001',
  'CRITICAL_DEPENDENCY_INCIDENT',
  'INFRASTRUCTURE_RELIABILITY',
  '{
     "event_types":["ACTIVE_OUTAGE","PAYMENT_RAIL_OUTAGE","SETTLEMENT_DELAY","SWITCH_OUTAGE","BANK_INTEGRATION_FAILURE","CLOUD_INCIDENT"],
     "requires_context_match":"INFRASTRUCTURE_DEPENDENCY"
   }'::jsonb,
  '{
     "exposure_types":["INFRASTRUCTURE_DEPENDENCY","OPERATIONS"],
     "stakes_types":["OPERATIONAL","REVENUE","CUSTOMER"],
     "decision_required":true,
     "decision_type":"REROUTE_OR_FAILOVER",
     "owner_role_codes":["COO","PRODUCT","CFO","CEO"]
   }'::jsonb,
  20,
  '2026.08-v2',
  TRUE
);
```

Decision rules are starting hypotheses. They must be adjusted from pilot feedback without changing the canonical meanings of Event Type codes.

---

# 15. CLASSIFIER OUTPUT CONTRACT

Rules-first classification returns:

```json
{
  "primary_domain": "INFRASTRUCTURE_RELIABILITY",
  "event_type": "PAYMENT_RAIL_OUTAGE",
  "secondary_tags": ["REAL_TIME_PAYMENTS"],
  "entity_ids": ["<entity-uuid>"],
  "region_tags": ["NG"],
  "classification_confidence": 0.93,
  "classification_method": "RULE_BASED",
  "taxonomy_version": "2026.08-v2"
}
```

The classifier does not return:
- tenant relevance;
- business exposure;
- stakes;
- decision type;
- owner role;
- exact financial impact.

Those are downstream decision-layer outputs.

---

# 16. QUALITY / ACCEPTANCE TESTS

Migration 0003 taxonomy work is complete when:

- [ ] Exactly eight active V2 top-level `domain_code` values exist.
- [ ] Every Event Type in Section 3 is seeded.
- [ ] No old top-level domain is emitted by the V2 classifier.
- [ ] `STRATEGIC` cannot be produced as a primary raw domain.
- [ ] Event Type-specific urgency is available.
- [ ] Global urgency does not read tenant context.
- [ ] Company relevance does not mutate global signal truth.
- [ ] Initial `config.decision_rules` are seeded and versioned.
- [ ] Decision rules require relevant context matches where specified.
- [ ] No decision rule fabricates monetary exposure.
- [ ] Role codes match the V2 Decision Lens vocabulary.
- [ ] Taxonomy version is returned with every classification.
- [ ] Rules are hot-reloadable without redeploy.
- [ ] Old `0004_signal_taxonomy_seed` instruction is removed from engineering execution.
- [ ] Advanced ML is not required for acceptance.

---

# 17. EXAMPLE END-TO-END CASES

## 17.1 Regulatory

**Observed event:** CBN changes wallet transaction limits.

Global classification:

```text
REGULATORY_POLICY
→ TRANSACTION_LIMIT_CHANGED
```

Company Context match:

```text
Product: Wallet
Market: Nigeria
Regulatory category: Mobile Money
```

Decision assessment may produce:

```text
Exposure: PRODUCT, REGULATORY_OBLIGATION
Stakes: REGULATORY, EXECUTION, CUSTOMER
Decision Type: REGULATORY_IMPLEMENTATION
Owners: PRODUCT, COMPLIANCE_RISK, COO
```

## 17.2 Infrastructure

**Observed event:** NIBSS rail outage.

Global classification:

```text
INFRASTRUCTURE_RELIABILITY
→ PAYMENT_RAIL_OUTAGE
```

Company Context match:

```text
Dependency: NIBSS
Product: Merchant Transfers
```

Decision assessment may produce:

```text
Exposure: INFRASTRUCTURE_DEPENDENCY, OPERATIONS
Stakes: OPERATIONAL, REVENUE, CUSTOMER
Decision Type: REROUTE_OR_FAILOVER
Owners: COO, PRODUCT, CFO, CEO
```

## 17.3 Competitive Pricing

**Observed event:** Configured competitor reduces merchant fees.

Global classification:

```text
COMPETITIVE_PRODUCT
→ PRICING_REDUCTION
```

Company Context / Focus match:

```text
Configured competitor: TRUE
Customer segment: SME merchants
Focus Area: Merchant profitability
```

Decision assessment may produce:

```text
Exposure: PRICING, REVENUE_STREAM, CUSTOMER_SEGMENT
Stakes: REVENUE, MARGIN, MARKET, CUSTOMER
Decision Type: PRICING_RESPONSE
Owners: CFO, CSO, CEO, PRODUCT
```

Stem Cogent must not tell the company to lower price automatically. It tells the company that a pricing decision deserves attention and preserves the evidence supporting that assessment.

---

# 18. SOURCE-OF-TRUTH RULE

This document is the canonical launch seed specification for:

- V2 Signal Taxonomy;
- Event Type vocabulary;
- Event-level base urgency;
- Decision Type vocabulary;
- Exposure Type vocabulary;
- Stakes Type vocabulary;
- initial Decision Rules;
- legacy taxonomy migration mapping.

If another implementation document conflicts with these codes or meanings, update the downstream implementation to this specification unless a later approved version supersedes it.

**End of SC-SEED-002 v2.0.0**
