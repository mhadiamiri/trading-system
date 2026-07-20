"""
Capture-redaction scan (WO-011 section 6.2).

The scan must FIRE on an unredacted session/connection identifier and be CLEAN
after redaction. This is the mechanical replacement for the per-script inline
regex that A3 used — the pattern set is now the single source of truth.
"""

from trading.logkit.redaction import redact, scan, REDACTION_PATTERNS


# A realistic Kraken v2 status frame with an unredacted connection_id.
UNREDACTED = (
    '{"channel":"status","type":"update","data":[{"connection_id":18446744073709551615,'
    '"api_version":"v2","system":"online","version":"2.0.9"}]}'
)


class TestRedactionScan:
    def test_scan_fires_on_unredacted_connection_id(self):
        """The bite: an unredacted identifier is detected."""
        hits = scan(UNREDACTED)
        assert hits, "scan must FIRE on an unredacted connection_id"
        assert any(name == "connection_id" for name, _ in hits), hits

    def test_scan_is_clean_after_redaction(self):
        """redact() removes what scan() detects — round-trip is clean."""
        redacted = redact(UNREDACTED)
        assert "18446744073709551615" not in redacted, "identifier value must be gone"
        assert "<REDACTED>" in redacted
        assert scan(redacted) == [], f"scan must be clean after redaction, got {scan(redacted)}"

    def test_scan_detector_actually_distinguishes(self):
        """
        Rule 0.1d: prove the scan can both fire and stay silent, so a green result
        is meaningful. A no-op 'redaction' would leave the identifier and scan would
        still fire — the failure the bite proof exercises.
        """
        assert scan('{"connection_id":12345}')  # fires
        assert scan('{"connection_id":"<REDACTED>"}') == []  # silent when redacted
        assert scan('{"symbol":"BTC/USD"}') == []  # silent when nothing to find

    def test_every_pattern_has_a_name(self):
        """The pattern set is the single source of truth for redact() and scan()."""
        assert REDACTION_PATTERNS
        assert all(name and pat for name, pat in REDACTION_PATTERNS)
