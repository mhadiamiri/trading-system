"""
Reason-code vocabulary safety (WO-008b-A3, addendum B).

RULED: **NO REASON CODE MAY BE A PREFIX OF ANOTHER REASON CODE.**

Why this outlives the bug that prompted it: even with every assertion converted
to exact matching, prefix-overlapping codes remain a latent trap for every future
grep, log query and dashboard filter. The VOCABULARY must be safe, not merely
today's assertions against it.

The bug that prompted it: `test_no_market_state_guard` passed with its own guard
disabled, because `EXEC_NO_MARKET_STATE` is a prefix of the
`EXEC_NO_MARKET_STATE_TIMESTAMP` raised by the adjacent guard — so a substring
assertion could not tell the two mechanisms apart (rule 0.1d).
"""

import itertools
import re
from pathlib import Path

import pytest

from trading.logkit.decision import VALID_REASON_CODES

SRC = Path(__file__).resolve().parents[1] / "src"

# Codes raised in production but not (yet) declared in VALID_REASON_CODES.
# Discovered by WO-008b-A3's sweep: the staleness codes were never added to the
# vocabulary, so a check over the declared list alone would have passed while the
# real collision sat in raise strings. Both sets are checked.
_RAISED_CODE_RE = re.compile(r'"([A-Z][A-Z0-9_]{3,}):')


def _declared_codes():
    return sorted(set(itertools.chain.from_iterable(VALID_REASON_CODES.values())))


def _raised_codes():
    """Scrape reason codes from raise/message strings across production code."""
    found = set()
    for path in SRC.rglob("*.py"):
        for match in _RAISED_CODE_RE.finditer(path.read_text(encoding="utf-8")):
            found.add(match.group(1))
    return sorted(found)


def _prefix_collisions(codes):
    return [(a, b) for a, b in itertools.permutations(codes, 2) if b.startswith(a)]


class TestReasonCodePrefixFreedom:
    """The ruled naming constraint, enforced mechanically."""

    def test_declared_vocabulary_is_prefix_free(self):
        codes = _declared_codes()
        assert codes, "reason-code vocabulary is empty"
        collisions = _prefix_collisions(codes)
        assert collisions == [], (
            f"REASON CODE PREFIX COLLISION in the declared vocabulary: {collisions}. "
            f"No reason code may be a prefix of another (WO-008b-A3 addendum B)."
        )

    def test_codes_raised_in_production_are_prefix_free(self):
        """
        The check that would actually have caught the original bug.

        The declared vocabulary was already prefix-free — because the staleness
        codes were never declared. The collision lived entirely in raise strings,
        so scanning only the declared list proves nothing about production.
        """
        codes = _raised_codes()
        assert codes, "no reason codes found in production sources"
        collisions = _prefix_collisions(codes)
        assert collisions == [], (
            f"REASON CODE PREFIX COLLISION among codes raised in production: "
            f"{collisions}. No reason code may be a prefix of another."
        )

    def test_declared_and_raised_codes_are_jointly_prefix_free(self):
        """A declared code must not be a prefix of an undeclared raised one."""
        codes = sorted(set(_declared_codes()) | set(_raised_codes()))
        collisions = _prefix_collisions(codes)
        assert collisions == [], (
            f"REASON CODE PREFIX COLLISION across declared+raised codes: {collisions}."
        )

    def test_the_check_can_actually_detect_a_collision(self):
        """
        Rule 0.1d: prove the mechanism works rather than trusting an empty result.

        Three green assertions above are only meaningful if the detector fires on
        a real collision.
        """
        assert _prefix_collisions(["EXEC_NO_MARKET_STATE", "EXEC_NO_MARKET_STATE_TIMESTAMP"]) == [
            ("EXEC_NO_MARKET_STATE", "EXEC_NO_MARKET_STATE_TIMESTAMP")
        ]
        assert _prefix_collisions(["ALPHA", "BETA"]) == []
