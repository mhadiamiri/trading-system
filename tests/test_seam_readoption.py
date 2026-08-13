"""
WO-066 — BITE PROOF: a failed resume must not mint a second seam for the same gap.

FOUND IN THE FIELD, not in review. Launching Kraken leg 3 on 2026-08-12, the preflight passed and
the seam opened — and the run then died at `create_live_capture_feed` because DATA_SOURCE was
`simulated`. The guard refused correctly, before any socket. But the seam was already open, and its
`resumed_run_id` named a run that produced no frames and never would.

WHY THAT IS NOT COSMETIC. An unresolved seam is read as +infinity (`corpus_reader.Discontinuity`:
`end_utc: None => OPEN-ENDED, read as +infinity`). It therefore intersects EVERY later query, and
the default-deny reader refuses the whole corpus from that instant onward. A single failed launch
would have made the entire following 25-hour capture unreadable — the corpus would still be on
disk, and no honest reader would hand any of it out.

THE FIX IS NOT TO OPEN THE SEAM LATER. It opens before the socket on purpose: the left bound is
known then, and a process killed mid-run must leave the seam LOUD rather than absent. The fix is
that a gap which never closed is still the SAME gap — so a resume finding an unresolved seam with
the same measured left bound adopts it instead of appending a duplicate.

MATCHED ON THE MEASURED LEFT BOUND, NOT THE RUN ID. That is what keeps adoption from swallowing a
genuinely different gap: a different gap has a different `prior_last_frame_utc` and still gets its
own seam.
"""

from __future__ import annotations

import json

import pytest

from trading.data.corpus import CorpusLedger, RunRecord, SeamCauseUndeclared


PRIOR_LAST = "2026-08-12T08:16:02.556556+00:00"


def ledger_with_prior(tmp_path) -> CorpusLedger:
    led = CorpusLedger(tmp_path, "phaseb_test", host="test")
    led.add_run(RunRecord(run_id="run_prior", start_utc="2026-08-12T02:30:15+00:00",
                          first_frame_utc="2026-08-12T02:30:15.104454+00:00",
                          last_frame_utc=PRIOR_LAST, finalized=False))
    return led


def test_bite_a_failed_resume_does_not_leave_two_open_seams(tmp_path):
    """BITE — the real 2026-08-12 sequence: open a seam, die before the first frame, resume."""
    led = ledger_with_prior(tmp_path)

    first = led.open_seam("POLICY_SHUTDOWN", "run_prior", "run_died", PRIOR_LAST)
    assert not first.resolved

    # The launch dies at adapter resolution. No frame is ever emitted by run_died.
    second = led.open_seam("POLICY_SHUTDOWN", "run_prior", "run_real", PRIOR_LAST)

    assert len(led.manifest.seams) == 1, (
        f"a failed resume minted a second seam for the same gap; the first can never be closed "
        f"and, read as +infinity, it would refuse every query over the rest of the corpus. "
        f"seams={[s.to_dict() for s in led.manifest.seams]}")
    assert second is first
    assert second.resumed_run_id == "run_real", "the adopted seam still names the dead run"
    assert len(led.manifest.open_seams) == 1


def test_the_adopted_seam_closes_normally_and_the_corpus_is_readable_again(tmp_path):
    """The economic effect (0.9): after the real run emits, NOTHING is left open."""
    led = ledger_with_prior(tmp_path)
    led.open_seam("POLICY_SHUTDOWN", "run_prior", "run_died", PRIOR_LAST)
    seam = led.open_seam("POLICY_SHUTDOWN", "run_prior", "run_real", PRIOR_LAST)

    led.close_seam(seam, "2026-08-13T01:35:00+00:00")

    assert led.manifest.open_seams == [], (
        "an open seam survives, so the default-deny reader still refuses the corpus")
    # 2026-08-12T08:16:02.556556Z -> 2026-08-13T01:35:00Z = 17 h 18 m 57.44 s
    assert seam.duration_seconds == pytest.approx(62337.44, abs=1.0)


def test_dual_a_genuinely_different_gap_still_gets_its_own_seam(tmp_path):
    """DUAL — adoption must not swallow a real second discontinuity.

    A guard that collapsed every seam into one would hide real gaps, which is worse than the defect
    it fixes: the corpus would read as continuous across a window that has no data.
    """
    led = ledger_with_prior(tmp_path)
    first = led.open_seam("POLICY_SHUTDOWN", "run_prior", "run_a", PRIOR_LAST)
    led.close_seam(first, "2026-08-13T01:35:00+00:00")

    led.add_run(RunRecord(run_id="run_a", start_utc="2026-08-13T01:35:00+00:00",
                          first_frame_utc="2026-08-13T01:35:00+00:00",
                          last_frame_utc="2026-08-13T09:00:00+00:00", finalized=True))
    second = led.open_seam("PROCESS_RESTART", "run_a", "run_b", "2026-08-13T09:00:00+00:00")

    assert len(led.manifest.seams) == 2, "a genuinely different gap was swallowed by adoption"
    assert second is not first
    assert second.seam_id == 1


def test_an_unresolved_seam_with_a_different_left_bound_is_not_adopted(tmp_path):
    """The discriminator is the MEASURED left bound, so two open gaps stay two gaps."""
    led = ledger_with_prior(tmp_path)
    led.open_seam("POLICY_SHUTDOWN", "run_prior", "run_a", PRIOR_LAST)
    other = led.open_seam("PROCESS_RESTART", "run_a", "run_b", "2026-08-13T09:00:00+00:00")

    assert len(led.manifest.seams) == 2
    assert len(led.manifest.open_seams) == 2
    assert other.prior_last_frame_utc == "2026-08-13T09:00:00+00:00"


def test_adoption_is_recorded_in_the_write_through_ledger_not_only_in_memory(tmp_path):
    """The seam ledger is the durable record; adoption has to be visible in it.

    A reader reconstructing history from the JSONL must be able to see that a resume was attempted
    and failed — smoothing that away would hide a real launch failure from the record.
    """
    led = ledger_with_prior(tmp_path)
    led.open_seam("POLICY_SHUTDOWN", "run_prior", "run_died", PRIOR_LAST)
    led.open_seam("POLICY_SHUTDOWN", "run_prior", "run_real", PRIOR_LAST)

    events = [json.loads(ln) for ln in
              led.seam_ledger_path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    assert [e["event"] for e in events] == ["open", "readopted"]
    assert events[-1]["resumed_run_id"] == "run_real"
    assert "READOPTED" in events[-1]["detail"]
    assert "run_died" not in events[-1]["resumed_run_id"]


def test_mutation_removing_adoption_restores_the_defect(tmp_path, monkeypatch):
    """MUTATION — make the scan find nothing: two seams reappear, one permanently open."""
    led = ledger_with_prior(tmp_path)

    real_seams = led.manifest.seams
    monkeypatch.setattr(type(led.manifest), "seams",
                        property(lambda self: real_seams, lambda self, v: None), raising=False)

    led.open_seam("POLICY_SHUTDOWN", "run_prior", "run_died", PRIOR_LAST)
    # Neuter adoption by hiding the existing seam from the scan only.
    original = list(real_seams)
    real_seams.clear()
    led.open_seam("POLICY_SHUTDOWN", "run_prior", "run_real", PRIOR_LAST)
    real_seams[:0] = original

    assert len(real_seams) == 2, "the mutation did not reach the adoption scan"
    assert len([s for s in real_seams if not s.resolved]) == 2, (
        "without adoption, the failed resume's seam stays open forever — which is the defect")


def test_an_undeclared_cause_is_still_refused_on_the_adoption_path(tmp_path):
    """Adoption must not become a way past the cause declaration."""
    led = ledger_with_prior(tmp_path)
    led.open_seam("POLICY_SHUTDOWN", "run_prior", "run_died", PRIOR_LAST)

    with pytest.raises(SeamCauseUndeclared):
        led.open_seam("GUESSED", "run_prior", "run_real", PRIOR_LAST)
