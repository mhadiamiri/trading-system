"""
WO-057 §2 — THE RE-SPECIFIED TERM 2 GATE (D57 ruling 1).

Committed code in the tree it certifies (the D51 standing rule), so the gate is a figure anyone can
recompute rather than a number carried between reports.

═══════════════════════════════════════════════════════════════════════════════════════════════
⚠ WHY THE OLD GATE HAD TO GO — AND IT WAS WORSE THAN "UNDERIVED"

The old Term 2 reference was "12.33 GB free memory", taken from the WO-044 capture's preflight.
**That figure is not free memory.** `LoadRecord.capture()` records

    memory_gb = psutil.virtual_memory().used / (1024 ** 3)

— host memory **USED**. So WO-054, WO-055 and WO-056 each compared today's *available* memory
against the WO-044 capture's *used* memory. Two different quantities.

Corrected on this host (total 15.715 GiB):

    WO-044 capture : 12.334 GiB USED  ->  ~3.381 GiB FREE
    a later reading:  4.573 GiB FREE

**The capture that banked 12.9 hours ran with LESS free memory than the readings later called RED.**
The gate was demanding roughly 3.6x more headroom than its own reference run ever had.

That is the shape D57 names: a number that travelled between documents on the strength of being
repeated, and which nobody re-derived. The replacement below is tied to a MECHANISM instead.
═══════════════════════════════════════════════════════════════════════════════════════════════

THE GATE, in two parts. Both must pass.

  A. PAGING **FLOW** AT IDLE, SUSTAINED AT ~ZERO — the gate (WO-058 §2.3, D58 ruling 3).

     ⚠ THIS REPLACED A GATE ON **STOCK**, AND THE DISTINCTION IS THE WHOLE POINT.
     WO-057 gated on swap BYTES IN USE. That is a STOCK: bytes parked in the pagefile, which
     Windows retains proactively even on a host that is not paging at all. D46's chain does not
     run through parked bytes; it runs through PAGE FAULTS SERVICED FROM DISK — an ongoing RATE.
     A host can sit at 500 MiB of pagefile stock and read zero pages per second, which is exactly
     this host, and gating on the stock made a reachable capture unreachable for a second time.

     STOCK is still reported, as CONTEXT. It never gates.

  B. FREE MEMORY >= THE CAPTURE'S OWN DERIVED FOOTPRINT, WITH DECLARED MARGIN.
     Derived below from measurement plus the declared retention caps — not from a remembered
     figure. Unchanged by WO-058; it clears on this host by ~10x.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

# ── §2.1 THE FOOTPRINT, DERIVED ───────────────────────────────────────────────────────────────
#
# MEASURED on this host, 2026-08-08, by running the real capture runner over a fixture socket
# (no network) and sampling this process's RSS — `psutil.Process().memory_info().rss`:
#
#     bare interpreter                         27.39 MiB
#     + every capture import loaded            35.68 MiB
#     + a running capture, 3,000 frames        71.92 MiB   <- process baseline
#
# At 3,000 frames the raw-text retention buffer held roughly 3,000 x ~175 B ~= 0.5 MiB, i.e. it was
# effectively EMPTY. So 71.92 MiB is the baseline BEFORE the buffer fills.
#
#     process baseline                         71.92 MiB   (measured)
#   + retention buffer at its declared cap     64.00 MiB   (MAX_RETAINED_RAW_BYTES)
#   ------------------------------------------------------
#   = steady-state ceiling                    135.92 MiB
#
#   + segment-close transient                 ~18.00 MiB
#     A closed segment is ~17.26 MiB raw (measured mean, WO-054) and gzip holds source and
#     destination at once.
#   ------------------------------------------------------
#   = transient peak                          ~154 MiB
#
#   x2 allowance for allocator fragmentation over a multi-week run
#   ------------------------------------------------------
#   = DERIVED REQUIREMENT                     ~308 MiB
#
# DECLARED FLOOR: 512 MiB — the next power of two above the derived 308 MiB. Rounded UP, and
# stated as a declared floor rather than reported as "308 MiB", because a derivation resting on a
# fragmentation allowance does not deserve three significant figures.
#
# ⚠ THE TRADE CHANNEL ADDS NOTHING TO THIS CEILING, BY CONSTRUCTION — and that is worth stating
# because WO-057 §2.1 asks for its increment. The retention buffer is BYTE-capped
# (precedence FLOOR > BYTE CAP > COUNT CAP), so a higher message rate does not raise the memory
# ceiling; it only makes the cap bind sooner in wall-clock time. The trade rate therefore does not
# enter this figure at all.
#
# The trade rate REMAINS AN UNMEASURED ASSUMPTION (1 trade per 8 book frames, WO-054) because no
# socket has opened. It is NOT promoted here, and it is not needed here — but it IS load-bearing
# for abort condition 4 (trim frequency), where it is carried explicitly as an assumption.
CAPTURE_PROCESS_BASELINE_MIB = 71.92        # measured, fixture run, 2026-08-08
RETENTION_BYTE_CAP_MIB = 64.0               # KrakenV2BookAdapter.MAX_RETAINED_RAW_BYTES
SEGMENT_CLOSE_TRANSIENT_MIB = 18.0          # ~17.26 MiB segment + gzip destination
FRAGMENTATION_ALLOWANCE = 2.0
DERIVED_REQUIREMENT_MIB = (
    (CAPTURE_PROCESS_BASELINE_MIB + RETENTION_BYTE_CAP_MIB + SEGMENT_CLOSE_TRANSIENT_MIB)
    * FRAGMENTATION_ALLOWANCE
)
MIN_FREE_MEMORY_MIB = 512.0                 # declared floor, above the derived requirement

# ── WO-058 §2.3: WHICH COUNTER, AND WHY ──────────────────────────────────────────────────────
#
# ENUMERATED on this host rather than assumed (0.11). `psutil.swap_memory().sin/sout` are
# documented-unsupported on Windows and read 0 always — they cannot be the flow source. The
# Windows performance counters were sampled directly:
#
#     \Memory\Pages/sec           0.00        <- HARD faults: pages read from / written to DISK
#     \Memory\Pages Input/sec     0.00        <- the read half; the D46 stall specifically
#     \Memory\Pages Output/sec    0.00
#     \Memory\Page Faults/sec     4,165-5,410 <- MOSTLY SOFT faults, satisfied from RAM
#
# THE GATE USES `\Memory\Pages/sec`. It counts only faults that required disk I/O, in either
# direction, which is precisely D46's mechanism. Both directions are included rather than reads
# alone: page-OUT is the OS trimming working sets, which is itself evidence of memory pressure
# even though it does not stall the loop directly. Including it makes the gate conservative in the
# safe direction.
#
# `Page Faults/sec` IS DELIBERATELY NOT USED, and this matters: it counts SOFT faults too — a page
# already resident, a standby-list hit, the first touch of a committed page. Those cost
# microseconds and never reach the disk. It reads thousands per second on any idle Windows box, so
# a gate built on it would be permanently RED. That is the same failure this WO exists to end:
# a threshold no healthy host could ever satisfy.
PAGING_FLOW_COUNTER = r"\Memory\Pages/sec"

# ── "~ZERO", DECLARED NUMERICALLY (§2.3 / 0.15) ──────────────────────────────────────────────
#
# Two conditions, both of which must hold across the window:
#     every sample  <= 10.0 pages/sec
#     the mean      <=  1.0 pages/sec
#
# DERIVATION. A 4 KiB page read from this host's SSD costs on the order of 50-100 us. At 10
# pages/sec that is ~1 ms of disk wait per second — 0.1% of wall time — against a capture whose
# frame budget is ~30 ms at the observed 24-32 frames/s. To threaten the multi-second
# HEARTBEAT_ABSENCE timeout that D46 describes, paging would have to stall the loop for SECONDS,
# which needs tens of thousands of pages/sec. The per-sample bound therefore sits roughly three
# orders of magnitude below the level that could plausibly matter.
#
# The mean bound catches the other shape: a steady low trickle that never trips the per-sample
# bound but indicates the host is paging continuously.
#
# ROUNDED, AND SAID SO (0.15): 10.0 and 1.0 are round numbers chosen ABOVE the derivation, not
# fitted to it. A bound resting on an order-of-magnitude argument about disk latency does not
# deserve more precision than that, and pretending otherwise would be the false-precision habit
# this project keeps correcting.
MAX_PAGING_FLOW_PER_SAMPLE = 10.0
MAX_PAGING_FLOW_MEAN = 1.0


# ── §2.2 "SUSTAINED" — the observation window, declared ───────────────────────────────────────
#
# A single sample is not evidence about swap. Windows commits and reclaims pages LAZILY, so an
# instantaneous read can land in a quiet interval between page-outs and report zero on a host that
# is paging steadily.
#
# WINDOW: 60 seconds. SAMPLES: every 2 seconds, 30 in total. EVERY sample must read zero swap in
# use — not the mean, not the median. One non-zero sample fails the gate, because the question is
# whether the host pages AT ALL while idle.
#
# WHY 60s / 2s: most Windows scheduled tasks and background service ticks run on intervals of 30 s
# or less, so a 60-second window contains at least one full period of the commonest sources of
# idle churn. 2-second sampling gives 30 observations, enough that a single transient does not
# dominate, while keeping the check short enough to run as a preflight step rather than a chore.
#
# FALSIFIER FOR THE WINDOW ITSELF (0.12): if two consecutive 60-second windows on the same
# otherwise-idle host DISAGREE — one all-zero, the next not — then 60 s is too short to
# characterise this host and the window must be lengthened. That is a checkable claim, and the
# right response is to re-derive the window, not to re-run until a green one appears.
SWAP_OBSERVATION_WINDOW_SECONDS = 60.0
SWAP_SAMPLE_INTERVAL_SECONDS = 2.0
SWAP_SAMPLE_COUNT = int(SWAP_OBSERVATION_WINDOW_SECONDS / SWAP_SAMPLE_INTERVAL_SECONDS)


@dataclass
class GateVerdict:
    """The gate's answer, with the evidence that produced it.

    `flow_samples` GATES. `stock_mib` is CONTEXT and never gates — see the module docstring.
    """

    green: bool
    flow_green: bool
    memory_green: bool
    free_mib: float
    flow_samples: List[float] = field(default_factory=list)
    stock_mib: float = 0.0
    detail: str = ""
    flow_available: bool = True

    @property
    def max_flow(self) -> float:
        return max(self.flow_samples) if self.flow_samples else 0.0

    @property
    def mean_flow(self) -> float:
        return sum(self.flow_samples) / len(self.flow_samples) if self.flow_samples else 0.0

    def to_dict(self) -> dict:
        return {
            "green": self.green,
            "flow_green": self.flow_green,
            "memory_green": self.memory_green,
            "gated_on": "paging FLOW (pages/sec requiring disk I/O)",
            "counter": PAGING_FLOW_COUNTER,
            "max_flow_pages_per_sec": round(self.max_flow, 2),
            "mean_flow_pages_per_sec": round(self.mean_flow, 3),
            "max_flow_allowed": MAX_PAGING_FLOW_PER_SAMPLE,
            "mean_flow_allowed": MAX_PAGING_FLOW_MEAN,
            "flow_samples": len(self.flow_samples),
            "flow_available": self.flow_available,
            # CONTEXT ONLY. Reported so a reader sees the whole picture, never consulted by the
            # verdict — gating on it is what WO-057 did and what D58 ruling 3 reversed.
            "stock_swap_in_use_mib_CONTEXT_ONLY": round(self.stock_mib, 2),
            "free_mib": round(self.free_mib, 2),
            "min_free_required_mib": MIN_FREE_MEMORY_MIB,
            "derived_requirement_mib": round(DERIVED_REQUIREMENT_MIB, 2),
            "observation_window_seconds": SWAP_OBSERVATION_WINDOW_SECONDS,
            "detail": self.detail,
            "falsifier": (
                "GREEN would be falsified by any single flow sample above "
                f"{MAX_PAGING_FLOW_PER_SAMPLE} pages/sec, by a mean above "
                f"{MAX_PAGING_FLOW_MEAN}, by free memory below the declared floor, or by the flow "
                "counter being unreadable (which fails CLOSED — a gate that cannot measure must "
                "not pass). Swap STOCK cannot falsify it: a host may hold pagefile bytes without "
                "paging. The WINDOW's own adequacy would be falsified by two consecutive windows "
                "on the same idle host disagreeing — re-derive it, do not re-run until green."
            ),
        }


def evaluate(sampler: Optional[Callable] = None, sample_count: int = SWAP_SAMPLE_COUNT,
             sleep_fn: Optional[Callable] = None) -> GateVerdict:
    """Evaluate the Term 2 gate.

    Args:
        sampler: returns (free_bytes, stock_swap_bytes, flow_pages_per_sec). `flow` may be None,
            meaning the counter could not be read — which FAILS CLOSED.
        sample_count: number of samples. Injected so a test need not wait 60 s.
        sleep_fn: injected sleep, so the observation window is driveable.

    Never raises on a RED — a gate that crashes cannot be reported.
    """
    use_window = sampler is None          # the real path; injected samplers drive per-sample
    if sampler is None:
        sampler = _default_sampler
    if sleep_fn is None:
        import time as _time
        sleep_fn = _time.sleep

    if use_window:
        # Take the WHOLE window in one subprocess (see read_paging_flow_window's docstring), then
        # read free/stock once at the end. Free memory is a level, not a rate; one reading of it
        # after the window is the honest sample to pair with the window's flow.
        import psutil

        window = read_paging_flow_window(sample_count)
        free_bytes = psutil.virtual_memory().available
        stock_bytes = psutil.swap_memory().used
        return _verdict(free_bytes, stock_bytes, window if window is not None else [],
                        flow_available=window is not None)

    flow_samples: List[float] = []
    free_bytes = 0
    stock_bytes = 0
    flow_available = True
    for i in range(max(1, sample_count)):
        free_bytes, stock_bytes, flow = sampler()
        if flow is None:
            flow_available = False
        else:
            flow_samples.append(float(flow))
        if i < sample_count - 1:
            sleep_fn(SWAP_SAMPLE_INTERVAL_SECONDS)

    return _verdict(free_bytes, stock_bytes, flow_samples, flow_available)


def _verdict(free_bytes, stock_bytes, flow_samples, flow_available) -> GateVerdict:
    """Build the verdict from measured evidence. Shared by the real and injected paths, so both
    are judged by exactly the same rules."""
    free_mib = free_bytes / (1024 ** 2)
    stock_mib = stock_bytes / (1024 ** 2)

    if not flow_available or not flow_samples:
        # FAIL CLOSED. A gate that cannot measure must not pass — that is the whole lesson of the
        # figures this gate replaced.
        flow_green = False
    else:
        mean_flow = sum(flow_samples) / len(flow_samples)
        flow_green = (max(flow_samples) <= MAX_PAGING_FLOW_PER_SAMPLE
                      and mean_flow <= MAX_PAGING_FLOW_MEAN)

    memory_green = free_mib >= MIN_FREE_MEMORY_MIB

    if flow_green and memory_green:
        detail = (f"paging flow ~zero across {len(flow_samples)} samples "
                  f"(max {max(flow_samples):.2f}, mean {sum(flow_samples)/len(flow_samples):.3f} "
                  f"pages/sec); {free_mib:.0f} MiB free >= {MIN_FREE_MEMORY_MIB:.0f} MiB floor. "
                  f"Swap stock {stock_mib:.0f} MiB is CONTEXT and does not gate.")
    else:
        parts = []
        if not flow_available or not flow_samples:
            parts.append(
                f"paging-flow counter {PAGING_FLOW_COUNTER} could not be read — FAILING CLOSED, "
                f"because a gate that cannot measure must not pass")
        elif not flow_green:
            parts.append(
                f"host IS PAGING at idle (max {max(flow_samples):.2f}, mean "
                f"{sum(flow_samples)/len(flow_samples):.3f} pages/sec over {len(flow_samples)} "
                f"samples) — D46's chain runs through exactly this")
        if not memory_green:
            parts.append(
                f"free memory {free_mib:.0f} MiB < {MIN_FREE_MEMORY_MIB:.0f} MiB declared floor "
                f"(derived requirement {DERIVED_REQUIREMENT_MIB:.0f} MiB)")
        detail = "; ".join(parts)

    return GateVerdict(
        green=flow_green and memory_green,
        flow_green=flow_green,
        memory_green=memory_green,
        free_mib=free_mib,
        flow_samples=flow_samples,
        stock_mib=stock_mib,
        detail=detail,
        flow_available=flow_available,
    )


def read_paging_flow() -> Optional[float]:
    r"""One reading of `\Memory\Pages/sec`, or None if it cannot be read.

    Windows-specific by necessity: `psutil.swap_memory().sin/sout` are documented-unsupported on
    Windows and read 0 unconditionally, so they cannot serve as the flow source. The performance
    counter is read through PowerShell's `Get-Counter`, which is present on every supported
    Windows install and needs no extra dependency.

    Returns None rather than 0.0 on failure — the difference matters: 0.0 would be a claim that the
    host is not paging, and None is the absence of a claim. The caller fails CLOSED on None.
    """
    import subprocess

    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             f"(Get-Counter -Counter '{PAGING_FLOW_COUNTER}' -SampleInterval 1 -MaxSamples 1)"
             f".CounterSamples[0].CookedValue"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        return float(proc.stdout.strip())
    except (TypeError, ValueError):
        return None


def read_paging_flow_window(sample_count: int = SWAP_SAMPLE_COUNT,
                            interval_seconds: float = SWAP_SAMPLE_INTERVAL_SECONDS):
    """The whole window in ONE `Get-Counter` call. Returns a list of readings, or None on failure.

    ⚠ WHY ONE PROCESS AND NOT `sample_count` OF THEM — AN OBSERVER-EFFECT DEFECT, MEASURED.
    The first implementation called `read_paging_flow()` once per sample, i.e. spawned 30
    PowerShell processes across the window. Launching PowerShell loads the executable and its .NET
    assemblies from disk, which is itself a burst of hard page faults. The instrument was
    measuring its own cost: over the same window, 30 processes reported a mean of 859 pages/sec
    where one process reported 277.

    Both readings exceeded the bound here, so the verdict did not turn on it — but a measurement
    that inflates by 3x is not one to keep, and on a quieter host it would be the difference
    between GREEN and RED.
    """
    import subprocess

    script = (
        f"(Get-Counter -Counter '{PAGING_FLOW_COUNTER}' "
        f"-SampleInterval {int(max(1, interval_seconds))} -MaxSamples {int(sample_count)})"
        f" | ForEach-Object {{ $_.CounterSamples[0].CookedValue }}"
    )
    timeout = interval_seconds * sample_count + 60
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    values = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            values.append(float(line))
        except ValueError:
            return None
    return values or None


def _default_sampler():
    import psutil
    return (psutil.virtual_memory().available,
            psutil.swap_memory().used,
            read_paging_flow())
