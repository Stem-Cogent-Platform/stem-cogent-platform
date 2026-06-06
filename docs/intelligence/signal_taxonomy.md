# STEM COGENT — ENTITY REGISTRY & SIGNAL TAXONOMY SEED DATA

**Document Version:** 1.0.0
**Purpose:** Complete seed data for `intelligence.entities` and `config.signal_taxonomy` tables.
**Use:** Run these lists via `infrastructure/scripts/seed_entity_registry.py`
and the taxonomy migration `0004_signal_taxonomy_seed`.

---

# PART A — ENTITY REGISTRY

Total entities at launch: **147**
Organized by entity type. All are Nigerian-primary, Africa-relevant.

---

## 1. REGULATORY BODIES (19 entities)

| # | Canonical Name | Aliases | Type | Region |
|---|---|---|---|---|
| 1 | Central Bank of Nigeria | CBN, apex bank, the bank | REGULATOR_NG | NG |
| 2 | Securities and Exchange Commission Nigeria | SEC Nigeria, SEC, Nigerian SEC | REGULATOR_NG | NG |
| 3 | National Data Protection Commission | NDPC, Nigeria NDPC | REGULATOR_NG | NG |
| 4 | NIBSS | Nigeria Inter-Bank Settlement System, NIBSS Plc | FINANCIAL_INFRA | NG |
| 5 | Federal Competition and Consumer Protection Commission | FCCPC, Nigeria FCCPC | REGULATOR_NG | NG |
| 6 | National Insurance Commission | NAICOM | REGULATOR_NG | NG |
| 7 | Corporate Affairs Commission | CAC, Nigerian CAC | REGULATOR_NG | NG |
| 8 | National Communications Commission | NCC, Nigeria NCC | REGULATOR_NG | NG |
| 9 | Federal Inland Revenue Service | FIRS | REGULATOR_NG | NG |
| 10 | Nigerian Deposit Insurance Corporation | NDIC | REGULATOR_NG | NG |
| 11 | Financial Reporting Council of Nigeria | FRCN | REGULATOR_NG | NG |
| 12 | Special Control Unit Against Money Laundering | SCUML | REGULATOR_NG | NG |
| 13 | Nigerian Financial Intelligence Unit | NFIU | REGULATOR_NG | NG |
| 14 | Economic and Financial Crimes Commission | EFCC | REGULATOR_NG | NG |
| 15 | Ghana Revenue Authority | GRA Ghana | REGULATOR_NG | GH |
| 16 | Bank of Ghana | BoG, Ghana central bank | REGULATOR_NG | GH |
| 17 | Central Bank of Kenya | CBK | REGULATOR_NG | KE |
| 18 | South African Reserve Bank | SARB | REGULATOR_NG | ZA |
| 19 | Central Bank of Egypt | CBE | REGULATOR_NG | EG |

---

## 2. NIGERIAN FINTECH COMPANIES (42 entities)

| # | Canonical Name | Aliases | Type | Sector |
|---|---|---|---|---|
| 1 | Flutterwave | Flutterwave Inc, FLW | FINTECH_CO | PAYMENT_PROCESSING |
| 2 | Paystack | Paystack Inc | FINTECH_CO | PAYMENT_PROCESSING |
| 3 | Moniepoint | Moniepoint Inc, TeamApt | FINTECH_CO | BUSINESS_BANKING |
| 4 | OPay | OPay Digital Services, Opera Pay | FINTECH_CO | MOBILE_MONEY |
| 5 | Kuda Bank | Kuda, Kuda Microfinance Bank | FINTECH_CO | DIGITAL_BANKING |
| 6 | PalmPay | PalmPay Ltd | FINTECH_CO | MOBILE_MONEY |
| 7 | Chipper Cash | ChipperCash | FINTECH_CO | CROSS_BORDER_PAYMENTS |
| 8 | Carbon | Carbon Nigeria, OneFi | FINTECH_CO | LENDING |
| 9 | FairMoney | FairMoney Microfinance Bank | FINTECH_CO | LENDING |
| 10 | Branch International | Branch Nigeria | FINTECH_CO | LENDING |
| 11 | Renmoney | Renmoney Microfinance Bank | FINTECH_CO | LENDING |
| 12 | Cowrywise | Cowrywise Technologies | FINTECH_CO | SAVINGS_INVESTMENT |
| 13 | Piggyvest | PiggyVest, Piggybank.ng | FINTECH_CO | SAVINGS_INVESTMENT |
| 14 | Bamboo | Bamboo Invest | FINTECH_CO | SAVINGS_INVESTMENT |
| 15 | Risevest | Rise, Rise Vest | FINTECH_CO | SAVINGS_INVESTMENT |
| 16 | Paga | Paga Nigeria | FINTECH_CO | MOBILE_MONEY |
| 17 | Bankly | Bankly Nigeria | FINTECH_CO | AGENT_BANKING |
| 18 | Lidya | Lidya Nigeria | FINTECH_CO | SME_LENDING |
| 19 | Migo | Migo Money, Mines.io | FINTECH_CO | LENDING |
| 20 | Indicina | Indicina Technologies | FINTECH_CO | CREDIT_INFRASTRUCTURE |
| 21 | Mono | Mono Africa | FINTECH_CO | OPEN_BANKING |
| 22 | Okra | Okra Technologies | FINTECH_CO | OPEN_BANKING |
| 23 | OnePipe | OnePipe Nigeria | FINTECH_CO | OPEN_BANKING |
| 24 | Stitch | Stitch Money | FINTECH_CO | OPEN_BANKING |
| 25 | Sudo Africa | Sudo | FINTECH_CO | CARD_INFRASTRUCTURE |
| 26 | Union54 | Union 54 | FINTECH_CO | CARD_INFRASTRUCTURE |
| 27 | Brass | Brass Business Banking | FINTECH_CO | BUSINESS_BANKING |
| 28 | Prospa | Prospa Africa | FINTECH_CO | BUSINESS_BANKING |
| 29 | Anchor | Anchor HQ | FINTECH_CO | BANKING_AS_SERVICE |
| 30 | Bloc | Bloc Finance | FINTECH_CO | BANKING_AS_SERVICE |
| 31 | Lendsqr | LendSqr | FINTECH_CO | LENDING_INFRASTRUCTURE |
| 32 | CredPal | CredPal Nigeria | FINTECH_CO | BNPL |
| 33 | CDcare | CDCare Nigeria | FINTECH_CO | BNPL |
| 34 | Kippa | Kippa Africa | FINTECH_CO | SME_TOOLS |
| 35 | Bumpa | Bumpa Africa | FINTECH_CO | SME_TOOLS |
| 36 | Monnify | Monnify Payments | FINTECH_CO | PAYMENT_PROCESSING |
| 37 | Fincra | Fincra Africa | FINTECH_CO | CROSS_BORDER_PAYMENTS |
| 38 | Leatherback | Leatherback Africa | FINTECH_CO | CROSS_BORDER_PAYMENTS |
| 39 | Grey | Grey Finance | FINTECH_CO | CROSS_BORDER_PAYMENTS |
| 40 | Sendstack | SendStack Africa | FINTECH_CO | LOGISTICS_FINTECH |
| 41 | Klasha | Klasha Finance | FINTECH_CO | CROSS_BORDER_PAYMENTS |
| 42 | Nomba | Nomba Financial Services | FINTECH_CO | POS_PAYMENTS |

---

## 3. NIGERIAN BANKS (17 entities)

| # | Canonical Name | Aliases | Type | Sector |
|---|---|---|---|---|
| 1 | Access Bank | Access Bank Nigeria, Access Bank Plc | COMPANY | BANKING |
| 2 | Zenith Bank | Zenith Bank Plc | COMPANY | BANKING |
| 3 | GTBank | Guaranty Trust Bank, GTB, GTCO | COMPANY | BANKING |
| 4 | First Bank of Nigeria | First Bank, FBN | COMPANY | BANKING |
| 5 | United Bank for Africa | UBA | COMPANY | BANKING |
| 6 | Ecobank Nigeria | Ecobank | COMPANY | BANKING |
| 7 | Fidelity Bank | Fidelity Bank Nigeria | COMPANY | BANKING |
| 8 | Sterling Bank | Sterling Bank Nigeria | COMPANY | BANKING |
| 9 | Stanbic IBTC | Stanbic IBTC Bank | COMPANY | BANKING |
| 10 | Union Bank Nigeria | Union Bank | COMPANY | BANKING |
| 11 | Wema Bank | Wema Bank Nigeria, ALAT by Wema | COMPANY | BANKING |
| 12 | Polaris Bank | Polaris Bank Nigeria | COMPANY | BANKING |
| 13 | Providus Bank | ProvidusBank | COMPANY | BANKING |
| 14 | Jaiz Bank | Jaiz Bank Nigeria | COMPANY | ISLAMIC_BANKING |
| 15 | Keystone Bank | Keystone Bank Nigeria | COMPANY | BANKING |
| 16 | FCMB | First City Monument Bank | COMPANY | BANKING |
| 17 | VFD Microfinance Bank | VFD MFB, VFD Group | COMPANY | MICROFINANCE |

---

## 4. PAYMENT & FINANCIAL INFRASTRUCTURE (15 entities)

| # | Canonical Name | Aliases | Type | Sector |
|---|---|---|---|---|
| 1 | Interswitch | Interswitch Group, Quickteller | FINANCIAL_INFRA | PAYMENT_SWITCHING |
| 2 | eTranzact | eTranzact International | FINANCIAL_INFRA | PAYMENT_SWITCHING |
| 3 | SystemSpecs | SystemSpecs Nigeria, Remita | FINANCIAL_INFRA | PAYMENT_PROCESSING |
| 4 | Unified Payments | Unified Payments Nigeria | FINANCIAL_INFRA | PAYMENT_PROCESSING |
| 5 | Verve International | Verve Card | FINANCIAL_INFRA | CARD_SCHEME |
| 6 | Mastercard Nigeria | Mastercard | FINANCIAL_INFRA | CARD_SCHEME |
| 7 | Visa Nigeria | Visa Inc Nigeria | FINANCIAL_INFRA | CARD_SCHEME |
| 8 | UnionPay Nigeria | Union Pay | FINANCIAL_INFRA | CARD_SCHEME |
| 9 | PAPSS | Pan-African Payment and Settlement System | FINANCIAL_INFRA | CROSS_BORDER_INFRASTRUCTURE |
| 10 | Network International | Network Intl | FINANCIAL_INFRA | PAYMENT_PROCESSING |
| 11 | DPO Group | DPO Pay | FINANCIAL_INFRA | PAYMENT_PROCESSING |
| 12 | Paymentology | Paymentology Africa | FINANCIAL_INFRA | CARD_INFRASTRUCTURE |
| 13 | NIP | Nigeria Instant Payment, NIP Scheme | FINANCIAL_INFRA | PAYMENT_RAIL |
| 14 | RTGS | Real-Time Gross Settlement | FINANCIAL_INFRA | PAYMENT_RAIL |
| 15 | NACS | Nigeria Automated Clearing System | FINANCIAL_INFRA | PAYMENT_RAIL |

---

## 5. TELECOM & INFRASTRUCTURE PROVIDERS (10 entities)

| # | Canonical Name | Aliases | Type | Sector |
|---|---|---|---|---|
| 1 | MTN Nigeria | MTN, MTN Nigeria Communications | INFRASTRUCTURE_PROVIDER | TELCO |
| 2 | Airtel Nigeria | Airtel Africa Nigeria | INFRASTRUCTURE_PROVIDER | TELCO |
| 3 | Glo Mobile | Globacom, Glo | INFRASTRUCTURE_PROVIDER | TELCO |
| 4 | 9mobile | 9Mobile Nigeria, Etisalat Nigeria | INFRASTRUCTURE_PROVIDER | TELCO |
| 5 | MTN MoMo | MTN Mobile Money, MoMo PSB | INFRASTRUCTURE_PROVIDER | MOBILE_MONEY_INFRA |
| 6 | Airtel Money | Airtel Mobile Commerce | INFRASTRUCTURE_PROVIDER | MOBILE_MONEY_INFRA |
| 7 | AWS Africa | Amazon Web Services Africa | INFRASTRUCTURE_PROVIDER | CLOUD |
| 8 | Microsoft Azure Africa | Azure Africa | INFRASTRUCTURE_PROVIDER | CLOUD |
| 9 | Google Cloud Nigeria | GCP Nigeria | INFRASTRUCTURE_PROVIDER | CLOUD |
| 10 | MainOne | MainOne Cable Company | INFRASTRUCTURE_PROVIDER | INTERNET_INFRASTRUCTURE |

---

## 6. LEGISLATION & DIRECTIVES (18 entities)

| # | Canonical Name | Aliases | Type |
|---|---|---|---|
| 1 | Finance Act 2020 | Finance Act Nigeria 2020 | LEGISLATION |
| 2 | Finance Act 2021 | Finance Act Nigeria 2021 | LEGISLATION |
| 3 | Finance Act 2022 | Finance Act Nigeria 2022 | LEGISLATION |
| 4 | Finance Act 2023 | Finance Act Nigeria 2023 | LEGISLATION |
| 5 | Banks and Other Financial Institutions Act | BOFIA 2020, BOFIA | LEGISLATION |
| 6 | Central Bank of Nigeria Act | CBN Act | LEGISLATION |
| 7 | Nigeria Data Protection Act | NDPA, NDPA 2023 | LEGISLATION |
| 8 | Nigeria Startup Act | Nigerian Startup Act 2022, Startup Act | LEGISLATION |
| 9 | Companies and Allied Matters Act | CAMA, CAMA 2020 | LEGISLATION |
| 10 | Federal Competition and Consumer Protection Act | FCCPA | LEGISLATION |
| 11 | Investment and Securities Act | ISA Nigeria | LEGISLATION |
| 12 | Money Laundering Prevention and Prohibition Act | MLPPA, MLPA | LEGISLATION |
| 13 | Cybercrime Act Nigeria | Cybercrime Prohibition Act | LEGISLATION |
| 14 | Electronic Transaction Act Nigeria | ETA Nigeria | LEGISLATION |
| 15 | Payment System Management Act | PSMA Nigeria | LEGISLATION |
| 16 | CBN Regulatory Framework for Mobile Money | Mobile Money Framework, MMO Framework | LEGISLATION |
| 17 | CBN Consumer Protection Framework | CPF CBN | LEGISLATION |
| 18 | National Financial Inclusion Strategy | NFIS, Nigeria NFIS | LEGISLATION |

---

## 7. INVESTORS & VC FIRMS ACTIVE IN NIGERIA/AFRICA (12 entities)

| # | Canonical Name | Aliases | Type | Sector |
|---|---|---|---|---|
| 1 | Sequoia Capital Africa | Sequoia Africa | COMPANY | VENTURE_CAPITAL |
| 2 | TLcom Capital | TLcom | COMPANY | VENTURE_CAPITAL |
| 3 | Partech Africa | Partech Partners Africa | COMPANY | VENTURE_CAPITAL |
| 4 | Lateral Capital | Lateral Cap | COMPANY | VENTURE_CAPITAL |
| 5 | Future Africa | FutureAfrica | COMPANY | VENTURE_CAPITAL |
| 6 | Ventures Platform | VenturesPlatform | COMPANY | VENTURE_CAPITAL |
| 7 | Catalyst Fund | Catalyst Fund Africa | COMPANY | IMPACT_INVESTING |
| 8 | Quona Capital | Quona | COMPANY | VENTURE_CAPITAL |
| 9 | Goodwell Investments | Goodwell | COMPANY | IMPACT_INVESTING |
| 10 | IFC | International Finance Corporation | COMPANY | DEVELOPMENT_FINANCE |
| 11 | African Development Bank | AfDB | COMPANY | DEVELOPMENT_FINANCE |
| 12 | FCDO | UK Foreign Commonwealth and Development Office | COMPANY | DEVELOPMENT_FINANCE |

---

## 8. KEY GEOGRAPHIC REGIONS (14 entities)

| # | Canonical Name | Aliases | Type | Code |
|---|---|---|---|---|
| 1 | Nigeria | Federal Republic of Nigeria | GEOGRAPHIC_REGION | NG |
| 2 | Lagos | Lagos State, Lagos Nigeria | GEOGRAPHIC_REGION | NG-LA |
| 3 | Abuja | FCT, Federal Capital Territory | GEOGRAPHIC_REGION | NG-FC |
| 4 | Kano | Kano State | GEOGRAPHIC_REGION | NG-KN |
| 5 | Rivers State | Rivers, Port Harcourt | GEOGRAPHIC_REGION | NG-RI |
| 6 | Ghana | Republic of Ghana | GEOGRAPHIC_REGION | GH |
| 7 | Kenya | Republic of Kenya, Nairobi | GEOGRAPHIC_REGION | KE |
| 8 | South Africa | SA, Republic of South Africa | GEOGRAPHIC_REGION | ZA |
| 9 | Egypt | Arab Republic of Egypt, Cairo | GEOGRAPHIC_REGION | EG |
| 10 | West Africa | West African region | GEOGRAPHIC_REGION | WAF |
| 11 | East Africa | East African region | GEOGRAPHIC_REGION | EAF |
| 12 | Francophone Africa | French-speaking Africa | GEOGRAPHIC_REGION | FRAF |
| 13 | Sub-Saharan Africa | SSA | GEOGRAPHIC_REGION | SSA |
| 14 | Africa | African continent | GEOGRAPHIC_REGION | AF |

---

## ENTITY REGISTRY SUMMARY

| Entity Type | Count |
|---|---|
| REGULATOR_NG | 19 |
| FINTECH_CO | 42 |
| COMPANY (Banks) | 17 |
| FINANCIAL_INFRA | 15 |
| INFRASTRUCTURE_PROVIDER | 10 |
| LEGISLATION | 18 |
| COMPANY (Investors) | 12 |
| GEOGRAPHIC_REGION | 14 |
| **Total** | **147** |

---

---

# PART B — SIGNAL TAXONOMY SEED DATA

20 macro domains with subcategories and urgency weights.
Urgency weight = the domain's contribution to the urgency scoring formula.
1.0 = maximum urgency weight; 0.0 = no urgency contribution.

---

Domain ID| Domain
D01| Regulatory Signals
D02| Competitive Signals
D03| Consumer Signals
D04| Operational Signals
D05| Financial Signals
D06| Infrastructure Signals
D07| Ecosystem Signals
D08| Market Expansion Signals
D09| Fraud & Risk Signals
D10| Partnership Signals
D11| Product Signals
D12| Talent & Organization Signals
D13| Capital & Funding Signals
D14| Macroeconomic Signals
D15| Cross-Border Signals
D16| Technology Signals
D17| Reputation Signals
D18| Behavioral Signals
D19| Distribution Signals
D20| Strategic Signals
D21| Financial Inclusion Signals
D22| Identity & Trust Signals
D23| Payment Rail Signals

---

### D01 — REGULATORY SIGNALS

Categories

CBN Policy Changes

- New circular issued
- Circular amendment
- Circular withdrawal
- Consultation paper issued
- Compliance deadline announced
- Enforcement timeline update

SEC Policy Changes

- Securities regulation update
- Digital asset regulation update
- Investment platform regulation

NDPC/Data Protection Enforcement

- Privacy enforcement notice
- Data breach sanction
- Compliance audit

KYC/AML Directives

- AML rule update
- KYC threshold update
- Suspicious reporting update

Open Banking Regulations

- API standard release
- Framework update
- New participant approval

Licensing Framework Changes

- New license category
- License approval
- License suspension
- License revocation

Consumer Protection Directives

- Consumer rights framework
- Complaint handling rules

Fraud Liability Rules

- Liability reassignment
- Fraud reimbursement update

Transaction Limit Changes

- Wallet limit update
- Transfer limit update

Cash Policy Changes

- Cash withdrawal policy
- Cashless policy update

CBDC Updates

- eNaira developments
- CBDC policy updates

Cross-Border Payment Regulation

- International transfer rules
- Regional settlement policies

Taxation Policy

- Digital services tax
- Financial services taxation

Telecom Regulation Affecting Fintech

- SIM registration rules
- USSD regulation

Banking API Standards

- API standards update
- Security standards update

Compliance Enforcement Notices

- Regulatory warning
- Enforcement action

Sanctions & Restrictions

- Regulatory sanctions
- Market restrictions

FX Policy Changes

- FX access policy
- FX market intervention

Identity Verification Requirements

- BVN requirements
- NIN requirements

Agent Banking Regulation

- Agent framework update
- Agent compliance requirements

---

### D02 — COMPETITIVE SIGNALS

Categories

New Product Launch

- Wallet launch
- Lending launch
- Savings launch
- Insurance launch
- Investment launch

Feature Rollout

- New feature deployment
- Feature enhancement

Pricing Changes

- Fee increase
- Fee reduction
- FX spread adjustment

Merchant Expansion

- Merchant acquisition surge
- Enterprise onboarding

Regional Expansion

- New city launch
- New country launch

API Launch

- Public API release
- Developer platform launch

Embedded Finance Rollout

- Banking-as-a-Service launch
- Embedded credit launch

POS Deployment Growth

- POS rollout expansion

Mobile App Redesign

- UX redesign
- Mobile platform relaunch

User Acquisition Campaigns

- Incentive campaigns
- Referral programs

Partnership Announcements

- Strategic partnership
- Commercial partnership

Infrastructure Investments

- Data center investment
- Switching infrastructure investment

Wallet Expansion

Super App Expansion

Cross-Border Expansion

Agent Network Expansion

SME Product Launch

Credit Product Launch

Savings Product Launch

BNPL Rollout

---

### D03 — CONSUMER SIGNALS

Categories

App Store Complaints

- Rating decline
- Complaint volume increase

Feature Demand

- Requested features
- Emerging customer needs

Transaction Failure Complaints

Settlement Delay Complaints

Trust & Security Concerns

Withdrawal Friction

Onboarding Friction

Identity Verification Complaints

Support Sentiment

Fraud Complaints

Credit Repayment Friction

SME Banking Frustrations

Agent Reliability Complaints

FX Access Frustration

Cross-Border Payment Complaints

Savings Behavior Trends

Cash Preference Indicators

Payment Preference Shifts

Network Failure Sentiment

Transfer Delay Discussions

Primary Sources

- Google Play Reviews
- Apple App Store Reviews
- X (Twitter)
- LinkedIn
- Reddit
- TikTok
- Facebook Groups
- YouTube Comments
- Consumer Forums
- Community Groups
- News Comments
- Support Communities

---

### D04 — OPERATIONAL SIGNALS

Categories

Downtime Reports

Settlement Delays

API Instability

Transaction Failure Spikes

Infrastructure Outages

Queue Congestion

Agent Liquidity Shortage

Bank Integration Failure

Service Degradation

Latency Increases

NIBSS Disruptions

Card Processing Failure

Switch Downtime

POS Failure Spikes

Webhook Failure Trends

---

### D05 — FINANCIAL SIGNALS

Categories

Revenue Growth Signals

Transaction Volume Growth

GMV Expansion

Customer Growth

Deposit Growth

Credit Default Trends

Loan Repayment Trends

Wallet Usage Growth

Merchant Activity Growth

Interchange Fee Trends

Liquidity Signals

Burn Rate Indicators

FX Exposure

Pricing Compression

Margin Pressure

---

### D06 — INFRASTRUCTURE SIGNALS

Categories

Mobile Network Reliability

Internet Penetration

Payment Rail Changes

Identity Infrastructure Stability

NIN Changes

BVN Changes

Cloud Infrastructure Incidents

Switch Infrastructure Updates

USSD Reliability

POS Hardware Availability

Biometric Infrastructure Expansion

Satellite Internet Penetration

Electricity Reliability Impact

---

### D07 — ECOSYSTEM SIGNALS

Categories

Accelerator Activity

Developer Ecosystem Growth

Open API Adoption

Bank-Fintech Collaboration

Fintech Association Activity

Hackathon Trends

Government Innovation Programs

VC Ecosystem Shifts

Talent Migration

Startup Mortality Trends

Industry Consolidation

---

### D08 — MARKET EXPANSION SIGNALS

Categories

Country Entry

Regional Expansion

Francophone Expansion

Rural Expansion

Agent Network Growth

Diaspora Corridor Expansion

SME Penetration

Sector Penetration

Cross-Sector Expansion

Offline Market Penetration

---

### D09 — FRAUD & RISK SIGNALS

Categories

Fraud Pattern Detection

- Emerging fraud schemes
- Fraud spike detection

Account Takeover Trends

Social Engineering Spikes

KYC Abuse Patterns

Suspicious Transaction Clusters

Chargeback Spikes

Scam Pattern Evolution

Merchant Fraud

Synthetic Identity Indicators

Credit Abuse Patterns

AML Risk Clusters

Cybersecurity Incidents

---

#### D10 — PARTNERSHIP SIGNALS

Categories

Banking Partnerships

Fintech Partnerships

Telco Partnerships

Government Partnerships

Infrastructure Partnerships

International Partnerships

Strategic Alliances

Distribution Partnerships

Merchant Partnerships

Enterprise Partnerships

---

### D11 — PRODUCT SIGNALS

Categories

Feature Adoption

Feature Failure

Customer Retention Impact

Payment Method Preference

Credit Product Usage

Savings Product Engagement

Agent Banking Usage

QR Adoption

Offline Payment Adoption

Subscription Product Growth

Embedded Finance Adoption

Open Banking API Usage

---

### D12 — TALENT & ORGANIZATION SIGNALS

Categories

Executive Departures

Executive Appointments

Compliance Hiring Surges

Engineering Hiring Trends

Regional Hiring Expansion

Layoffs

Product Team Expansion

Leadership Restructuring

Remote Work Expansion

Country GM Hiring

Risk Team Expansion

AI Team Expansion

---

### D13 — CAPITAL & FUNDING SIGNALS

Categories

VC Funding

Debt Financing

Acquisitions

Mergers

IPO Signals

Bridge Rounds

Down Rounds

Strategic Investment

Infrastructure Investment

Bank Investments

Telco Investments

---

### D14 — MACROECONOMIC SIGNALS

Categories

Inflation

FX Volatility

Interest Rate Changes

Fuel Price Impact

Cash Scarcity

Currency Devaluation

Import Restrictions

Consumer Spending Pressure

SME Liquidity Stress

Employment Pressure

---

### D15 — CROSS-BORDER SIGNALS

Categories

Remittance Corridor Growth

Regional Payment Interoperability

PAPSS Adoption

FX Settlement Friction

Trade Corridor Expansion

Diaspora Transaction Trends

Regional Compliance Harmonization

Local Currency Settlement

---

#### D16 — TECHNOLOGY SIGNALS

Categories

AI Adoption

Machine Learning Risk Models

Fraud Detection Systems

Open Banking Adoption

API Innovation

Cloud Migration

Digital Identity Technology

Biometric Authentication

Blockchain Infrastructure

Stablecoin Adoption

---

### D17 — REPUTATION SIGNALS

Categories

Trust Erosion

Public Backlash

Media Controversy

Security Incident Perception

Brand Confidence

Executive Reputation

Regulatory Reputation

Consumer Confidence

Merchant Confidence

---

### D18 — BEHAVIORAL SIGNALS

Categories

Cash to Digital Migration

Wallet Switching Behavior

Merchant Payment Preference Shift

Savings Behavior Change

Credit Usage Behavior

Agent Usage Patterns

Remittance Behavior Changes

Subscription Adoption Behavior

---

### D19 — DISTRIBUTION SIGNALS

Categories

Agent Network Density

Merchant Network Growth

Embedded Finance Distribution

Enterprise Distribution

Platform Integrations

Offline Distribution Expansion

Retail Partnerships

Ecosystem Distribution Reach

---

### D20 — STRATEGIC SIGNALS

Categories

Market Consolidation

Ecosystem Power Shifts

Competitive Positioning

Regulatory Positioning

Platform Strategy

Vertical Expansion

Strategic Realignment

Long-Term Market Bets

---

### D21 — FINANCIAL INCLUSION SIGNALS

Categories

Rural Financial Inclusion

Women Financial Inclusion

Youth Financial Inclusion

SME Inclusion

Agent Banking Penetration

First-Time Account Creation

Informal Economy Digitization

Underserved Region Penetration

---

### D22 — IDENTITY & TRUST SIGNALS

Categories

BVN Adoption

NIN Adoption

Identity Verification Success Rates

Digital Identity Programs

eKYC Adoption

Verification Failure Rates

Fraud Identity Detection

Trust Infrastructure Expansion

---

### D23 — PAYMENT RAIL SIGNALS

Categories

NIBSS Infrastructure Updates

PAPSS Infrastructure Updates

Card Network Updates

Instant Payment Rail Changes

Settlement Infrastructure Changes

Switching Network Updates

ISO 20022 Adoption

Rail Reliability Metrics

Interoperability Improvements

Real-Time Payment Expansion

---

# PART C — TAXONOMY URGENCY WEIGHT SUMMARY

Quick reference for the scoring engine.

| Domain Code | Domain Label | Urgency Weight | Priority |
|---|---|---|---|
| REGULATORY | Regulatory | 0.90 | 🔴 CRITICAL |
| INFRASTRUCTURE | Infrastructure | 0.88 | 🔴 CRITICAL |
| FRAUD_RISK | Fraud & Risk | 0.85 | 🔴 CRITICAL |
| OPERATIONAL | Operational | 0.80 | 🟠 HIGH |
| FINANCIAL | Financial | 0.80 | 🟠 HIGH |
| MACROECONOMIC | Macroeconomic | 0.75 | 🟠 HIGH |
| REPUTATION | Reputation | 0.65 | 🟡 MEDIUM |
| COMPETITIVE | Competitive | 0.65 | 🟡 MEDIUM |
| CONSUMER | Consumer | 0.60 | 🟡 MEDIUM |
| CROSS_BORDER | Cross-Border | 0.60 | 🟡 MEDIUM |
| MARKET_EXPANSION | Market Expansion | 0.55 | 🟢 STANDARD |
| CAPITAL_FUNDING | Capital & Funding | 0.55 | 🟢 STANDARD |
| STRATEGIC | Strategic | 0.55 | 🟢 STANDARD |
| BEHAVIORAL | Behavioral | 0.50 | 🟢 STANDARD |
| PARTNERSHIP | Partnership | 0.50 | 🟢 STANDARD |
| PRODUCT | Product | 0.50 | 🟢 STANDARD |
| TALENT_ORG | Talent & Organization | 0.45 | 🔵 LOW |
| ECOSYSTEM | Ecosystem | 0.45 | 🔵 LOW |
| TECHNOLOGY | Technology | 0.45 | 🔵 LOW |
| DISTRIBUTION | Distribution | 0.45 | 🔵 LOW |

---

# PART D — SQL SEED SCRIPTS

Copy these directly into your migration files.

---

## D1 — Signal Taxonomy INSERT

```sql
-- Migration: 0004_signal_taxonomy_seed
-- Insert all 20 domains with urgency weights

INSERT INTO config.signal_taxonomy
  (taxonomy_version, domain_code, domain_label, level, urgency_weight, is_active)
VALUES
  ('2026.06', 'REGULATORY',       'Regulatory',          1, 0.90, TRUE),
  ('2026.06', 'COMPETITIVE',      'Competitive',         1, 0.65, TRUE),
  ('2026.06', 'CONSUMER',         'Consumer',            1, 0.60, TRUE),
  ('2026.06', 'OPERATIONAL',      'Operational',         1, 0.80, TRUE),
  ('2026.06', 'FINANCIAL',        'Financial',           1, 0.80, TRUE),
  ('2026.06', 'INFRASTRUCTURE',   'Infrastructure',      1, 0.88, TRUE),
  ('2026.06', 'ECOSYSTEM',        'Ecosystem',           1, 0.45, TRUE),
  ('2026.06', 'MARKET_EXPANSION', 'Market Expansion',    1, 0.55, TRUE),
  ('2026.06', 'FRAUD_RISK',       'Fraud & Risk',        1, 0.85, TRUE),
  ('2026.06', 'PARTNERSHIP',      'Partnership',         1, 0.50, TRUE),
  ('2026.06', 'PRODUCT',          'Product',             1, 0.50, TRUE),
  ('2026.06', 'TALENT_ORG',       'Talent & Organization', 1, 0.45, TRUE),
  ('2026.06', 'CAPITAL_FUNDING',  'Capital & Funding',   1, 0.55, TRUE),
  ('2026.06', 'MACROECONOMIC',    'Macroeconomic',       1, 0.75, TRUE),
  ('2026.06', 'CROSS_BORDER',     'Cross-Border',        1, 0.60, TRUE),
  ('2026.06', 'TECHNOLOGY',       'Technology',          1, 0.45, TRUE),
  ('2026.06', 'REPUTATION',       'Reputation',          1, 0.65, TRUE),
  ('2026.06', 'BEHAVIORAL',       'Behavioral',          1, 0.50, TRUE),
  ('2026.06', 'PAYMENT',        'Payment',           1, 0.50, TRUE);
  ('2026.06', 'DISTRIBUTION',     'Distribution',        1, 0.45, TRUE),
  ('2026.06', 'INFLUSION',        'Influsion',           1, 0.50, TRUE);
  ('2026.06', 'IDENTITY',        'Identity',           1, 0.59, TRUE);
  ('2026.06', 'STRATEGIC',        'Strategic',           1, 0.55, TRUE);
```

---

## D2 — Entity Registry INSERT (abridged — key entities)

```sql
-- Migration: 0010_entity_registry_seed
-- Core Nigerian fintech entity registry

INSERT INTO intelligence.entities
  (entity_name, entity_slug, entity_type, canonical_name, aliases,
   region, sector, is_verified, source_of_creation)
VALUES

-- REGULATORS
('Central Bank of Nigeria', 'central-bank-of-nigeria', 'REGULATOR_NG',
 'Central Bank of Nigeria', ARRAY['CBN','apex bank','the bank'], 'NG', 'REGULATOR', TRUE, 'SYSTEM'),
('Securities and Exchange Commission Nigeria', 'sec-nigeria', 'REGULATOR_NG',
 'Securities and Exchange Commission Nigeria', ARRAY['SEC Nigeria','SEC','Nigerian SEC'], 'NG', 'REGULATOR', TRUE, 'SYSTEM'),
('National Data Protection Commission', 'ndpc-nigeria', 'REGULATOR_NG',
 'National Data Protection Commission', ARRAY['NDPC','Nigeria NDPC'], 'NG', 'REGULATOR', TRUE, 'SYSTEM'),
('NIBSS', 'nibss', 'FINANCIAL_INFRA',
 'NIBSS', ARRAY['Nigeria Inter-Bank Settlement System','NIBSS Plc'], 'NG', 'PAYMENT_SWITCHING', TRUE, 'SYSTEM'),
('Federal Competition and Consumer Protection Commission', 'fccpc', 'REGULATOR_NG',
 'Federal Competition and Consumer Protection Commission', ARRAY['FCCPC','Nigeria FCCPC'], 'NG', 'REGULATOR', TRUE, 'SYSTEM'),
('National Communications Commission', 'ncc-nigeria', 'REGULATOR_NG',
 'National Communications Commission', ARRAY['NCC','Nigeria NCC'], 'NG', 'REGULATOR', TRUE, 'SYSTEM'),
('Nigerian Deposit Insurance Corporation', 'ndic', 'REGULATOR_NG',
 'Nigerian Deposit Insurance Corporation', ARRAY['NDIC'], 'NG', 'REGULATOR', TRUE, 'SYSTEM'),

-- TOP FINTECHS
('Flutterwave', 'flutterwave', 'FINTECH_CO',
 'Flutterwave', ARRAY['Flutterwave Inc','FLW'], 'NG', 'PAYMENT_PROCESSING', TRUE, 'SYSTEM'),
('Paystack', 'paystack', 'FINTECH_CO',
 'Paystack', ARRAY['Paystack Inc'], 'NG', 'PAYMENT_PROCESSING', TRUE, 'SYSTEM'),
('Moniepoint', 'moniepoint', 'FINTECH_CO',
 'Moniepoint', ARRAY['Moniepoint Inc','TeamApt'], 'NG', 'BUSINESS_BANKING', TRUE, 'SYSTEM'),
('OPay', 'opay', 'FINTECH_CO',
 'OPay', ARRAY['OPay Digital Services','Opera Pay'], 'NG', 'MOBILE_MONEY', TRUE, 'SYSTEM'),
('Kuda Bank', 'kuda-bank', 'FINTECH_CO',
 'Kuda Bank', ARRAY['Kuda','Kuda Microfinance Bank'], 'NG', 'DIGITAL_BANKING', TRUE, 'SYSTEM'),
('PalmPay', 'palmpay', 'FINTECH_CO',
 'PalmPay', ARRAY['PalmPay Ltd'], 'NG', 'MOBILE_MONEY', TRUE, 'SYSTEM'),
('Carbon', 'carbon-nigeria', 'FINTECH_CO',
 'Carbon', ARRAY['Carbon Nigeria','OneFi'], 'NG', 'LENDING', TRUE, 'SYSTEM'),
('Cowrywise', 'cowrywise', 'FINTECH_CO',
 'Cowrywise', ARRAY['Cowrywise Technologies'], 'NG', 'SAVINGS_INVESTMENT', TRUE, 'SYSTEM'),
('Piggyvest', 'piggyvest', 'FINTECH_CO',
 'Piggyvest', ARRAY['PiggyVest','Piggybank.ng'], 'NG', 'SAVINGS_INVESTMENT', TRUE, 'SYSTEM'),
('Chipper Cash', 'chipper-cash', 'FINTECH_CO',
 'Chipper Cash', ARRAY['ChipperCash'], 'NG', 'CROSS_BORDER_PAYMENTS', TRUE, 'SYSTEM'),
('Mono', 'mono-africa', 'FINTECH_CO',
 'Mono', ARRAY['Mono Africa'], 'NG', 'OPEN_BANKING', TRUE, 'SYSTEM'),
('Okra', 'okra', 'FINTECH_CO',
 'Okra', ARRAY['Okra Technologies'], 'NG', 'OPEN_BANKING', TRUE, 'SYSTEM'),
('Nomba', 'nomba', 'FINTECH_CO',
 'Nomba', ARRAY['Nomba Financial Services'], 'NG', 'POS_PAYMENTS', TRUE, 'SYSTEM'),

-- BANKS
('Access Bank', 'access-bank', 'COMPANY',
 'Access Bank', ARRAY['Access Bank Nigeria','Access Bank Plc'], 'NG', 'BANKING', TRUE, 'SYSTEM'),
('Zenith Bank', 'zenith-bank', 'COMPANY',
 'Zenith Bank', ARRAY['Zenith Bank Plc'], 'NG', 'BANKING', TRUE, 'SYSTEM'),
('GTBank', 'gtbank', 'COMPANY',
 'GTBank', ARRAY['Guaranty Trust Bank','GTB','GTCO'], 'NG', 'BANKING', TRUE, 'SYSTEM'),
('First Bank of Nigeria', 'first-bank-nigeria', 'COMPANY',
 'First Bank of Nigeria', ARRAY['First Bank','FBN'], 'NG', 'BANKING', TRUE, 'SYSTEM'),
('United Bank for Africa', 'uba', 'COMPANY',
 'United Bank for Africa', ARRAY['UBA'], 'NG', 'BANKING', TRUE, 'SYSTEM'),

-- INFRASTRUCTURE
('Interswitch', 'interswitch', 'FINANCIAL_INFRA',
 'Interswitch', ARRAY['Interswitch Group','Quickteller'], 'NG', 'PAYMENT_SWITCHING', TRUE, 'SYSTEM'),
('MTN Nigeria', 'mtn-nigeria', 'INFRASTRUCTURE_PROVIDER',
 'MTN Nigeria', ARRAY['MTN','MTN Nigeria Communications'], 'NG', 'TELCO', TRUE, 'SYSTEM'),
('Airtel Nigeria', 'airtel-nigeria', 'INFRASTRUCTURE_PROVIDER',
 'Airtel Nigeria', ARRAY['Airtel Africa Nigeria'], 'NG', 'TELCO', TRUE, 'SYSTEM'),
('Verve International', 'verve', 'FINANCIAL_INFRA',
 'Verve International', ARRAY['Verve Card'], 'NG', 'CARD_SCHEME', TRUE, 'SYSTEM'),

-- LEGISLATION
('Finance Act 2023', 'finance-act-2023', 'LEGISLATION',
 'Finance Act 2023', ARRAY['Finance Act Nigeria 2023'], 'NG', NULL, TRUE, 'SYSTEM'),
('Banks and Other Financial Institutions Act', 'bofia', 'LEGISLATION',
 'Banks and Other Financial Institutions Act', ARRAY['BOFIA 2020','BOFIA'], 'NG', NULL, TRUE, 'SYSTEM'),
('Nigeria Data Protection Act', 'ndpa', 'LEGISLATION',
 'Nigeria Data Protection Act', ARRAY['NDPA','NDPA 2023'], 'NG', NULL, TRUE, 'SYSTEM'),
('Nigeria Startup Act', 'nigeria-startup-act', 'LEGISLATION',
 'Nigeria Startup Act', ARRAY['Nigerian Startup Act 2022','Startup Act'], 'NG', NULL, TRUE, 'SYSTEM'),

-- GEOGRAPHY
('Nigeria', 'nigeria', 'GEOGRAPHIC_REGION',
 'Nigeria', ARRAY['Federal Republic of Nigeria'], 'NG', NULL, TRUE, 'SYSTEM'),
('Lagos', 'lagos', 'GEOGRAPHIC_REGION',
 'Lagos', ARRAY['Lagos State','Lagos Nigeria'], 'NG', NULL, TRUE, 'SYSTEM'),
('Abuja', 'abuja', 'GEOGRAPHIC_REGION',
 'Abuja', ARRAY['FCT','Federal Capital Territory'], 'NG', NULL, TRUE, 'SYSTEM'),
('Ghana', 'ghana', 'GEOGRAPHIC_REGION',
 'Ghana', ARRAY['Republic of Ghana'], 'GH', NULL, TRUE, 'SYSTEM'),
('Kenya', 'kenya', 'GEOGRAPHIC_REGION',
 'Kenya', ARRAY['Republic of Kenya','Nairobi'], 'KE', NULL, TRUE, 'SYSTEM');

-- Add remaining entities using same pattern for the full 147-entity list above
```

---

*End of Entity Registry & Signal Taxonomy Seed Data*
