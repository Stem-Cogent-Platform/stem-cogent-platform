"""Reviewed production source manifest for the Nigeria-first launch."""

from __future__ import annotations

from dataclasses import dataclass


MANIFEST_VERSION = "2026.08-v1"


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
    primary_domain: str
    review_reference: str
    max_attempts: int = 3


LAUNCH_SOURCES = (
    LaunchSource(
        "CBN_CIRCULARS_RSS",
        "Central Bank of Nigeria Circulars RSS",
        "RSS",
        1,
        "https://www.cbn.gov.ng/RSS/CircularsRSS.html",
        "NO_AUTH",
        "*/15 * * * *",
        "CRITICAL",
        0.99,
        "REGULATORY_POLICY",
        "https://www.cbn.gov.ng/Documents/circulars.html",
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
        "INFRASTRUCTURE_RELIABILITY",
        "https://status.paystack.com/public-api",
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
        "REGULATORY_POLICY",
        "https://ndpc.gov.ng/news/",
    ),
    LaunchSource(
        "NIBSS_MEDIA_HTML",
        "Nigeria Inter-Bank Settlement System Media",
        "HTML",
        1,
        "https://nibss-plc.com.ng/media/",
        "NO_AUTH",
        "*/15 * * * *",
        "HIGH",
        0.95,
        "INFRASTRUCTURE_RELIABILITY",
        "https://nibss-plc.com.ng/media/",
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
        "COMPETITIVE_PRODUCT",
        "https://flutterwave.com/us/blog/",
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
        "REGULATORY_POLICY",
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
        "CUSTOMER_MARKET",
        "SC-DOC-004 section 5.1",
    ),
)
