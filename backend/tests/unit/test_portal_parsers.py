"""Unit tests for the CBK circulars portal adapter and NFIU gazette portal monitor."""

from __future__ import annotations

from app.ingestion.feed_parsers.portal_parser import parse_cbk_portal, parse_gazette_portal


class TestCBKPortalParser:
    SAMPLE_HTML = b"""<!DOCTYPE html>
    <html>
      <head><title>Central Bank of Kenya Circulars</title></head>
      <body>
        <div class="content">
          <a href="/uploads/banking_circulars/Banking_Circular_No_1_2026.pdf">
            Banking Circular No. 1 of 2026 - Changes to CBK Discount Window Facility
          </a>
          <a href="https://www.centralbank.go.ke/regulations-and-licensing/guidelines-2026.pdf">
            National Payment System Risk Guidelines 2026
          </a>
          <a href="/about-us/">About the Bank</a>
          <a href="/contact/">Contact Us</a>
        </div>
      </body>
    </html>
    """

    def test_parse_cbk_extracts_circulars(self) -> None:
        signals = parse_cbk_portal(self.SAMPLE_HTML, "CBK Circulars")
        assert len(signals) == 2
        titles = [s.raw_title for s in signals]
        assert any("Banking Circular No. 1 of 2026" in t for t in titles)
        assert any("National Payment System Risk Guidelines 2026" in t for t in titles)
        # URLs must be resolved to absolute URLs
        assert all(s.source_url.startswith("https://www.centralbank.go.ke") for s in signals)
        # Content hash must be 64-character SHA-256
        assert all(len(s.content_hash) == 64 for s in signals)

    def test_parse_cbk_empty_html(self) -> None:
        signals = parse_cbk_portal(b"", "CBK Circulars")
        assert signals == []


class TestGazettePortalParser:
    SAMPLE_HTML = b"""<!DOCTYPE html>
    <html>
      <head><title>NFIU AML/CFT Gazette Portal</title></head>
      <body>
        <div class="notices">
          <a href="/gazettes/2026/Advisory_Notice_AML_CFT_Fintechs.pdf">
            Advisory Notice on AML/CFT Compliance Measures for Digital Asset Custodians
          </a>
          <a href="/publications/sanctions-list-update-2026.pdf">
            Public Notice: Consolidated Sanctions List Update
          </a>
          <a href="/home">Home Page</a>
        </div>
      </body>
    </html>
    """

    def test_parse_gazette_extracts_advisories(self) -> None:
        signals = parse_gazette_portal(self.SAMPLE_HTML, "NFIU Gazette")
        assert len(signals) == 2
        titles = [s.raw_title for s in signals]
        assert any("AML/CFT" in t for t in titles)
        assert any("Sanctions List Update" in t for t in titles)
        assert all(s.source_url.startswith("https://nfiu.gov.ng") for s in signals)
        assert all(len(s.content_hash) == 64 for s in signals)

    def test_maintenance_page_is_not_a_regulatory_notice(self) -> None:
        html = b"<html><body>" + b"<p>NFIU Portal undergoing routine maintenance.</p>" * 20 + b"</body></html>"
        signals = parse_gazette_portal(html, "NFIU Gazette")
        assert signals == []
