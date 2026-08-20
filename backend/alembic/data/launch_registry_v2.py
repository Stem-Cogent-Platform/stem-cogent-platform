"""Reviewed Nigeria-first launch entity manifest for Task 1.4.12.

The product-category cohort is derived directly from SC-SEED-002 v2 Section
4.2. The remaining cohorts cover the named organisations and legal instruments
needed to resolve the regulator, infrastructure, market, competitive, fraud,
and cross-border events in the same taxonomy.
"""

from typing import NamedTuple

SEED_VERSION = "2026.08-v2"
REGISTRY_CODE = "NIGERIA_LAUNCH"


class LaunchEntity(NamedTuple):
    canonical_name: str
    entity_type: str
    aliases: tuple[str, ...]
    region_tags: tuple[str, ...]
    taxonomy_basis: tuple[str, ...]
    business_model: str | None = None


_BASE_LAUNCH_ENTITIES = (
    # Regulatory and public-policy authorities.
    LaunchEntity("Central Bank of Nigeria", "REGULATOR", ("CBN",), ("NG",), ("REGULATORY_POLICY", "FINANCIAL_ECONOMIC")),
    LaunchEntity("Nigeria Data Protection Commission", "REGULATOR", ("NDPC",), ("NG",), ("DATA_PROTECTION_RULE_CHANGED", "DATA_PROTECTION_ENFORCEMENT")),
    LaunchEntity("Securities and Exchange Commission Nigeria", "REGULATOR", ("SEC Nigeria", "SEC NG"), ("NG",), ("REGULATORY_POLICY", "CAPITAL_PARTNERSHIP")),
    LaunchEntity("Nigerian Communications Commission", "REGULATOR", ("NCC",), ("NG",), ("USSD_TELECOM_RULE_CHANGED", "TELCO_INCIDENT")),
    LaunchEntity("Federal Competition and Consumer Protection Commission", "REGULATOR", ("FCCPC",), ("NG",), ("CONSUMER_PROTECTION_RULE_CHANGED",)),
    LaunchEntity("Nigeria Financial Intelligence Unit", "REGULATOR", ("NFIU",), ("NG",), ("AML_REQUIREMENT_CHANGED", "AML_RISK_CLUSTER")),
    LaunchEntity("Nigeria Revenue Service", "REGULATOR", ("NRS", "Federal Inland Revenue Service", "FIRS"), ("NG",), ("TAX_POLICY_CHANGED",)),
    LaunchEntity("Corporate Affairs Commission", "REGULATOR", ("CAC",), ("NG",), ("REGULATORY_POLICY",)),
    LaunchEntity("Nigeria Deposit Insurance Corporation", "REGULATOR", ("NDIC",), ("NG",), ("LIQUIDITY_STRESS", "REGULATORY_POLICY")),
    LaunchEntity("National Information Technology Development Agency", "REGULATOR", ("NITDA",), ("NG",), ("CYBERSECURITY_INCIDENT", "DATA_PROTECTION_RULE_CHANGED")),

    # Payment rails, switches, identity, telecommunications, and cloud dependencies.
    LaunchEntity("Nigeria Inter-Bank Settlement System", "INFRASTRUCTURE_PROVIDER", ("NIBSS", "NIBSS Plc"), ("NG",), ("PAYMENT_RAIL_OUTAGE", "SETTLEMENT_DELAY", "REAL_TIME_PAYMENTS")),
    LaunchEntity("Pan-African Payment and Settlement System", "INFRASTRUCTURE_PROVIDER", ("PAPSS",), ("AF",), ("PAYMENT_RAIL_OUTAGE", "PAPSS_ADOPTION", "CROSS_BORDER_PAYMENTS")),
    LaunchEntity("National Identity Management Commission", "INFRASTRUCTURE_PROVIDER", ("NIMC",), ("NG",), ("IDENTITY_INFRA_INCIDENT", "DIGITAL_IDENTITY")),
    LaunchEntity("MTN Nigeria", "INFRASTRUCTURE_PROVIDER", ("MTN NG",), ("NG",), ("TELCO_INCIDENT", "USSD_DEGRADATION", "MOBILE_MONEY")),
    LaunchEntity("Airtel Nigeria", "INFRASTRUCTURE_PROVIDER", ("Airtel NG",), ("NG",), ("TELCO_INCIDENT", "USSD_DEGRADATION")),
    LaunchEntity("Globacom", "INFRASTRUCTURE_PROVIDER", ("Glo", "Globacom Nigeria"), ("NG",), ("TELCO_INCIDENT", "USSD_DEGRADATION")),
    LaunchEntity("9mobile", "INFRASTRUCTURE_PROVIDER", ("Emerging Markets Telecommunication Services", "EMTS"), ("NG",), ("TELCO_INCIDENT", "USSD_DEGRADATION")),
    LaunchEntity("Amazon Web Services", "INFRASTRUCTURE_PROVIDER", ("AWS",), ("GLOBAL",), ("CLOUD_INCIDENT", "CLOUD")),
    LaunchEntity("Microsoft Azure", "INFRASTRUCTURE_PROVIDER", ("Azure",), ("GLOBAL",), ("CLOUD_INCIDENT", "CLOUD")),
    LaunchEntity("Google Cloud", "INFRASTRUCTURE_PROVIDER", ("GCP", "Google Cloud Platform"), ("GLOBAL",), ("CLOUD_INCIDENT", "CLOUD")),

    # Card and payment schemes named as launch payment dependencies.
    LaunchEntity("AfriGo", "CARD_NETWORK", ("AfriGo Card Scheme",), ("NG",), ("CARD_NETWORK_INCIDENT", "CARD_INFRASTRUCTURE", "CARDS")),
    LaunchEntity("Visa", "CARD_NETWORK", ("Visa International",), ("GLOBAL",), ("CARD_NETWORK_INCIDENT", "CARD_INFRASTRUCTURE", "CARDS")),
    LaunchEntity("Mastercard", "CARD_NETWORK", ("MasterCard", "Mastercard International"), ("GLOBAL",), ("CARD_NETWORK_INCIDENT", "CARD_INFRASTRUCTURE", "CARDS")),
    LaunchEntity("Verve", "CARD_NETWORK", ("Verve International",), ("NG", "AF"), ("CARD_NETWORK_INCIDENT", "CARD_INFRASTRUCTURE", "CARDS")),

    # Priority Nigerian bank integration dependencies.
    LaunchEntity("Access Bank", "BANK", ("Access Bank Nigeria",), ("NG",), ("BANK_INTEGRATION_FAILURE", "DIGITAL_BANKING")),
    LaunchEntity("Guaranty Trust Bank", "BANK", ("GTBank", "GTCO"), ("NG",), ("BANK_INTEGRATION_FAILURE", "DIGITAL_BANKING")),
    LaunchEntity("Zenith Bank", "BANK", (), ("NG",), ("BANK_INTEGRATION_FAILURE", "DIGITAL_BANKING")),
    LaunchEntity("United Bank for Africa", "BANK", ("UBA",), ("NG", "AF"), ("BANK_INTEGRATION_FAILURE", "DIGITAL_BANKING")),
    LaunchEntity("First Bank of Nigeria", "BANK", ("FirstBank",), ("NG",), ("BANK_INTEGRATION_FAILURE", "DIGITAL_BANKING")),
    LaunchEntity("Stanbic IBTC Bank", "BANK", ("Stanbic IBTC",), ("NG",), ("BANK_INTEGRATION_FAILURE", "DIGITAL_BANKING")),
    LaunchEntity("Fidelity Bank Nigeria", "BANK", ("Fidelity Bank",), ("NG",), ("BANK_INTEGRATION_FAILURE", "DIGITAL_BANKING")),
    LaunchEntity("Wema Bank", "BANK", (), ("NG",), ("BANK_INTEGRATION_FAILURE", "DIGITAL_BANKING")),
    LaunchEntity("First City Monument Bank", "BANK", ("FCMB",), ("NG",), ("BANK_INTEGRATION_FAILURE", "DIGITAL_BANKING")),
    LaunchEntity("Sterling Bank", "BANK", (), ("NG",), ("BANK_INTEGRATION_FAILURE", "DIGITAL_BANKING")),
    LaunchEntity("Union Bank of Nigeria", "BANK", ("Union Bank",), ("NG",), ("BANK_INTEGRATION_FAILURE", "DIGITAL_BANKING")),
    LaunchEntity("Ecobank Nigeria", "BANK", ("Ecobank",), ("NG", "AF"), ("BANK_INTEGRATION_FAILURE", "DIGITAL_BANKING")),

    # Legislation anchoring regulatory, privacy, AML, consumer, and cyber events.
    LaunchEntity("Nigeria Data Protection Act 2023", "LEGISLATION", ("NDPA 2023", "NDP Act"), ("NG",), ("DATA_PROTECTION_RULE_CHANGED", "DATA_PROTECTION_ENFORCEMENT")),
    LaunchEntity("Banks and Other Financial Institutions Act 2020", "LEGISLATION", ("BOFIA 2020",), ("NG",), ("REGULATORY_FRAMEWORK_UPDATED",)),
    LaunchEntity("Money Laundering (Prevention and Prohibition) Act 2022", "LEGISLATION", ("MLPPA 2022",), ("NG",), ("AML_REQUIREMENT_CHANGED", "AML_RISK_CLUSTER")),
    LaunchEntity("Cybercrimes (Prohibition, Prevention, Etc.) Act 2015", "LEGISLATION", ("Cybercrimes Act", "Cybercrimes Act 2015", "Cybercrimes Amendment Act 2024"), ("NG",), ("CYBERSECURITY_INCIDENT", "FRAUD_RISK_TRUST")),
    LaunchEntity("Federal Competition and Consumer Protection Act 2018", "LEGISLATION", ("FCCPA 2018",), ("NG",), ("CONSUMER_PROTECTION_RULE_CHANGED",)),
    LaunchEntity("Central Bank of Nigeria Act 2007", "LEGISLATION", ("CBN Act 2007",), ("NG",), ("REGULATORY_POLICY",)),

    # Exact SC-SEED-002 v2 Section 4.2 product/business-model vocabulary.
    LaunchEntity("Digital Wallets", "PRODUCT_CATEGORY", ("Wallet", "Mobile Wallets"), ("NG",), ("WALLET",)),
    LaunchEntity("Merchant Acquiring", "PRODUCT_CATEGORY", ("Merchant Payments",), ("NG",), ("MERCHANT_ACQUIRING",)),
    LaunchEntity("Payment Processing", "PRODUCT_CATEGORY", ("Payment Services",), ("NG",), ("PAYMENT_PROCESSING",)),
    LaunchEntity("Mobile Money", "PRODUCT_CATEGORY", (), ("NG",), ("MOBILE_MONEY",)),
    LaunchEntity("Digital Banking", "PRODUCT_CATEGORY", ("Digital Bank", "Neobank"), ("NG",), ("DIGITAL_BANKING",)),
    LaunchEntity("Digital Lending", "PRODUCT_CATEGORY", ("Online Lending",), ("NG",), ("LENDING",)),
    LaunchEntity("SME Lending", "PRODUCT_CATEGORY", ("Business Lending",), ("NG",), ("SME_LENDING",)),
    LaunchEntity("Buy Now Pay Later", "PRODUCT_CATEGORY", ("BNPL",), ("NG",), ("BNPL",)),
    LaunchEntity("Savings and Investments", "PRODUCT_CATEGORY", ("WealthTech",), ("NG",), ("SAVINGS_INVESTMENT",)),
    LaunchEntity("Remittances", "PRODUCT_CATEGORY", ("Remittance",), ("NG",), ("REMITTANCE",)),
    LaunchEntity("Cross-Border Payments", "PRODUCT_CATEGORY", ("International Payments",), ("NG",), ("CROSS_BORDER_PAYMENTS",)),
    LaunchEntity("Open Banking Infrastructure", "PRODUCT_CATEGORY", ("Open Banking", "Open Finance"), ("NG",), ("OPEN_BANKING_INFRA",)),
    LaunchEntity("Banking as a Service", "PRODUCT_CATEGORY", ("BaaS",), ("NG",), ("BaaS",)),
    LaunchEntity("Card Infrastructure", "PRODUCT_CATEGORY", ("Card Payments",), ("NG",), ("CARD_INFRASTRUCTURE",)),
    LaunchEntity("Agent Banking", "PRODUCT_CATEGORY", ("Agency Banking",), ("NG",), ("AGENT_BANKING",)),
    LaunchEntity("Credit Infrastructure", "PRODUCT_CATEGORY", ("Credit Technology",), ("NG",), ("CREDIT_INFRASTRUCTURE",)),

    LaunchEntity("Nigeria", "MARKET", ("NG", "Federal Republic of Nigeria"), ("NG",), ("NG",)),
)


# User-reviewed Nigerian launch cohort. The category strings are product-facing
# market segments; their values map to canonical SC-SEED-002 secondary tags.
BUSINESS_MODEL_TAXONOMY = {
    "Lending / Credit": ("LENDING", "CREDIT_INFRASTRUCTURE"),
    "Digital Assets / Stablecoin": ("STABLECOIN", "BLOCKCHAIN"),
    "RegTech / Identity / Risk": ("DIGITAL_IDENTITY", "FRAUD_TECH", "CREDIT_INFRASTRUCTURE"),
    "Insurtech / Embedded Insurance": ("COMPETITIVE_PRODUCT",),
    "Financial Infrastructure / APIs": ("API", "PAYMENT_PROCESSING"),
    "Cross-border / Payments": ("CROSS_BORDER_PAYMENTS", "REMITTANCE"),
    "Payments / Wallets / Processing": ("PAYMENT_PROCESSING", "WALLET"),
    "SME / Business Finance": ("SME", "DIGITAL_BANKING"),
    "Wealth / Investment": ("SAVINGS_INVESTMENT",),
}

BUSINESS_MODEL_LAUNCH_ROLES = {
    "Lending / Credit": ("LENDING_CREDIT",),
    "Digital Assets / Stablecoin": ("DIGITAL_ASSETS_STABLECOIN",),
    "RegTech / Identity / Risk": ("REGTECH_IDENTITY_RISK",),
    "Insurtech / Embedded Insurance": ("INSURTECH_EMBEDDED_INSURANCE",),
    "Financial Infrastructure / APIs": ("FINANCIAL_INFRASTRUCTURE_API",),
    "Cross-border / Payments": ("CROSS_BORDER_PAYMENTS",),
    "Payments / Wallets / Processing": ("PAYMENTS_WALLETS_PROCESSING",),
    "SME / Business Finance": ("SME_BUSINESS_FINANCE",),
    "Wealth / Investment": ("WEALTH_INVESTMENT",),
}

ENTITY_LAUNCH_ROLE_OVERRIDES = {
    "3Line": ("CARD_PAYMENT_SCHEME",),
    "CoralPay": ("PAYMENT_SWITCH_PROCESSOR",),
    "eTranzact": ("PAYMENT_SWITCH_PROCESSOR",),
    "E-Settlement": ("PAYMENT_SWITCH_PROCESSOR",),
    "Global Accelerex": ("PAYMENT_SWITCH_PROCESSOR",),
    "Hydrogen": ("PAYMENT_SWITCH_PROCESSOR",),
    "Interswitch": ("PAYMENT_SWITCH_PROCESSOR",),
    "ITEX": ("PAYMENT_SWITCH_PROCESSOR",),
    "SeerBit": ("PAYMENT_PROCESSOR",),
    "SystemSpecs": ("PAYMENT_SWITCH_PROCESSOR",),
    "Unified Payments": ("PAYMENT_SWITCH_PROCESSOR",),
    "Xpress Payments": ("PAYMENT_SWITCH_PROCESSOR",),
    "Zone": ("PAYMENT_SWITCH_PROCESSOR",),
}


# canonical_name, business_model, aliases
PRIORITY_FINTECH_MANIFEST = (
    ("Sycamore", "Lending / Credit", ()),
    ("Busha", "Digital Assets / Stablecoin", ()),
    ("Prembly", "RegTech / Identity / Risk", ()),
    ("Curacel", "Insurtech / Embedded Insurance", ()),
    ("Lendsqr", "Lending / Credit", ()),
    ("Zeeh", "RegTech / Identity / Risk", ()),
    ("Anchor", "Financial Infrastructure / APIs", ("Anchor API",)),
    ("Accrue", "Cross-border / Payments", ()),
    ("Touch & Pay", "Payments / Wallets / Processing", ("TAP",)),
    ("Kora", "Cross-border / Payments", ("Korapay",)),
    ("Quidax", "Digital Assets / Stablecoin", ()),
    ("SeerBit", "Cross-border / Payments", ()),
    ("Youverify", "RegTech / Identity / Risk", ("YouVerify",)),
    ("Bujeti", "SME / Business Finance", ()),
    ("Flex Finance", "SME / Business Finance", ()),
    ("Raenest", "Cross-border / Payments", ()),
    ("Payaza", "Cross-border / Payments", ()),
    ("Fincra", "Cross-border / Payments", ()),
    ("Grey", "Cross-border / Payments", ("Grey Finance",)),
    ("VeendHQ", "Payments / Wallets / Processing", ("Veend",)),
    ("Duplo", "SME / Business Finance", ()),
    ("Sudo Africa", "Financial Infrastructure / APIs", ("Sudo",)),
    ("Dojah", "RegTech / Identity / Risk", ()),
    ("OnePipe", "Financial Infrastructure / APIs", ()),
    ("Nomba", "Payments / Wallets / Processing", ("Kudi",)),
    ("Klasha", "Cross-border / Payments", ()),
    ("Juicyway", "Cross-border / Payments", ()),
    ("MyCover.ai", "Insurtech / Embedded Insurance", ("MyCover",)),
    ("Prospa", "SME / Business Finance", ()),
    ("Indicina", "Lending / Credit", ()),
    ("Zedvance", "Lending / Credit", ()),
    ("Rise", "Wealth / Investment", ("Risevest",)),
    ("Bloc", "Financial Infrastructure / APIs", ()),
    ("HabariPay", "Payments / Wallets / Processing", ("Squad", "Habaripay / Squad")),
    ("Global Accelerex", "Payments / Wallets / Processing", ("Accelerex",)),
    ("ZendWallet", "Cross-border / Payments", ("Zend Wallet",)),
    ("Woven Finance", "Financial Infrastructure / APIs", ()),
    ("Hydrogen", "Financial Infrastructure / APIs", ("Hydrogen Payment Services",)),
    ("Vendy", "Payments / Wallets / Processing", ()),
    ("KrediBank", "Lending / Credit", ("Kredi",)),
    ("Aella", "Lending / Credit", ("Aella Credit",)),
    ("eTranzact", "Payments / Wallets / Processing", ("eTranzact International",)),
    ("ETAP", "Payments / Wallets / Processing", ()),
    ("Earnipay", "SME / Business Finance", ()),
    ("VerifyMe Nigeria", "RegTech / Identity / Risk", ("VerifyMe",)),
    ("BoundlessPay", "Cross-border / Payments", ()),
    ("Xpress Payments", "Payments / Wallets / Processing", ("Xpress Payment Solutions",)),
    ("Redtech", "Financial Infrastructure / APIs", ()),
    ("Klump", "Lending / Credit", ()),
    ("Trade Lenda", "Lending / Credit", ("TradeLenda",)),
    ("Multigate", "Payments / Wallets / Processing", ()),
    ("Upperlink", "Financial Infrastructure / APIs", ()),
    ("Sparkle", "Payments / Wallets / Processing", ("Sparkle Nigeria",)),
    ("P2Vest", "Lending / Credit", ()),
    ("Trove Finance", "Wealth / Investment", ("Trove",)),
    ("3Line", "Payments / Wallets / Processing", ("3Line Card Management",)),
    ("SystemSpecs", "Payments / Wallets / Processing", ("Remita", "Remita / SystemSpecs", "SystemSpecs Remita")),
    ("Bamboo", "Wealth / Investment", ("Bamboo Investment",)),
    ("Maplerad", "Financial Infrastructure / APIs", ()),
    ("Unified Payments", "Payments / Wallets / Processing", ("Unified Payment Services",)),
    ("Zone", "Financial Infrastructure / APIs", ("Zone Payment Network", "Appzone")),
    ("CreditWave", "Lending / Credit", ("Credit Wave",)),
    ("CredPal", "Lending / Credit", ()),
    ("PiggyVest", "Wealth / Investment", ("Piggybank.ng",)),
    ("CoralPay", "Payments / Wallets / Processing", ("Coralpay Technology Nigeria",)),
    ("E-Settlement", "Payments / Wallets / Processing", ("ESettlement",)),
    ("Branch Nigeria", "Lending / Credit", ("Branch",)),
    ("Paga", "Payments / Wallets / Processing", ("Pagatech", "Pagatech Limited")),
    ("Miden", "Financial Infrastructure / APIs", ()),
    ("NOLT Finance", "Lending / Credit", ("NOLT",)),
    ("Cowrywise", "Wealth / Investment", ()),
    ("Airvend", "Payments / Wallets / Processing", ()),
    ("ITEX", "Payments / Wallets / Processing", ("Itex Integrated Services",)),
    ("PaidHR", "SME / Business Finance", ("Paid HR",)),
    ("Prophius", "Financial Infrastructure / APIs", ()),
    ("Roqqu", "Digital Assets / Stablecoin", ()),
    ("Page Financials", "Lending / Credit", ()),
    ("Credit Direct", "Lending / Credit", ()),
    ("Regfyl", "RegTech / Identity / Risk", ()),
    ("NowNow", "Payments / Wallets / Processing", ("NowNow Digital Systems",)),
    ("Kuda", "Payments / Wallets / Processing", ("Kuda Bank",)),
    ("Chipper Cash", "Cross-border / Payments", ()),
    ("Carbon", "Payments / Wallets / Processing", ("Paylater",)),
    ("Moniepoint", "Payments / Wallets / Processing", ("TeamApt", "Teamapt Limited")),
    ("Flutterwave", "Payments / Wallets / Processing", ("Flutterwave Technology Solutions",)),
    ("Traction Apps", "SME / Business Finance", ("Traction",)),
    ("Cellulant Nigeria", "Payments / Wallets / Processing", ("Cellulant",)),
    ("Sabi", "SME / Business Finance", ()),
    ("Renmoney", "Payments / Wallets / Processing", ()),
    ("Paystack", "Payments / Wallets / Processing", ("Paystack Payments",)),
    ("Interswitch", "Payments / Wallets / Processing", ("Interswitch Limited",)),
    ("OPay", "Payments / Wallets / Processing", ("OPay Nigeria", "Opay Digital Services")),
    ("Yellow Card", "Digital Assets / Stablecoin", ("Yellow Card Africa",)),
    ("PalmPay", "Payments / Wallets / Processing", ("PalmPay Nigeria", "PalmPay Limited")),
    ("M-KOPA Nigeria", "Payments / Wallets / Processing", ("M-KOPA",)),
    ("Mono", "Financial Infrastructure / APIs", ("Mono Technologies",)),
    ("FairMoney", "Payments / Wallets / Processing", ("FairMoney Nigeria",)),
    ("LemFi", "Cross-border / Payments", ("Lemonade Finance", "RightCard Payment Services")),
    ("TradeDepot", "SME / Business Finance", ("Trade Depot",)),
    ("Reliance Health", "Insurtech / Embedded Insurance", ()),
)


LAUNCH_ENTITIES = (
    _BASE_LAUNCH_ENTITIES
    + tuple(
        LaunchEntity(
            canonical_name,
            "FINTECH",
            aliases,
            ("NG",),
            BUSINESS_MODEL_TAXONOMY[business_model],
            business_model,
        )
        for canonical_name, business_model, aliases in PRIORITY_FINTECH_MANIFEST
    )
)


REVIEWED_MANIFEST_COUNTS = {
    entity_type: sum(row.entity_type == entity_type for row in LAUNCH_ENTITIES)
    for entity_type in sorted({row.entity_type for row in LAUNCH_ENTITIES})
}

TAXONOMY_PRODUCT_CODES = frozenset(
    {
        "WALLET",
        "MERCHANT_ACQUIRING",
        "PAYMENT_PROCESSING",
        "MOBILE_MONEY",
        "DIGITAL_BANKING",
        "LENDING",
        "SME_LENDING",
        "BNPL",
        "SAVINGS_INVESTMENT",
        "REMITTANCE",
        "CROSS_BORDER_PAYMENTS",
        "OPEN_BANKING_INFRA",
        "BaaS",
        "CARD_INFRASTRUCTURE",
        "AGENT_BANKING",
        "CREDIT_INFRASTRUCTURE",
    }
)
