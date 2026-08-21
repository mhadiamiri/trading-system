"""
WO-066 queue item (a) — BITE PROOF: a declared `--seam-cause` with no referent must REFUSE.

FOUND IN THE FIELD, not in review. WO-066 §6 attempt #4: a Kraken leg 3 launch carried
`--seam-cause POLICY_SHUTDOWN` against a corpus that already held runs, but `CORPUS_DIR` was
wrong. The ledger read an empty directory, found no prior run, printed "FIRST run of this corpus
— no seam owed", went GREEN, and started. The launch looked healthy. It was reading the wrong
corpus, and the ONE piece of evidence that said so — the operator's own declaration — was
discarded without a line of output.

WHY THE GUARD WAS THERE AND STILL DID NOT FIRE. `CorpusLedger.open_seam` does validate a cause
against the closed set. But it is only ever reached on the branch where a prior run exists. The
half of the space with no prior run was never validated at all, so the check sat one branch away
from the case that needed it. That is the same shape as `checksum_failures_total` (wired, always
zero) and term 11 (an expression no host state could turn RED): a guard whose reachable inputs
cannot include the failure.

THE ASYMMETRY, NAMED. Two contradictions are possible between the operator and the disk:

    prior run exists, no cause declared   -> already REFUSED (SeamCauseUndeclared)
    cause declared, no prior run exists   -> was SILENT; this is what these tests pin

`--seam-cause` is only ever typed by someone who believes this is a resume. If the disk disagrees
exactly one of them is wrong, and the disk-side reading is the one that fails for a mundane
reason: an unset or mistyped corpus root names an empty directory, and an empty directory is
indistinguishable from a genuinely new corpus.

0.9 — THE ECONOMIC EFFECT, NOT THE EVENT RECORD. The assertion is not that a warning is logged.
It is that the process REFUSES: `require_seam_referent` raises, the preflight seam term goes RED,
and `all_green` is False, so no socket opens and no frame is written into the wrong corpus.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from trading.data.corpus import (
    CORPUS_SEAM_CAUSES,
    CorpusLedger,
    RunRecord,
    SeamCauseWithoutReferent,
    require_seam_referent,
)


PRIOR_LAST = "2026-08-12T08:16:02.556556+00:00"


def _ledger_with_prior(tmp_path) -> CorpusLedger:
    led = CorpusLedger(tmp_path, "phaseb_test", host="test")
    led.add_run(RunRecord(run_id="run_prior", start_utc="2026-08-12T02:30:15+00:00",
                          first_frame_utc="2026-08-12T02:30:15.104454+00:00",
                          last_frame_utc=PRIOR_LAST, finalized=True))
    return led


def _empty_ledger(tmp_path) -> CorpusLedger:
    return CorpusLedger(tmp_path, "phaseb_test", host="test")


# ── BITE ──────────────────────────────────────────────────────────────────────────────────────

def test_bite_declared_cause_against_an_empty_corpus_dir_refuses(tmp_path):
    """BITE — the real attempt #4: right corpus-id, WRONG root, cause declared. Must refuse."""
    wrong_root = tmp_path / "captures" / "corpus_24h"     # exists, holds no runs
    wrong_root.mkdir(parents=True)
    led = _empty_ledger(wrong_root)

    assert led.prior_run() is None, "the fixture must reproduce the empty-directory reading"

    with pytest.raises(SeamCauseWithoutReferent) as exc:
        require_seam_referent(led.prior_run(), "POLICY_SHUTDOWN",
                              corpus_id="phaseb_test", corpus_root=wrong_root)

    assert "NO PRIOR RUN" in str(exc.value)
    assert "phaseb_test" in str(exc.value), "the refusal must name the corpus it searched"
    assert str(wrong_root) in str(exc.value), (
        "the refusal must name the ROOT it searched — that string is the whole diagnosis, since "
        "the operator's next question is which directory the process actually looked in")


def test_bite_an_undeclared_cause_string_refuses_even_with_no_prior_run(tmp_path):
    """BITE — a cause outside the closed set names nothing whether or not a prior run exists.

    `open_seam` catches this, but only when a prior run exists. `hyperliquid_capture.py` takes
    `--seam-cause` as a free string with no argparse `choices=`, so this is the reachable path.
    """
    led = _empty_ledger(tmp_path)
    with pytest.raises(SeamCauseWithoutReferent) as exc:
        require_seam_referent(led.prior_run(), "CHECKSUM_RESYNC",
                              corpus_id="phaseb_test", corpus_root=tmp_path)
    assert "not one of" in str(exc.value)
    assert "CHECKSUM_RESYNC" in str(exc.value)


# ── DUALS — the guard must not fire on ordinary launches ──────────────────────────────────────

def test_dual_an_ordinary_first_run_is_not_refused(tmp_path):
    """DUAL — no prior run and no cause declared is the ordinary first run. Silence is correct.

    A guard that refused this would refuse every new corpus, which is worse than no guard.
    """
    led = _empty_ledger(tmp_path)
    require_seam_referent(led.prior_run(), "", corpus_id="phaseb_test", corpus_root=tmp_path)
    require_seam_referent(led.prior_run(), None, corpus_id="phaseb_test", corpus_root=tmp_path)


def test_dual_an_ordinary_resume_is_not_refused(tmp_path):
    """DUAL — prior run present and a declared cause. The referent exists; proceed."""
    led = _ledger_with_prior(tmp_path)
    for cause in CORPUS_SEAM_CAUSES:
        require_seam_referent(led.prior_run(), cause,
                              corpus_id="phaseb_test", corpus_root=tmp_path)


def test_dual_a_resume_missing_its_cause_is_left_to_the_existing_guard(tmp_path):
    """DUAL — the reverse contradiction is NOT this function's job.

    Prior run, no cause: already refused by the preflight seam term and by `open_seam`. If this
    function also raised here, a passing test would no longer discriminate between the two guards
    and the older one could rot undetected.
    """
    led = _ledger_with_prior(tmp_path)
    require_seam_referent(led.prior_run(), "", corpus_id="phaseb_test", corpus_root=tmp_path)


# ── MUTATION — the discriminating check ───────────────────────────────────────────────────────

def test_mutation_dropping_the_prior_run_check_lets_the_bite_pass(tmp_path):
    """MUTATION — neuter the referent test; the BITE stops biting while every DUAL still passes.

    This is what makes the bite discriminating rather than incidental. The mutant is the exact
    pre-fix behaviour: validate the cause string, then return regardless of whether anything
    exists for it to describe.
    """
    def mutant(prior, declared_cause, *, corpus_id, corpus_root):
        if not declared_cause:
            return
        if declared_cause not in CORPUS_SEAM_CAUSES:
            raise SeamCauseWithoutReferent("not one of ...")
        return                                    # <- the dropped check

    led = _empty_ledger(tmp_path)

    # The bite no longer bites — this is precisely the silence that shipped.
    mutant(led.prior_run(), "POLICY_SHUTDOWN", corpus_id="phaseb_test", corpus_root=tmp_path)

    # ...while every dual still passes, so no other test would have caught the regression.
    mutant(led.prior_run(), "", corpus_id="phaseb_test", corpus_root=tmp_path)
    led2 = _ledger_with_prior(tmp_path / "b")
    mutant(led2.prior_run(), "POLICY_SHUTDOWN", corpus_id="phaseb_test", corpus_root=tmp_path)

    with pytest.raises(SeamCauseWithoutReferent):
        require_seam_referent(led.prior_run(), "POLICY_SHUTDOWN",
                              corpus_id="phaseb_test", corpus_root=tmp_path)


# ── REACHABILITY (0.14) — the production call sites, asserted rather than claimed ──────────────

def test_reachability_both_launchers_call_the_guard():
    """0.14 — an unwired guard is the WO-055 defect. Both capture entry points must call it.

    Structural, because the alternative is launching two real captures against wrong roots. The
    defect existed at BOTH launchers; repairing one and citing the other would reproduce it.
    """
    root = Path(__file__).resolve().parents[1]
    for rel in ("tools/live_corpus_capture.py", "tools/hyperliquid_capture.py"):
        src = (root / rel).read_text(encoding="utf-8")
        assert "require_seam_referent(" in src, (
            f"{rel} does not call require_seam_referent — the guard is unreachable from the "
            f"path that actually opens a socket, which is the WO-055 defect verbatim")
