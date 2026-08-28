"""Reviewed production source manifest for the Nigeria-first launch."""

from __future__ import annotations

from dataclasses import dataclass


MANIFEST_VERSION = "2026.08-v4"
TAXONOMY_DOMAINS = frozenset(
    {
        "REGULATORY_POLICY",
        "COMPETITIVE_PRODUCT",
        "INFRASTRUCTURE_RELIABILITY",
        "CUSTOMER_MARKET",
        "FINANCIAL_ECONOMIC",
        "CAPITAL_PARTNERSHIP",
        "MARKET_EXPANSION",
        "FRAUD_RISK_TRUST",
    }
)


@dataclass(frozen=True)
class LaunchSource:
    source_code: str
    source_name: str
    source_type: str
    tier: int
    base_url: str
    auth_type: str
    schedule_cron: str | None
    priority_class: str
    reliability_score: float
    coverage_domains: tuple[str, ...]
    review_reference: str
    max_attempts: int = 3


LAUNCH_SOURCES = (
    LaunchSource(
        "CBN_CIRCULARS_API",
        "Central Bank of Nigeria Circulars API",
        "API",
        1,
        "https://www.cbn.gov.ng/api/GetAllCirculars",
        "NO_AUTH",
        "2,17,32,47 * * * *",
        "CRITICAL",
        0.99,
        ("REGULATORY_POLICY", "FINANCIAL_ECONOMIC", "FRAUD_RISK_TRUST"),
        "https://www.cbn.gov.ng/RSS/CircularsRSS.html",
    ),
    LaunchSource(
        "CBN_NEWS_API",
        "Central Bank of Nigeria News API",
        "API",
        1,
        "https://www.cbn.gov.ng/api/GetAllNews",
        "NO_AUTH",
        "8,38 * * * *",
        "HIGH",
        0.98,
        ("FINANCIAL_ECONOMIC", "CUSTOMER_MARKET", "MARKET_EXPANSION"),
        "https://www.cbn.gov.ng/RSS/createrssfromdb.html",
    ),
    LaunchSource(
        "SEC_NIGERIA_CIRCULARS_HTML",
        "Securities and Exchange Commission Nigeria Circulars",
        "HTML",
        1,
        "https://sec.gov.ng/for-investors/keep-track-of-circulars/",
        "NO_AUTH",
        "5,35 * * * *",
        "HIGH",
        0.98,
        ("REGULATORY_POLICY", "CAPITAL_PARTNERSHIP", "FRAUD_RISK_TRUST"),
        "https://sec.gov.ng/for-investors/keep-track-of-circulars/",
    ),
    LaunchSource(
        "NDPC_NEWS_HTML",
        "Nigeria Data Protection Commission News",
        "HTML",
        1,
        "https://ndpc.gov.ng/news/",
        "NO_AUTH",
        "7,37 * * * *",
        "HIGH",
        0.97,
        ("REGULATORY_POLICY", "FRAUD_RISK_TRUST"),
        "https://ndpc.gov.ng/news/",
    ),
    LaunchSource(
        "PAYSTACK_STATUS_API",
        "Paystack Public Service Status API",
        "API",
        1,
        "https://status.paystack.com/v3/summary.json",
        "NO_AUTH",
        "*/5 * * * *",
        "CRITICAL",
        0.98,
        ("INFRASTRUCTURE_RELIABILITY",),
        "https://status.paystack.com/public-api",
    ),
    LaunchSource(
        "FLUTTERWAVE_STATUS_API",
        "Flutterwave Public Service Status API",
        "API",
        1,
        "https://status.flutterwave.com/api/v2/summary.json",
        "NO_AUTH",
        "1,6,11,16,21,26,31,36,41,46,51,56 * * * *",
        "CRITICAL",
        0.98,
        ("INFRASTRUCTURE_RELIABILITY",),
        "https://status.flutterwave.com/",
    ),
    LaunchSource(
        "FLUTTERWAVE_BLOG_HTML",
        "Flutterwave Product and Company Blog",
        "HTML",
        2,
        "https://flutterwave.com/us/blog/",
        "NO_AUTH",
        "11,41 * * * *",
        "STANDARD",
        0.90,
        ("COMPETITIVE_PRODUCT", "MARKET_EXPANSION", "CAPITAL_PARTNERSHIP"),
        "https://flutterwave.com/us/blog/",
    ),
    LaunchSource(
        "MONIEPOINT_BLOG_HTML",
        "Moniepoint Product and Company Blog",
        "HTML",
        2,
        "https://moniepoint.com/blog",
        "NO_AUTH",
        "13,43 * * * *",
        "STANDARD",
        0.90,
        ("COMPETITIVE_PRODUCT", "CUSTOMER_MARKET", "MARKET_EXPANSION"),
        "https://moniepoint.com/blog",
    ),
    LaunchSource(
        "TECHCABAL_RSS",
        "TechCabal African Technology Feed",
        "RSS",
        2,
        "https://techcabal.com/feed/",
        "NO_AUTH",
        "3,23,43 * * * *",
        "STANDARD",
        0.84,
        ("COMPETITIVE_PRODUCT", "CAPITAL_PARTNERSHIP", "MARKET_EXPANSION"),
        "https://techcabal.com/feed/",
    ),
    LaunchSource(
        "DISRUPT_AFRICA_RSS",
        "Disrupt Africa Startup News Feed",
        "RSS",
        2,
        "https://disruptafrica.com/feed/",
        "NO_AUTH",
        "9,39 * * * *",
        "STANDARD",
        0.82,
        ("COMPETITIVE_PRODUCT", "CAPITAL_PARTNERSHIP", "MARKET_EXPANSION"),
        "https://disruptafrica.com/feed/",
    ),
    LaunchSource(
        "TECHNEXT_RSS",
        "Technext African Technology Feed",
        "RSS",
        2,
        "https://technext24.com/feed/",
        "NO_AUTH",
        "14,44 * * * *",
        "STANDARD",
        0.80,
        ("COMPETITIVE_PRODUCT", "CUSTOMER_MARKET", "FRAUD_RISK_TRUST"),
        "https://technext24.com/feed/",
    ),
    LaunchSource(
        "BUSINESSDAY_TECH_RSS",
        "BusinessDay Nigeria Technology Feed",
        "RSS",
        2,
        "https://businessday.ng/technology/feed/",
        "NO_AUTH",
        "16,46 * * * *",
        "STANDARD",
        0.86,
        ("FINANCIAL_ECONOMIC", "CUSTOMER_MARKET", "CAPITAL_PARTNERSHIP"),
        "https://businessday.ng/technology/feed/",
    ),
    LaunchSource(
        "GDELT_NIGERIA_DISCOVERY",
        "GDELT Nigeria Fintech and Taxonomy Discovery",
        "LIVE_SEARCH",
        3,
        "https://api.gdeltproject.org/api/v2/doc/doc",
        "NO_AUTH",
        "*/10 * * * *",
        "STANDARD",
        0.78,
        tuple(sorted(TAXONOMY_DOMAINS)),
        "https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/",
    ),
    LaunchSource(
        "NBS_NIGERIA_HTML",
        "National Bureau of Statistics Nigeria",
        "HTML",
        1,
        "https://www.nigerianstat.gov.ng/",
        "NO_AUTH",
        "27 6,18 * * *",
        "HIGH",
        0.98,
        ("FINANCIAL_ECONOMIC", "CUSTOMER_MARKET"),
        "https://www.nigerianstat.gov.ng/",
    ),
    LaunchSource(
        "CBN_PAYMENT_OVERSIGHT_PDF_2026",
        "CBN Payments System Market Structure and Oversight Circular",
        "PDF",
        1,
        (
            "https://www.cbn.gov.ng/Out/2026/CCD/"
            "CIRCULAR%20ON%20INTRODUCTION%20OF%20MARKET%20STRUCTURE%20REQUIREMENTS,%20"
            "DATA%20LOCALISATION,%20ULTIMATE%20BENEFICIAL%20OWNERSHIP%20DISCLOSURE,%20"
            "AND%20SYSTEMIC%20OVERSIGHT%20MEASURES%20IN%20THE%20NIGERIA%20PAYMENTS%20SYSTEM.pdf"
        ),
        "NO_AUTH",
        None,
        "HIGH",
        0.99,
        ("REGULATORY_POLICY", "INFRASTRUCTURE_RELIABILITY"),
        "https://www.cbn.gov.ng/RSS/CircularsRSS.html",
    ),
    LaunchSource(
        "TENANT_EVIDENCE_UPLOAD",
        "Tenant-Authenticated Evidence Upload",
        "USER_UPLOAD",
        1,
        "s3://tenant-uploads/tenant/",
        "AWS_IAM",
        None,
        "CRITICAL",
        1.0,
        ("CUSTOMER_MARKET",),
        "SC-DOC-004 section 5.1",
    ),
)
