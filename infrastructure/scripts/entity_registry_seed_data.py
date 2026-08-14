"""Curated launch data for the Stem Cogent entity registry.

The authoritative launch list is SC-DOC-005 section 2.2. The specification's
"Wave (formerly Sendwave)" wording is corrected here: Sendwave and Wave are
distinct businesses, so both receive canonical records. The fourteen entries
listed in ``NIGERIA_LAUNCH_ADDITION_SLUGS`` close material Nigeria-specific
coverage gaps across regulation, banking, fintech, and financial infrastructure.
"""

from dataclasses import dataclass


ENTITY_TYPES = frozenset(
    {
        "COMPANY",
        "REGULATORY_BODY",
        "PERSON",
        "PRODUCT",
        "GEOGRAPHIC_REGION",
        "INFRASTRUCTURE_PROVIDER",
        "FINANCIAL_INSTRUMENT",
        "LEGISLATION",
    }
)


@dataclass(frozen=True, slots=True)
class EntitySeed:
    entity_name: str
    entity_slug: str
    entity_type: str
    canonical_name: str
    aliases: tuple[str, ...]
    description: str | None
    region: str | None
    country_code: str | None
    sector: str | None
    sub_sector: str | None
    website_url: str | None = None
    parent_slug: str | None = None


def _entity(
    name: str,
    slug: str,
    entity_type: str,
    aliases: tuple[str, ...] = (),
    *,
    description: str | None = None,
    region: str | None = "NG",
    country_code: str | None = "NG",
    sector: str | None = None,
    sub_sector: str | None = None,
    website_url: str | None = None,
    parent_slug: str | None = None,
) -> EntitySeed:
    return EntitySeed(
        entity_name=name,
        entity_slug=slug,
        entity_type=entity_type,
        canonical_name=name,
        aliases=aliases,
        description=description,
        region=region,
        country_code=country_code,
        sector=sector,
        sub_sector=sub_sector,
        website_url=website_url,
        parent_slug=parent_slug,
    )


NIGERIA_LAUNCH_ADDITION_SLUGS = frozenset(
    {
        "special-control-unit-against-money-laundering",
        "nigerian-financial-intelligence-unit",
        "economic-and-financial-crimes-commission",
        "national-information-technology-development-agency",
        "first-city-monument-bank",
        "providus-bank",
        "jaiz-bank",
        "nomba",
        "mono",
        "okra",
        "mainone",
        "momo-payment-service-bank",
        "nigerian-exchange-group",
        "fmdq-group",
    }
)


ENTITY_SEEDS: tuple[EntitySeed, ...] = (
    # SC-DOC-005 section 2.2: regulatory bodies.
    _entity(
        "Central Bank of Nigeria",
        "central-bank-of-nigeria",
        "REGULATORY_BODY",
        ("CBN", "Central Bank Nigeria", "Nigeria central bank"),
        sector="REGULATOR",
        sub_sector="CENTRAL_BANK",
    ),
    _entity(
        "Securities and Exchange Commission Nigeria",
        "securities-and-exchange-commission-nigeria",
        "REGULATORY_BODY",
        ("SEC Nigeria", "Nigerian SEC"),
        sector="REGULATOR",
        sub_sector="CAPITAL_MARKETS",
    ),
    _entity(
        "Nigeria Data Protection Commission",
        "nigeria-data-protection-commission",
        "REGULATORY_BODY",
        ("NDPC", "National Data Protection Commission", "Nigeria NDPC"),
        sector="REGULATOR",
        sub_sector="DATA_PROTECTION",
    ),
    _entity(
        "Nigeria Inter-Bank Settlement System",
        "nigeria-inter-bank-settlement-system",
        "INFRASTRUCTURE_PROVIDER",
        ("NIBSS", "NIBSS Plc", "Nigeria Interbank Settlement System"),
        sector="FINANCIAL_INFRASTRUCTURE",
        sub_sector="PAYMENT_SWITCHING",
    ),
    _entity(
        "Financial Reporting Council of Nigeria",
        "financial-reporting-council-of-nigeria",
        "REGULATORY_BODY",
        ("FRCN", "Financial Reporting Council"),
        sector="REGULATOR",
        sub_sector="FINANCIAL_REPORTING",
    ),
    _entity(
        "Federal Competition and Consumer Protection Commission",
        "federal-competition-and-consumer-protection-commission",
        "REGULATORY_BODY",
        ("FCCPC", "Nigeria FCCPC"),
        sector="REGULATOR",
        sub_sector="CONSUMER_PROTECTION",
    ),
    _entity(
        "National Insurance Commission",
        "national-insurance-commission",
        "REGULATORY_BODY",
        ("NAICOM",),
        sector="REGULATOR",
        sub_sector="INSURANCE",
    ),
    _entity(
        "Corporate Affairs Commission",
        "corporate-affairs-commission",
        "REGULATORY_BODY",
        ("CAC", "Nigeria CAC"),
        sector="REGULATOR",
        sub_sector="CORPORATE_REGISTRY",
    ),
    _entity(
        "Nigerian Communications Commission",
        "nigerian-communications-commission",
        "REGULATORY_BODY",
        ("NCC", "National Communications Commission", "Nigeria NCC"),
        sector="REGULATOR",
        sub_sector="TELECOMMUNICATIONS",
    ),
    _entity(
        "Federal Inland Revenue Service",
        "federal-inland-revenue-service",
        "REGULATORY_BODY",
        ("FIRS",),
        sector="REGULATOR",
        sub_sector="TAXATION",
    ),
    _entity(
        "Nigeria Deposit Insurance Corporation",
        "nigeria-deposit-insurance-corporation",
        "REGULATORY_BODY",
        ("NDIC", "Nigerian Deposit Insurance Corporation"),
        sector="REGULATOR",
        sub_sector="DEPOSIT_INSURANCE",
    ),

    # SC-DOC-005 section 2.2: fintech companies and their launch products.
    _entity(
        "Flutterwave",
        "flutterwave",
        "COMPANY",
        ("Flutterwave Inc", "Flutterwave Technology Solutions", "FLW"),
        sector="FINTECH",
        sub_sector="PAYMENT_PROCESSING",
    ),
    _entity(
        "Paystack",
        "paystack",
        "COMPANY",
        ("Paystack Payments", "Paystack Payment Limited"),
        sector="FINTECH",
        sub_sector="PAYMENT_PROCESSING",
    ),
    _entity(
        "Moniepoint",
        "moniepoint",
        "COMPANY",
        ("Moniepoint Inc", "TeamApt", "TeamApt Limited"),
        sector="FINTECH",
        sub_sector="BUSINESS_BANKING",
    ),
    _entity(
        "OPay",
        "opay",
        "COMPANY",
        ("OPay Digital Services", "Opera Pay", "Paycom Nigeria"),
        sector="FINTECH",
        sub_sector="MOBILE_MONEY",
    ),
    _entity(
        "Kuda Bank",
        "kuda-bank",
        "COMPANY",
        ("Kuda", "Kuda Microfinance Bank"),
        sector="FINTECH",
        sub_sector="DIGITAL_BANKING",
    ),
    _entity(
        "PalmPay",
        "palmpay",
        "COMPANY",
        ("PalmPay Limited", "PalmPay Ltd"),
        sector="FINTECH",
        sub_sector="MOBILE_MONEY",
    ),
    _entity(
        "Wave Mobile Money",
        "wave-mobile-money",
        "COMPANY",
        ("Wave", "Wave Digital Finance"),
        region="AF",
        country_code=None,
        sector="FINTECH",
        sub_sector="MOBILE_MONEY",
    ),
    _entity(
        "Sendwave",
        "sendwave",
        "COMPANY",
        ("SendWave", "Sendwave Money Transfer"),
        region="AF",
        country_code=None,
        sector="FINTECH",
        sub_sector="CROSS_BORDER_PAYMENTS",
    ),
    _entity(
        "Chipper Cash",
        "chipper-cash",
        "COMPANY",
        ("ChipperCash",),
        region="AF",
        country_code=None,
        sector="FINTECH",
        sub_sector="CROSS_BORDER_PAYMENTS",
    ),
    _entity(
        "Carbon",
        "carbon",
        "COMPANY",
        ("Carbon Nigeria", "OneFi", "Paylater"),
        sector="FINTECH",
        sub_sector="DIGITAL_LENDING",
    ),
    _entity(
        "FairMoney",
        "fairmoney",
        "COMPANY",
        ("FairMoney Microfinance Bank",),
        sector="FINTECH",
        sub_sector="DIGITAL_LENDING",
    ),
    _entity(
        "Branch International",
        "branch-international",
        "COMPANY",
        ("Branch Nigeria", "Branch"),
        region="AF",
        country_code=None,
        sector="FINTECH",
        sub_sector="DIGITAL_LENDING",
    ),
    _entity(
        "Renmoney",
        "renmoney",
        "COMPANY",
        ("Renmoney Microfinance Bank",),
        sector="FINTECH",
        sub_sector="DIGITAL_LENDING",
    ),
    _entity(
        "Cowrywise",
        "cowrywise",
        "COMPANY",
        ("Cowrywise Financial Technology",),
        sector="FINTECH",
        sub_sector="SAVINGS_INVESTMENT",
    ),
    _entity(
        "PiggyVest",
        "piggyvest",
        "COMPANY",
        ("Piggyvest", "Piggybank.ng"),
        sector="FINTECH",
        sub_sector="SAVINGS_INVESTMENT",
    ),
    _entity(
        "Bamboo",
        "bamboo",
        "COMPANY",
        ("Bamboo Invest", "Bamboo Investment"),
        sector="FINTECH",
        sub_sector="INVESTMENT",
    ),
    _entity(
        "Risevest",
        "risevest",
        "COMPANY",
        ("Rise Vest", "Rise"),
        sector="FINTECH",
        sub_sector="INVESTMENT",
    ),
    _entity(
        "Bankly",
        "bankly",
        "COMPANY",
        ("Bankly Nigeria",),
        sector="FINTECH",
        sub_sector="AGENT_BANKING",
    ),
    _entity(
        "Paga",
        "paga",
        "COMPANY",
        ("Pagatech", "Pagatech Limited"),
        sector="FINTECH",
        sub_sector="MOBILE_MONEY",
    ),
    _entity(
        "Interswitch",
        "interswitch",
        "INFRASTRUCTURE_PROVIDER",
        ("Interswitch Group", "Interswitch Limited"),
        sector="FINANCIAL_INFRASTRUCTURE",
        sub_sector="PAYMENT_SWITCHING",
    ),
    _entity(
        "Quickteller",
        "quickteller",
        "PRODUCT",
        ("Quickteller Paypoint",),
        sector="FINTECH",
        sub_sector="PAYMENTS",
        parent_slug="interswitch",
    ),
    _entity(
        "eTranzact",
        "etranzact",
        "INFRASTRUCTURE_PROVIDER",
        ("eTranzact International", "eTranzact International Plc"),
        sector="FINANCIAL_INFRASTRUCTURE",
        sub_sector="PAYMENT_SWITCHING",
    ),
    _entity(
        "SystemSpecs",
        "systemspecs",
        "INFRASTRUCTURE_PROVIDER",
        ("SystemSpecs Nigeria",),
        sector="FINANCIAL_INFRASTRUCTURE",
        sub_sector="PAYMENT_PROCESSING",
    ),
    _entity(
        "Remita",
        "remita",
        "PRODUCT",
        ("Remita Payment Service", "Remita Payments"),
        sector="FINTECH",
        sub_sector="PAYMENTS",
        parent_slug="systemspecs",
    ),
    _entity(
        "Unified Payments",
        "unified-payments",
        "INFRASTRUCTURE_PROVIDER",
        ("Unified Payment Services", "Unified Payments Nigeria"),
        sector="FINANCIAL_INFRASTRUCTURE",
        sub_sector="PAYMENT_PROCESSING",
    ),

    # SC-DOC-005 section 2.2: top-tier banks.
    _entity(
        "Access Bank",
        "access-bank",
        "COMPANY",
        ("Access Bank Nigeria", "Access Bank Plc"),
        sector="BANKING",
        sub_sector="COMMERCIAL_BANK",
    ),
    _entity(
        "Zenith Bank",
        "zenith-bank",
        "COMPANY",
        ("Zenith Bank Plc",),
        sector="BANKING",
        sub_sector="COMMERCIAL_BANK",
    ),
    _entity(
        "Guaranty Trust Bank",
        "guaranty-trust-bank",
        "COMPANY",
        ("GTBank", "GTB", "Guaranty Trust", "GTCO"),
        sector="BANKING",
        sub_sector="COMMERCIAL_BANK",
    ),
    _entity(
        "First Bank of Nigeria",
        "first-bank-of-nigeria",
        "COMPANY",
        ("First Bank", "FBN", "FirstBank"),
        sector="BANKING",
        sub_sector="COMMERCIAL_BANK",
    ),
    _entity(
        "United Bank for Africa",
        "united-bank-for-africa",
        "COMPANY",
        ("UBA", "UBA Nigeria"),
        sector="BANKING",
        sub_sector="COMMERCIAL_BANK",
    ),
    _entity(
        "Ecobank Nigeria",
        "ecobank-nigeria",
        "COMPANY",
        ("Ecobank", "Ecobank Nigeria Limited"),
        sector="BANKING",
        sub_sector="COMMERCIAL_BANK",
    ),
    _entity(
        "Fidelity Bank",
        "fidelity-bank",
        "COMPANY",
        ("Fidelity Bank Nigeria", "Fidelity Bank Plc"),
        sector="BANKING",
        sub_sector="COMMERCIAL_BANK",
    ),
    _entity(
        "Sterling Bank",
        "sterling-bank",
        "COMPANY",
        ("Sterling Bank Nigeria", "Sterling Bank Plc"),
        sector="BANKING",
        sub_sector="COMMERCIAL_BANK",
    ),
    _entity(
        "Stanbic IBTC Bank",
        "stanbic-ibtc-bank",
        "COMPANY",
        ("Stanbic IBTC",),
        sector="BANKING",
        sub_sector="COMMERCIAL_BANK",
    ),
    _entity(
        "Union Bank of Nigeria",
        "union-bank-of-nigeria",
        "COMPANY",
        ("Union Bank", "Union Bank Nigeria"),
        sector="BANKING",
        sub_sector="COMMERCIAL_BANK",
    ),
    _entity(
        "Wema Bank",
        "wema-bank",
        "COMPANY",
        ("Wema Bank Nigeria", "ALAT by Wema"),
        sector="BANKING",
        sub_sector="COMMERCIAL_BANK",
    ),
    _entity(
        "Polaris Bank",
        "polaris-bank",
        "COMPANY",
        ("Polaris Bank Nigeria",),
        sector="BANKING",
        sub_sector="COMMERCIAL_BANK",
    ),

    # SC-DOC-005 section 2.2: remaining infrastructure providers.
    _entity(
        "MTN Nigeria",
        "mtn-nigeria",
        "INFRASTRUCTURE_PROVIDER",
        ("MTN", "MTN Nigeria Communications"),
        sector="TELECOMMUNICATIONS",
        sub_sector="MOBILE_NETWORK_OPERATOR",
    ),
    _entity(
        "Airtel Nigeria",
        "airtel-nigeria",
        "INFRASTRUCTURE_PROVIDER",
        ("Airtel", "Airtel Africa Nigeria"),
        sector="TELECOMMUNICATIONS",
        sub_sector="MOBILE_NETWORK_OPERATOR",
    ),
    _entity(
        "Globacom",
        "globacom",
        "INFRASTRUCTURE_PROVIDER",
        ("Glo", "Glo Mobile", "Globacom Limited"),
        sector="TELECOMMUNICATIONS",
        sub_sector="MOBILE_NETWORK_OPERATOR",
    ),
    _entity(
        "9mobile",
        "9mobile",
        "INFRASTRUCTURE_PROVIDER",
        ("9Mobile Nigeria", "Etisalat Nigeria"),
        sector="TELECOMMUNICATIONS",
        sub_sector="MOBILE_NETWORK_OPERATOR",
    ),
    _entity(
        "Verve International",
        "verve-international",
        "INFRASTRUCTURE_PROVIDER",
        ("Verve", "Verve Card"),
        sector="FINANCIAL_INFRASTRUCTURE",
        sub_sector="CARD_SCHEME",
    ),
    _entity(
        "Mastercard Nigeria",
        "mastercard-nigeria",
        "INFRASTRUCTURE_PROVIDER",
        ("Mastercard", "MasterCard Nigeria"),
        sector="FINANCIAL_INFRASTRUCTURE",
        sub_sector="CARD_SCHEME",
    ),
    _entity(
        "Visa Nigeria",
        "visa-nigeria",
        "INFRASTRUCTURE_PROVIDER",
        ("Visa", "Visa International Nigeria"),
        sector="FINANCIAL_INFRASTRUCTURE",
        sub_sector="CARD_SCHEME",
    ),
    _entity(
        "UnionPay Nigeria",
        "unionpay-nigeria",
        "INFRASTRUCTURE_PROVIDER",
        ("UnionPay", "Union Pay Nigeria"),
        sector="FINANCIAL_INFRASTRUCTURE",
        sub_sector="CARD_SCHEME",
    ),

    # SC-DOC-005 section 2.2: legislation and directives. The current 2025
    # Investments and Securities Act replaces the obsolete 2007 act implied by
    # the undated specification entry.
    _entity(
        "Finance Act 2020",
        "finance-act-2020",
        "LEGISLATION",
        ("Nigeria Finance Act 2020",),
        sector="LEGISLATION",
        sub_sector="TAXATION",
    ),
    _entity(
        "Finance Act 2021",
        "finance-act-2021",
        "LEGISLATION",
        ("Nigeria Finance Act 2021",),
        sector="LEGISLATION",
        sub_sector="TAXATION",
    ),
    _entity(
        "Finance Act 2022",
        "finance-act-2022",
        "LEGISLATION",
        ("Nigeria Finance Act 2022",),
        sector="LEGISLATION",
        sub_sector="TAXATION",
    ),
    _entity(
        "Finance Act 2023",
        "finance-act-2023",
        "LEGISLATION",
        ("Nigeria Finance Act 2023",),
        sector="LEGISLATION",
        sub_sector="TAXATION",
    ),
    _entity(
        "Central Bank of Nigeria Act 2007",
        "central-bank-of-nigeria-act-2007",
        "LEGISLATION",
        ("CBN Act", "CBN Act 2007"),
        sector="LEGISLATION",
        sub_sector="BANKING",
    ),
    _entity(
        "Banks and Other Financial Institutions Act 2020",
        "banks-and-other-financial-institutions-act-2020",
        "LEGISLATION",
        ("BOFIA", "BOFIA 2020"),
        sector="LEGISLATION",
        sub_sector="BANKING",
    ),
    _entity(
        "Nigeria Data Protection Act 2023",
        "nigeria-data-protection-act-2023",
        "LEGISLATION",
        ("NDPA", "NDPA 2023", "NDPC Act 2023", "NDP Act 2023"),
        sector="LEGISLATION",
        sub_sector="DATA_PROTECTION",
    ),
    _entity(
        "Investments and Securities Act 2025",
        "investments-and-securities-act-2025",
        "LEGISLATION",
        (
            "Investment and Securities Act",
            "ISA",
            "ISA 2025",
            "Investments and Securities Act",
        ),
        sector="LEGISLATION",
        sub_sector="CAPITAL_MARKETS",
    ),
    _entity(
        "Companies and Allied Matters Act 2020",
        "companies-and-allied-matters-act-2020",
        "LEGISLATION",
        ("CAMA", "CAMA 2020"),
        sector="LEGISLATION",
        sub_sector="CORPORATE_LAW",
    ),
    _entity(
        "Nigeria Startup Act 2022",
        "nigeria-startup-act-2022",
        "LEGISLATION",
        ("Nigerian Startup Act 2022", "Startup Act", "NSA 2022"),
        sector="LEGISLATION",
        sub_sector="TECHNOLOGY",
    ),
    _entity(
        "Federal Competition and Consumer Protection Act 2018",
        "federal-competition-and-consumer-protection-act-2018",
        "LEGISLATION",
        ("FCCPA", "Federal Competition and Consumer Protection Act"),
        sector="LEGISLATION",
        sub_sector="CONSUMER_PROTECTION",
    ),

    # Fourteen Nigeria-specific launch additions authorized for TASK 1.4.10.
    _entity(
        "Special Control Unit Against Money Laundering",
        "special-control-unit-against-money-laundering",
        "REGULATORY_BODY",
        ("SCUML", "SCUML Nigeria"),
        sector="REGULATOR",
        sub_sector="AML_CFT",
    ),
    _entity(
        "Nigerian Financial Intelligence Unit",
        "nigerian-financial-intelligence-unit",
        "REGULATORY_BODY",
        ("NFIU", "Nigeria FIU"),
        sector="REGULATOR",
        sub_sector="FINANCIAL_INTELLIGENCE",
    ),
    _entity(
        "Economic and Financial Crimes Commission",
        "economic-and-financial-crimes-commission",
        "REGULATORY_BODY",
        ("EFCC",),
        sector="REGULATOR",
        sub_sector="FINANCIAL_CRIME_ENFORCEMENT",
    ),
    _entity(
        "National Information Technology Development Agency",
        "national-information-technology-development-agency",
        "REGULATORY_BODY",
        ("NITDA",),
        sector="REGULATOR",
        sub_sector="INFORMATION_TECHNOLOGY",
    ),
    _entity(
        "First City Monument Bank",
        "first-city-monument-bank",
        "COMPANY",
        ("FCMB", "FCMB Bank"),
        sector="BANKING",
        sub_sector="COMMERCIAL_BANK",
    ),
    _entity(
        "Providus Bank",
        "providus-bank",
        "COMPANY",
        ("ProvidusBank",),
        sector="BANKING",
        sub_sector="COMMERCIAL_BANK",
    ),
    _entity(
        "Jaiz Bank",
        "jaiz-bank",
        "COMPANY",
        ("Jaiz Bank Nigeria",),
        sector="BANKING",
        sub_sector="NON_INTEREST_BANK",
    ),
    _entity(
        "Nomba",
        "nomba",
        "COMPANY",
        ("Nomba Financial Services", "Kudi", "Kudi.ai"),
        sector="FINTECH",
        sub_sector="PAYMENT_TERMINALS",
    ),
    _entity(
        "Mono",
        "mono",
        "COMPANY",
        ("Mono Technologies", "Mono Africa"),
        sector="FINTECH",
        sub_sector="OPEN_BANKING",
    ),
    _entity(
        "Okra",
        "okra",
        "COMPANY",
        ("Okra Technologies", "Okra Africa"),
        sector="FINTECH",
        sub_sector="OPEN_BANKING",
    ),
    _entity(
        "MainOne",
        "mainone",
        "INFRASTRUCTURE_PROVIDER",
        ("MainOne Cable Company", "MainOne an Equinix company"),
        sector="TELECOMMUNICATIONS",
        sub_sector="INTERNET_INFRASTRUCTURE",
    ),
    _entity(
        "MoMo Payment Service Bank",
        "momo-payment-service-bank",
        "COMPANY",
        ("MoMo PSB", "MTN MoMo", "Y'ello Digital Financial Services"),
        sector="BANKING",
        sub_sector="PAYMENT_SERVICE_BANK",
    ),
    _entity(
        "Nigerian Exchange Group",
        "nigerian-exchange-group",
        "INFRASTRUCTURE_PROVIDER",
        ("NGX", "NGX Group", "Nigerian Exchange"),
        sector="FINANCIAL_INFRASTRUCTURE",
        sub_sector="SECURITIES_EXCHANGE",
    ),
    _entity(
        "FMDQ Group",
        "fmdq-group",
        "INFRASTRUCTURE_PROVIDER",
        ("FMDQ", "FMDQ Securities Exchange"),
        sector="FINANCIAL_INFRASTRUCTURE",
        sub_sector="SECURITIES_EXCHANGE",
    ),
)


def validate_seed_data() -> None:
    """Fail fast when a data edit would make the production seed unsafe."""
    if len(ENTITY_SEEDS) < 80:
        raise ValueError("entity registry launch seed must contain at least 80 rows")

    slugs = [entity.entity_slug for entity in ENTITY_SEEDS]
    if len(slugs) != len(set(slugs)):
        duplicates = sorted({slug for slug in slugs if slugs.count(slug) > 1})
        raise ValueError(f"duplicate entity slugs: {', '.join(duplicates)}")

    invalid_types = sorted(
        {entity.entity_type for entity in ENTITY_SEEDS} - ENTITY_TYPES
    )
    if invalid_types:
        raise ValueError(f"invalid entity types: {', '.join(invalid_types)}")

    missing_additions = NIGERIA_LAUNCH_ADDITION_SLUGS - set(slugs)
    if missing_additions:
        raise ValueError(
            "missing Nigeria launch additions: " + ", ".join(sorted(missing_additions))
        )

    for entity in ENTITY_SEEDS:
        if entity.parent_slug is not None and entity.parent_slug not in slugs:
            raise ValueError(
                f"unknown parent slug {entity.parent_slug!r} for {entity.entity_slug!r}"
            )
        if len(entity.aliases) != len(set(entity.aliases)):
            raise ValueError(f"duplicate aliases for {entity.entity_slug!r}")


validate_seed_data()
