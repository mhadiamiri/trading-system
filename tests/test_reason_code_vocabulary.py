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


_DECLARATION_SITE = "decision.py"  # where VALID_REASON_CODES lives


def _production_source_text():
    """
    Production source concatenated, EXCLUDING the vocabulary declaration site.

    A code's DECLARATION in VALID_REASON_CODES is not a code path emitting it. If
    the declaration counted as production, property 2 could never fail (it would be
    a 0.1d false guarantee — declaring a code would 'prove' it producible). So the
    declaration module is excluded, and producibility means EMITTED elsewhere.
    """
    return "\n".join(
        p.read_text(encoding="utf-8")
        for p in SRC.rglob("*.py")
        if p.name != _DECLARATION_SITE
    )


# WO-013 §2: the known-set exemption is REMOVED. It formerly held KILL_SWITCH_ENGAGED, LONG_SIGNAL,
# and SHORT_SIGNAL — declared codes that no code path emitted. WO-013 wired all three to the
# PRODUCTION decision-log emission path (interface.py KillSwitchEngagedError default;
# live.py signal reason_codes), each certified by a behavioral proof
# (tests/integration/test_reason_code_emission.py). `declared => producible` now holds with NO
# exceptions; the empty set below is retained only so the enforcement bite proof has a symbol to
# assert against, and to make the closure explicit rather than deleting the concept silently.
_KNOWN_UNPRODUCIBLE = {}


def _is_producible(code, source_text):
    """
    A declared code is producible if it appears as a STRING LITERAL in production.

    Broader than _raised_codes() (which only sees colon-form raise strings): risk
    and strategy codes like PASS/VETO/NO_SIGNAL are produced as reason_code values
    and enum members, never raised with a colon. A declared code that appears
    nowhere in production as a literal is one no code path can produce (rule 0.1d
    in vocabulary form).
    """
    return (
        f'"{code}"' in source_text
        or f"'{code}'" in source_text
        or f'"{code}:' in source_text
        or f"'{code}:" in source_text
    )


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


class TestReasonCodeCompleteness:
    """
    WO-011 §5: the vocabulary in use and the vocabulary on file must agree.

    Three properties (property 3, prefix-freedom across the union, is enforced by
    TestReasonCodePrefixFreedom above):
      1. Every code RAISED in production is DECLARED.
      2. Every DECLARED code is producible by some code path.
    """

    def test_every_raised_code_is_declared(self):
        """Property 1: no code is raised in production without being declared."""
        declared = set(_declared_codes())
        raised = _raised_codes()
        assert raised, "no reason codes found in production sources"
        undeclared = sorted(set(raised) - declared)
        assert undeclared == [], (
            f"codes RAISED in production but NOT DECLARED in VALID_REASON_CODES: "
            f"{undeclared}. The audit trail would speak words the dictionary lacks "
            f"(WO-011 §5 property 1)."
        )

    def test_every_declared_code_is_producible(self):
        """
        Property 2: EVERY declared code is producible by a code path — FULLY ENFORCED, no
        exceptions (WO-013 §2 removed the known-set exemption). Bites on ANY declared code that
        no code path can produce (rule 0.1d in vocabulary form). The _KNOWN_UNPRODUCIBLE set is
        now empty, so `new_unproducible` == `unproducible` and the assertion is unconditional.
        """
        source = _production_source_text()
        declared = set(_declared_codes())
        assert declared, "reason-code vocabulary is empty"
        unproducible = {c for c in declared if not _is_producible(c, source)}

        # Keep the known set honest: every entry must still be declared AND still
        # unproducible — no stale suppression hiding a now-producible or removed code.
        stale = {
            c for c in _KNOWN_UNPRODUCIBLE
            if c not in declared or c not in unproducible
        }
        assert not stale, (
            f"stale _KNOWN_UNPRODUCIBLE entries (now producible or undeclared): {sorted(stale)}"
        )

        new_unproducible = unproducible - set(_KNOWN_UNPRODUCIBLE)
        assert new_unproducible == set(), (
            f"NEW declared codes that no code path can produce: {sorted(new_unproducible)}. "
            f"Rule 0.1d in vocabulary form (WO-011 §5 property 2). Report; do not delete "
            f"without asking. Known/reported set: {sorted(_KNOWN_UNPRODUCIBLE)}."
        )

    def test_property1_check_actually_detects_an_undeclared_raised_code(self):
        """Rule 0.1d: prove property 1's mechanism fires on a real gap."""
        declared = {"ALPHA"}
        raised = ["ALPHA", "BETA_UNDECLARED"]
        assert sorted(set(raised) - declared) == ["BETA_UNDECLARED"]
        assert sorted({"ALPHA"} - {"ALPHA"}) == []

    def test_property2_check_actually_detects_an_unproducible_code(self):
        """Rule 0.1d: prove property 2's mechanism fires on a real gap."""
        source = 'reason_code = "ALPHA_USED"\n'
        assert _is_producible("ALPHA_USED", source)
        assert not _is_producible("GAMMA_NEVER_EMITTED", source)
