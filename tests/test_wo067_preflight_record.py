"""
WO-067 — BITE PROOF: the twelve-term preflight record belongs IN the corpus, hashed at capture.

THE GAP. Every Kraken run carries a `PREFLIGHT.json` in its run directory. The Hyperliquid legs
carried none — the twelve-term record went to `.artifacts/wo066/`, which is git-ignored and
outside the corpus entirely. It surfaced concretely in WO-067 §1: confirming the Hyperliquid grant
had not lapsed meant reading a scratch file, because no corpus artifact held the expiry. A capture
whose opening record cannot be read back FROM the corpus cannot be audited from it — structurally
the same defect as WO-055's `raw_text_trim_events`, which reached the object and never the record.

WHAT THIS PINS, and each one is a way the repair could be quietly undone:

  1. the record LANDS IN THE RUN DIRECTORY, not in a scratch path
  2. it is HASHED AT CAPTURE and written through to the segment ledger before the socket
  3. it is written EVEN WHEN THE VERDICT IS RED — a refused launch is the case you most want to
     audit, and WO-066's four failed launches left no corpus artifact saying which term was RED
  4. it records the AMBIENT VARIABLES BY NAME AND VALUE, including when unset
  5. a RED verdict REFUSES the run (0.9 — the economic effect, not a log line)

0.11 ON THE AMBIENT SET. WO-066 discovered four ambient variables one failed launch at a time and
recorded that the one deciding whether a socket can open at all — `DATA_SOURCE` — was absent from
every preflight record ever written, so no past leg's artifacts can answer "what was DATA_SOURCE
when this corpus was captured?". `None` (unset) is a recorded value here, because unset is exactly
the state that produced two of those failed launches.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from tools import hyperliquid_preflight as pf


REQUIRED_AMBIENT = (
    "TRADING_ENV",
    "DATA_SOURCE",                 # the one WO-066 found in NO preflight record at all
    "CORPUS_DIR",
    "HYPERLIQUID_GRANT_EXPIRY",    # the one WO-067 §1 had to recover from a scratch file
    "CORPUS_AUTO_MODE_CONFIRMED",
)


@pytest.fixture(autouse=True)
def _fast_terms(monkeypatch):
    """Stub the two terms that are slow BY DESIGN, so this module tests the record not the gates.

    Term 4 samples CPU over 1 s and term 10 is the WO-059 pagefile-MOVEMENT gate, which observes a
    60 s / 2 s / 30-sample window — deliberately, because a movement gate cannot measure movement
    instantaneously. Six real evaluations would add six minutes to every CI run.

    THE STUBS DO NOT WEAKEN ANYTHING HERE. These tests assert what the RECORD contains and where it
    LANDS; term 4 and term 10 keep their own proofs in tests/test_capture_gate.py and are executed
    for real by the launch path. Both stubs return GREEN so the verdict is decided by the terms
    each test is actually about.
    """
    import psutil
    from trading.data import capture_gate

    monkeypatch.setattr(psutil, "cpu_percent", lambda interval=None: 1.0)

    class _Green:
        green = flow_green = memory_green = True
        max_move_pp = 0.0
        free_mib = 4096.0

        def to_dict(self):
            return {"green": True, "flow_green": True, "memory_green": True,
                    "detail": "stubbed for the record tests"}

    monkeypatch.setattr(capture_gate, "evaluate", lambda *a, **k: _Green())


@pytest.fixture
def evaluated(monkeypatch):
    """Run the real twelve terms once. Opens no socket — that is the preflight's whole contract."""
    monkeypatch.setenv("TRADING_ENV", "paper")
    record, all_green = pf.evaluate()
    return record, all_green


# ── the record itself ─────────────────────────────────────────────────────────────────────────

def test_evaluate_returns_a_record_and_a_verdict_rather_than_exiting(evaluated):
    """It must be CALLABLE. As module-level script code its only output was a git-ignored file."""
    record, all_green = evaluated
    assert isinstance(record, dict) and isinstance(all_green, bool)
    assert len(record["terms"]) == 12, (
        f"twelve terms were enumerated from the code (0.11); got {len(record['terms'])}")
    assert record["all_green"] == all_green, "the verdict must be IN the record, not only returned"


def test_bite_the_record_carries_the_ambient_variables_that_gate_the_run(evaluated):
    """BITE — the WO-066 §6 finding, closed. Every gating variable by NAME AND VALUE."""
    record, _ = evaluated
    ambient = record["ambient"]
    for name in REQUIRED_AMBIENT:
        assert name in ambient, (
            f"{name} is absent from the preflight record. WO-066: 'the variable deciding whether "
            f"a socket can open is absent from the run's own opening record, so no past leg's "
            f"artifacts can answer what it was.'")


def test_dual_an_unset_ambient_variable_is_recorded_as_unset_not_omitted(monkeypatch):
    """DUAL — `None` is a recorded value. Omitting it would erase the state that caused failures.

    Two of WO-066's four failed launches were caused by a variable being UNSET. A record that
    simply leaves unset variables out cannot distinguish "unset" from "this record predates the
    field", which is the `count: 0` / `count: null` distinction one directory over.
    """
    monkeypatch.setenv("TRADING_ENV", "paper")
    monkeypatch.delenv("HYPERLIQUID_GRANT_EXPIRY", raising=False)
    record, _ = pf.evaluate()

    assert "HYPERLIQUID_GRANT_EXPIRY" in record["ambient"], "unset must not mean omitted"
    assert record["ambient"]["HYPERLIQUID_GRANT_EXPIRY"] is None


def test_bite_a_red_term_is_recorded_with_which_term_was_red(monkeypatch):
    """BITE — a RED verdict still produces a full record naming the failing term.

    A refused launch is the case you most want to audit. WO-066 had four of them and not one left
    a corpus artifact saying which condition was RED.
    """
    monkeypatch.setenv("TRADING_ENV", "paper")
    monkeypatch.delenv("HYPERLIQUID_GRANT_EXPIRY", raising=False)
    record, all_green = pf.evaluate()

    assert not all_green, "an unset grant expiry must make term 12 RED"
    assert record["terms"]["grant_expiry"]["green"] is False
    assert len(record["terms"]) == 12, "a RED run must still record all twelve terms"


# ── the capture-side wiring ───────────────────────────────────────────────────────────────────

def test_bite_the_capture_writes_the_record_into_the_run_directory_and_hashes_it(tmp_path,
                                                                                 monkeypatch):
    """BITE — the record lands in the CORPUS and its digest is ledgered before the socket.

    Asserts the artifact on disk, not that a function was called: the defect being repaired was
    precisely a record that existed somewhere else.
    """
    monkeypatch.setenv("TRADING_ENV", "paper")
    monkeypatch.chdir(tmp_path)

    import tools.hyperliquid_capture as cap_mod
    from trading.data.corpus import CorpusLedger

    root = tmp_path / "captures" / "hyperliquid"
    ledger = CorpusLedger(root, "hlspike_test", host="test",
                          segment_patterns=cap_mod.SEGMENT_PATTERNS)
    cap = cap_mod.HyperliquidCapture(ledger, "20260821170000", 3600.0, None)

    cap._write_preflight_record()

    path = cap.run_dir / cap_mod.PREFLIGHT_FILENAME
    assert path.exists(), (
        "no PREFLIGHT.json in the run directory — the record is outside the corpus again, which "
        "is the entire defect")

    written = json.loads(path.read_text(encoding="utf-8"))
    assert len(written["terms"]) == 12
    assert written["run_id"] == "20260821170000"
    assert written["corpus_id"] == "hlspike_test"

    # hashed AT CAPTURE, and the digest must match the bytes actually written
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert cap._preflight_digest == expected, "the recorded digest does not match the file"

    ledger_path = cap.run_dir / cap_mod.SEGMENT_LEDGER
    assert ledger_path.exists(), "nothing written through to the segment ledger"
    events = [json.loads(ln) for ln in ledger_path.read_text(encoding="utf-8").splitlines() if ln]
    pre = [e for e in events if e.get("event") == "preflight_recorded"]
    assert len(pre) == 1, f"expected one preflight_recorded event, got {len(pre)}"
    assert pre[0]["sha256"] == expected
    assert pre[0]["hashed_at_capture"] is True


def test_dual_the_record_is_written_even_when_the_verdict_is_red(tmp_path, monkeypatch):
    """DUAL — RED must not skip the write. A refused launch still owes an auditable record."""
    monkeypatch.setenv("TRADING_ENV", "paper")
    monkeypatch.delenv("HYPERLIQUID_GRANT_EXPIRY", raising=False)
    monkeypatch.chdir(tmp_path)

    import tools.hyperliquid_capture as cap_mod
    from trading.data.corpus import CorpusLedger

    ledger = CorpusLedger(tmp_path / "captures" / "hyperliquid", "hlspike_red", host="test",
                          segment_patterns=cap_mod.SEGMENT_PATTERNS)
    cap = cap_mod.HyperliquidCapture(ledger, "20260821170001", 3600.0, None)

    green = cap._write_preflight_record()

    assert green is False, "the fixture must produce a RED verdict"
    path = cap.run_dir / cap_mod.PREFLIGHT_FILENAME
    assert path.exists(), (
        "a RED preflight wrote NO record — the launches you most need to audit are the refused "
        "ones, and WO-066 had four that left nothing behind")
    assert cap._preflight_digest is not None, "a RED record must still be hashed"


def test_mutation_writing_to_a_scratch_path_leaves_the_corpus_unauditable(tmp_path, monkeypatch):
    """MUTATION — write the record to `.artifacts/` instead. That is the pre-fix behaviour.

    The mutant produces an identical-looking JSON file and an identical digest. What it cannot do
    is let a reader holding ONLY the corpus find it — which is the property under test, and the
    reason "it was recorded somewhere" was never good enough.
    """
    monkeypatch.setenv("TRADING_ENV", "paper")
    monkeypatch.chdir(tmp_path)

    import tools.hyperliquid_capture as cap_mod
    from trading.data.corpus import CorpusLedger

    ledger = CorpusLedger(tmp_path / "captures" / "hyperliquid", "hlspike_mut", host="test",
                          segment_patterns=cap_mod.SEGMENT_PATTERNS)
    cap = cap_mod.HyperliquidCapture(ledger, "20260821170002", 3600.0, None)

    record, _ = pf.evaluate()
    scratch = tmp_path / ".artifacts" / "wo066"
    scratch.mkdir(parents=True)
    (scratch / "hyperliquid_preflight.json").write_text(json.dumps(record, default=str),
                                                        encoding="utf-8")

    # The mutant "recorded" the preflight — and the corpus holds nothing.
    assert not (cap.run_dir / cap_mod.PREFLIGHT_FILENAME).exists()
    assert not (cap.run_dir / cap_mod.SEGMENT_LEDGER).exists()

    # The real path puts it where a corpus reader will find it.
    cap._write_preflight_record()
    assert (cap.run_dir / cap_mod.PREFLIGHT_FILENAME).exists()


def test_reachability_the_capture_refuses_to_start_on_a_red_preflight():
    """0.14 — the record is written by the launch path, and RED stops it (0.9)."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "tools" / "hyperliquid_capture.py").read_text(
        encoding="utf-8")

    assert "cap._write_preflight_record()" in src, "the launch path never records the preflight"
    assert "HL_PREFLIGHT_RED" in src, "a RED preflight does not refuse the run"
    assert "if not cap._write_preflight_record():" in src, (
        "the preflight result is computed but not acted on — a guard that records a verdict and "
        "proceeds anyway is a log line, not a gate (0.9)")
