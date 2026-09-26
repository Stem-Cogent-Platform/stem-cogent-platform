import json

from app.ingestion.feed_parsers.json_api_parser import parse_cbn_api
from app.ingestion.incoming_sources import resolve_feed_link


def test_cbn_relative_pdf_links_keep_feed_identity_hash():
    payload = json.dumps([{'Title': 'A circular', 'Link': '/Out/2026/CCD/example.pdf'}]).encode()
    item = parse_cbn_api(payload, 'CBN Circulars')[0]
    assert item.source_url == 'https://www.cbn.gov.ng/Out/2026/CCD/example.pdf'
    from app.ingestion.feed_parsers.models import IncomingSignal
    assert item.content_hash == IncomingSignal.compute_hash('/Out/2026/CCD/example.pdf', 'A circular')


def test_relative_link_resolution_requires_configured_provenance():
    assert resolve_feed_link('/Out/test.pdf', 'Unknown') == '/Out/test.pdf'
    assert resolve_feed_link('//evil.example/test', 'CBN Circulars') == '//evil.example/test'
    assert resolve_feed_link('https://evil.example/test', 'CBN Circulars') == 'https://evil.example/test'
    assert resolve_feed_link('Out/test.pdf', 'CBN Circulars') == 'https://www.cbn.gov.ng/Out/test.pdf'
