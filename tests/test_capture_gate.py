"""
WO-057 §2 — THE RE-SPECIFIED TERM 2 GATE.

§0.10 — single-purpose tests. §0.12 — every verdict states its falsifier, and these are the tests
that make the falsifiers real: a gate that could not go RED would be the same defect one level up
from the abort conditions this WO exists to fix.
"""

from trading.data import capture_gate

MIB = 1024 ** 2


def _sampler(free_mib, flow_sequence, stock_mib=0):
    """A scripted (free, stock, flow) sampler. `flow_sequence` is consumed one per call.

    WO-058: FLOW gates, STOCK is context. Default stock 0 keeps the flow tests focused; the
    flow-vs-stock tests set it deliberately.
    """
    seq = list(flow_sequence)

    def sample():
        flow = seq.pop(0) if seq else 0.0
        return int(free_mib * MIB), int(stock_mib * MIB), flow

    return sample


def _no_sleep(_seconds):
    return None


# ══════════════════════════════════════════════════════════════════════════════════════════════
# THE GATE CAN GO GREEN, AND IT CAN GO RED — BOTH HALVES, SEPARATELY
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_green_when_paging_flow_is_zero_and_memory_clears_the_floor():
    v = capture_gate.evaluate(sampler=_sampler(2048, [0.0] * 5), sample_count=5,
                              sleep_fn=_no_sleep)
    assert v.green and v.flow_green and v.memory_green


def test_BITE_red_when_the_host_is_actually_paging():
    """THE BITE (2.3). Paging flow above the declared bound is RED — D46's chain runs through
    exactly this."""
    # STOCK is non-zero here ON PURPOSE. A host that is actively paging necessarily HAS pagefile
    # bytes in use — a paging host with zero stock is not a real configuration. Modelling it with
    # stock=0 would make this test fail under the stock-gating mutation too, and the proof's whole
    # value is that the bite CANNOT distinguish the two criteria while the dual can.
    v = capture_gate.evaluate(sampler=_sampler(2048, [0.0, 0.0, 250.0, 0.0, 0.0], stock_mib=900),
                              sample_count=5, sleep_fn=_no_sleep)
    assert not v.green and not v.flow_green
    assert v.memory_green, "the memory half is independent and must not be dragged red"
    assert "IS PAGING" in v.detail


def test_DUAL_green_when_flow_is_zero_but_STOCK_is_large():
    """THE PRE-RULED DUAL (2.3) — the whole point of D58 ruling 3.

    A host can hold half a gigabyte of pagefile STOCK and read ZERO pages per second; Windows
    retains those bytes proactively. WO-057 gated on the stock and made a capture the host was
    always able to run look impossible for a second time.
    """
    v = capture_gate.evaluate(sampler=_sampler(2048, [0.0] * 5, stock_mib=512), sample_count=5,
                              sleep_fn=_no_sleep)
    assert v.green, "zero flow with non-zero stock is GREEN"
    assert v.stock_mib == 512.0, "and the stock is still REPORTED"
    assert "CONTEXT" in v.detail


def test_a_low_trickle_below_the_per_sample_bound_still_fails_on_the_mean():
    """The second shape the bounds catch: a steady trickle that never trips the per-sample bound
    but shows the host paging continuously."""
    v = capture_gate.evaluate(sampler=_sampler(2048, [5.0] * 6), sample_count=6,
                              sleep_fn=_no_sleep)
    assert not v.flow_green, "max 5.0 <= 10.0 but the mean 5.0 exceeds 1.0"


def test_the_gate_FAILS_CLOSED_when_the_counter_cannot_be_read():
    """A gate that cannot measure must not pass. `None` is the ABSENCE of a reading and is
    deliberately not treated as 0.0 — 0.0 would be a claim that the host is not paging."""
    v = capture_gate.evaluate(sampler=_sampler(2048, [None] * 3), sample_count=3,
                              sleep_fn=_no_sleep)
    assert not v.green and not v.flow_green
    assert v.flow_available is False
    assert "FAILING CLOSED" in v.detail


def test_red_when_free_memory_is_below_the_declared_floor():
    v = capture_gate.evaluate(sampler=_sampler(100, [0.0] * 5), sample_count=5, sleep_fn=_no_sleep)
    assert not v.green and not v.memory_green
    assert v.flow_green, "the flow half is independent and must not be dragged red"


def test_the_two_halves_are_reported_separately():
    """A gate that collapsed both halves into one boolean could not tell an operator WHICH
    condition to fix — and the two need entirely different actions."""
    v = capture_gate.evaluate(sampler=_sampler(100, [0.0, 900.0]), sample_count=2,
                              sleep_fn=_no_sleep)
    d = v.to_dict()
    assert d["flow_green"] is False and d["memory_green"] is False
    assert "IS PAGING" in d["detail"] and "declared floor" in d["detail"]


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §2.1 THE FOOTPRINT DERIVATION — the arithmetic is executable, not just described
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_the_derived_requirement_is_computed_from_its_declared_components():
    """The derivation lives in code, so a future edit to one component cannot leave the total
    stale — the failure mode that produced the 12.33 GB figure this gate replaces."""
    expected = (capture_gate.CAPTURE_PROCESS_BASELINE_MIB
                + capture_gate.RETENTION_BYTE_CAP_MIB
                + capture_gate.SEGMENT_CLOSE_TRANSIENT_MIB) * capture_gate.FRAGMENTATION_ALLOWANCE
    assert capture_gate.DERIVED_REQUIREMENT_MIB == expected
    assert abs(capture_gate.DERIVED_REQUIREMENT_MIB - 307.84) < 0.01


def test_the_flow_bounds_are_declared_and_rounded_up_per_0_15():
    """0.15: a margin-bearing figure rounds up and says so. Both bounds sit above the
    order-of-magnitude derivation rather than being fitted to it."""
    assert capture_gate.MAX_PAGING_FLOW_PER_SAMPLE == 10.0
    assert capture_gate.MAX_PAGING_FLOW_MEAN == 1.0
    assert "Pages/sec" in capture_gate.PAGING_FLOW_COUNTER


def test_the_soft_fault_counter_is_deliberately_not_the_gate():
    """`Page Faults/sec` reads thousands per second on any idle Windows box because it counts SOFT
    faults, satisfied from RAM. A gate on it would be permanently RED — the exact failure this
    WO ends."""
    assert "Page Faults" not in capture_gate.PAGING_FLOW_COUNTER


def test_the_declared_floor_is_above_the_derived_requirement():
    """A floor below its own derivation would be decoration."""
    assert capture_gate.MIN_FREE_MEMORY_MIB > capture_gate.DERIVED_REQUIREMENT_MIB


def test_the_retention_component_matches_the_adapter_s_actual_cap():
    """The footprint's dominant bounded term is the adapter's byte cap. If someone raises the cap
    without revisiting the gate, this fails rather than the gate quietly under-reserving."""
    from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter

    assert (capture_gate.RETENTION_BYTE_CAP_MIB * MIB
            == KrakenV2BookAdapter.MAX_RETAINED_RAW_BYTES)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §2.2 THE OBSERVATION WINDOW — declared, and actually observed
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_the_window_is_declared_and_the_sample_count_follows_from_it():
    assert capture_gate.SWAP_OBSERVATION_WINDOW_SECONDS == 60.0
    assert capture_gate.SWAP_SAMPLE_INTERVAL_SECONDS == 2.0
    assert capture_gate.SWAP_SAMPLE_COUNT == 30


def test_the_gate_actually_samples_the_declared_number_of_times():
    """A window is only 'sustained' if it is observed more than once. This is the test that stops
    the window being a comment above a single reading."""
    calls = []

    def counting_sampler():
        calls.append(1)
        return 4096 * MIB, 0, 0.0

    capture_gate.evaluate(sampler=counting_sampler, sample_count=7, sleep_fn=_no_sleep)
    assert len(calls) == 7


def test_the_verdict_carries_its_falsifier():
    """0.12: an observation offered as corroboration states what would have falsified it — and it
    travels in the artifact, not only in a docstring."""
    d = capture_gate.evaluate(sampler=_sampler(2048, [0.0]), sample_count=1,
                              sleep_fn=_no_sleep).to_dict()
    assert "falsified" in d["falsifier"]
    assert "pages/sec" in d["falsifier"]
    assert "Swap STOCK cannot falsify it" in d["falsifier"], "stock is context, not a criterion"
    assert "consecutive windows" in d["falsifier"], "the WINDOW's own adequacy has a falsifier too"


def test_the_verdict_records_the_evidence_not_just_the_answer():
    d = capture_gate.evaluate(sampler=_sampler(2048, [0.0, 0.0, 3.0], stock_mib=77),
                              sample_count=3, sleep_fn=_no_sleep).to_dict()
    assert d["flow_samples"] == 3
    assert d["max_flow_pages_per_sec"] == 3.0
    assert d["stock_swap_in_use_mib_CONTEXT_ONLY"] == 77.0, "stock reported, never gating"
    assert d["gated_on"].startswith("paging FLOW")
    assert d["observation_window_seconds"] == 60.0


# ══════════════════════════════════════════════════════════════════════════════════════════════
# §2.3 THE PREFLIGHT READS IT — and a RED gate blocks
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_the_preflight_reads_the_gate_rather_than_re_deriving_it():
    """§2.3: verified by reading the committed code, not by intending it."""
    from pathlib import Path

    source = Path("tools/live_corpus_capture.py").read_text(encoding="utf-8")
    assert "capture_gate.evaluate()" in source, "the preflight must CALL the gate"
    assert 'record["conditions"]["term2_memory_gate"]' in source, "and record its verdict"
    # And it must not carry its own copy of the threshold. Checked on EXECUTABLE lines only: the
    # site deliberately explains the superseded 12.33 figure in a comment, and matching that
    # comment would make this assertion fail for the opposite of the right reason.
    code = "\n".join(ln for ln in source.splitlines() if not ln.lstrip().startswith("#"))
    assert "12.33" not in code, "the superseded figure must not be live code in the runner"


def test_a_red_gate_makes_the_preflight_refuse(tmp_path, monkeypatch):
    """THE ONE THAT MATTERS: the gate is not decoration. A RED gate must stop the run.

    Every other test in the capture suite patches the gate green so it can exercise other things;
    this is the test that proves the patched-out thing can actually refuse.
    """
    import os
    from datetime import date, timedelta

    import pytest

    from trading.data import capture_gate as gate_mod
    from tools.live_corpus_capture import CorpusCaptureError, CorpusCaptureRunner, RotationConfig

    monkeypatch.setattr(
        gate_mod, "evaluate",
        lambda *a, **k: gate_mod.GateVerdict(
            green=False, flow_green=False, memory_green=True, free_mib=8192.0,
            flow_samples=[0.0, 410.0], detail="host IS PAGING at idle (max 410.00 pages/sec)"))
    for key, value in {
        "CORPUS_AUTO_MODE_CONFIRMED": "true",
        "CORPUS_SHUTDOWN_POLICY_DISABLED": "true",
        "CORPUS_GRANT_EXPIRY": (date.today() + timedelta(days=1)).isoformat(),
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr("time.sleep", lambda *_: None)
    assert os.environ["CORPUS_AUTO_MODE_CONFIRMED"] == "true"

    with pytest.raises(CorpusCaptureError, match="PREFLIGHT_FAILED"):
        CorpusCaptureRunner(
            config=RotationConfig(corpus_dir=tmp_path, corpus_id="gate_red"),
            trading_env="paper", duration_hours=0.0001)
