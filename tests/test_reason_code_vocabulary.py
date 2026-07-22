"""
Vocabulary safety + completeness across BOTH governed namespaces (reason_code AND event_type).

RULED (WO-008b-A3 addendum B): NO CODE MAY BE A PREFIX OF ANOTHER — a latent trap for every grep,
log query and dashboard filter. Extended by WO-018 to the UNION of reason_code and event_type,
because a cross-namespace prefix/identity is exactly how a canonical literal borrows the governed
namespace's credibility (WO-013 §0: NO_SIGNAL read "producible" via its event_type literal).

THE FOUR PROPERTIES, now across BOTH namespaces (WO-018 §4):
  1. raised/emitted => declared     — both namespaces, both LITERAL forms (colon "CODE:" AND
                                       keyword reason_code=/event_type=). Closes the reason_code=
                                       escape hatch (WO-018 §2).
  2. declared => producible         — both namespaces, scan EXCLUDING the declaration site.
  3. prefix-freedom across the UNION of both vocabularies.
  4. the scan reads EMITTED strings, never the declared lists.

Detection-method note (WO-018 §1): the scan matches the LITERAL forms. Values emitted via VARIABLE
indirection (reason_code=<var>: the risk REASON_* constants, signal_reason, e.reason_code; and
event_type=decision.value) are NOT statically resolved here — they are covered by (a) declaring their
resolved values, verified in the §1 denominator, and (b) for the RiskDecision enum event_types, the
mechanical drift guard test_event_type_risk_values_match_enum below. A check is bounded by the form it
matches and the namespace it reads (WO-018 §8); those bounds are stated, not hidden.

DECLARED LIMIT — the variable-indirection residual (WO-018 follow-up B), stated in the HOST_SUSPEND /
active-probe form so the bound is read where the guard is read, not only in a report:
  - CAUGHT: every reason_code / event_type emitted as a string LITERAL at the call site — colon
    "CODE:", reason_code="CODE", event_type="CODE" (any case). raised⇒declared holds for these.
  - NOT CAUGHT: an emission through VARIABLE INDIRECTION whose value is not a literal at the call
    site — reason_code=<var>, reason_code=self.SOME_CONST, reason_code=e.reason_code,
    event_type=decision.value. The scan does not statically resolve the variable to its string.
  - WHAT THE UNCAUGHT CASE LOOKS LIKE: a future emission adds `reason_code=new_var` where `new_var`
    holds an UNDECLARED string. raised⇒declared reads only literals, so it never sees `new_var`, and
    the code ships as a GOVERNED SYSTEM EMITTING AN UNGOVERNED CODE — the colon-form blind spot one
    level in. (Symmetric half: declared⇒producible is satisfied for a declared code by its CONSTANT
    DEFINITION, or even a COMMENT / DOCSTRING mention, not only by a genuine emit — WO-018 follow-up
    A; the successor WO's tightened "reachable-as-emitted" scan closes that half. Not fixed here.)
  - WHAT COVERS THE GAP TODAY, AND WHAT DOES NOT: the §1 enumeration was a ONE-TIME semantic pass
    that resolved the current indirected values and DECLARED them; the enum-drift guard
    (test_event_type_risk_values_match_enum) pins ONLY the RiskDecision event_types emitted as
    event_type=decision.value. NEITHER covers a NEW indirection introduced after this pass — that is
    the standing residual, load-bearing until the successor WO's tightened scan lands.
"""

import itertools
import re
from pathlib import Path

import pytest

from trading.logkit.decision import VALID_REASON_CODES, VALID_EVENT_TYPES

SRC = Path(__file__).resolve().parents[1] / "src"
_DECLARATION_SITE = "decision.py"  # where VALID_REASON_CODES and VALID_EVENT_TYPES live

# ── Literal-form scanners (WO-018 §2/§4: both forms, both namespaces) ────────────────────────────
_RC_COLON = re.compile(r'"([A-Z][A-Z0-9_]{3,}):')                       # form (1): raise "CODE:"
_RC_KWARG = re.compile(r'reason_code(?:\s*:\s*\w+)?\s*=\s*"([A-Z_][A-Z0-9_]{3,})"')  # form (2)
_ET_KWARG = re.compile(r'event_type\s*=\s*"([A-Za-z_][A-Za-z0-9_]{2,})"')            # form (3), any case


def _src_files():
    return sorted(SRC.rglob("*.py"))


def _declared_reason_codes():
    return sorted(set(itertools.chain.from_iterable(VALID_REASON_CODES.values())))


def _declared_event_types():
    return sorted(set(itertools.chain.from_iterable(VALID_EVENT_TYPES.values())))


def _emitted_reason_codes():
    """Every reason_code EMITTED in production, by literal form (colon + keyword). Reads strings, not
    the declared list."""
    found = set()
    for path in _src_files():
        text = path.read_text(encoding="utf-8")
        found.update(_RC_COLON.findall(text))
        found.update(_RC_KWARG.findall(text))
    return sorted(found)


def _emitted_event_types():
    """Every event_type EMITTED in production (keyword form) PLUS the RiskDecision enum values, which
    are emitted via event_type=decision.value (variable form)."""
    found = set()
    for path in _src_files():
        found.update(_ET_KWARG.findall(path.read_text(encoding="utf-8")))
    from trading.risk.interface import RiskDecision
    found.update(d.value for d in RiskDecision)
    return sorted(found)


def _production_source_text():
    """Production source concatenated, EXCLUDING the declaration site (decision.py). A declaration is
    not a code path emitting the value (WO-011 §5 / rule 0.1d) — producibility means EMITTED elsewhere."""
    return "\n".join(p.read_text(encoding="utf-8") for p in _src_files()
                     if p.name != _DECLARATION_SITE)


def _is_producible(code, source_text):
    return (f'"{code}"' in source_text or f"'{code}'" in source_text
            or f'"{code}:' in source_text or f"'{code}:" in source_text)


def _prefix_collisions(codes):
    return [(a, b) for a, b in itertools.permutations(codes, 2) if b.startswith(a)]


# ── Property 1: raised/emitted => declared, BOTH namespaces, BOTH forms ──────────────────────────
class TestRaisedImpliesDeclared:
    def test_every_emitted_reason_code_is_declared(self):
        declared = set(_declared_reason_codes())
        emitted = _emitted_reason_codes()
        assert emitted, "no reason codes found emitted in production"
        undeclared = sorted(set(emitted) - declared)
        assert undeclared == [], (
            f"reason codes EMITTED in production (colon or keyword form) but NOT DECLARED: "
            f"{undeclared}. The reason_code= escape hatch (WO-018 §2) must stay closed."
        )

    def test_every_emitted_event_type_is_declared(self):
        declared = set(_declared_event_types())
        emitted = _emitted_event_types()
        assert emitted, "no event types found emitted in production"
        undeclared = sorted(set(emitted) - declared)
        assert undeclared == [], (
            f"event_types EMITTED in production but NOT DECLARED in VALID_EVENT_TYPES: {undeclared}. "
            f"The event_type namespace is governed now (WO-018 §3)."
        )


# ── Property 2: declared => producible, BOTH namespaces (excluding the declaration site) ─────────
class TestDeclaredImpliesProducible:
    def test_every_declared_reason_code_is_producible(self):
        source = _production_source_text()
        unproducible = sorted(c for c in _declared_reason_codes() if not _is_producible(c, source))
        assert unproducible == [], (
            f"declared reason codes that NO code path can produce: {unproducible} (rule 0.1d in "
            f"vocabulary form). Fully enforced — no exemptions (WO-013 §2)."
        )

    def test_every_declared_event_type_is_producible(self):
        source = _production_source_text()
        unproducible = sorted(c for c in _declared_event_types() if not _is_producible(c, source))
        assert unproducible == [], (
            f"declared event_types that NO code path can produce: {unproducible}."
        )


# ── Property 3: prefix-freedom across the UNION of both vocabularies ─────────────────────────────
class TestPrefixFreedomAcrossUnion:
    def test_declared_union_is_prefix_free(self):
        union = sorted(set(_declared_reason_codes()) | set(_declared_event_types()))
        collisions = _prefix_collisions(union)
        assert collisions == [], (
            f"PREFIX COLLISION in the UNION of reason_code + event_type vocabularies: {collisions}. "
            f"A cross-namespace prefix is how a canonical literal borrows credibility (WO-013 §0)."
        )

    def test_emitted_union_is_prefix_free(self):
        union = sorted(set(_emitted_reason_codes()) | set(_emitted_event_types()))
        collisions = _prefix_collisions(union)
        assert collisions == [], (
            f"PREFIX COLLISION among EMITTED codes across both namespaces: {collisions}."
        )

    def test_the_detector_actually_fires(self):
        # rule 0.1d: prove the mechanism, don't trust an empty result.
        assert _prefix_collisions(["EXEC_NO_MARKET_STATE", "EXEC_NO_MARKET_STATE_TIMESTAMP"]) == [
            ("EXEC_NO_MARKET_STATE", "EXEC_NO_MARKET_STATE_TIMESTAMP")]
        assert _prefix_collisions(["ALPHA", "BETA"]) == []


# ── Enum drift guard (WO-018 §3): the RISK event_types MUST equal RiskDecision.value ─────────────
def test_event_type_risk_values_match_enum():
    """A hand-restated enum is a second source of truth waiting to diverge. decision.py (logkit) must
    not import trading.risk (layering / cycle), so the sync is enforced HERE (tests may import both):
    the RISK group of VALID_EVENT_TYPES must equal the RiskDecision values, exactly."""
    from trading.risk.interface import RiskDecision
    assert set(VALID_EVENT_TYPES["RISK"]) == {d.value for d in RiskDecision}


# ── Property-mechanism self-tests (0.1d) ────────────────────────────────────────────────────────
class TestScansActuallyDetect:
    def test_reason_code_kwarg_form_is_seen(self):
        # the escape hatch: a non-colon keyword reason_code= literal must be visible to the scan.
        assert _RC_KWARG.findall('reason_code="BOGUS_UNDECLARED_CODE"') == ["BOGUS_UNDECLARED_CODE"]
        assert _RC_KWARG.findall('reason_code: str = "DEFAULT_CODE"') == ["DEFAULT_CODE"]

    def test_event_type_kwarg_form_is_seen_any_case(self):
        assert _ET_KWARG.findall('event_type="UPPER_CASE"') == ["UPPER_CASE"]
        assert _ET_KWARG.findall('event_type="lower_case"') == ["lower_case"]

    def test_producibility_detector_fires(self):
        assert _is_producible("ALPHA_USED", 'reason_code = "ALPHA_USED"\n')
        assert not _is_producible("GAMMA_NEVER_EMITTED", 'reason_code = "ALPHA_USED"\n')
