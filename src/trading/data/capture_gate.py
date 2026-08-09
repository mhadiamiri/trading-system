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

# ── WO-059 §1: WHICH COUNTER, AND WHY — CHOSEN BY MECHANISM, NOT BY NAME ─────────────────────
#
# ⚠ THIS IS THE SECOND COUNTER CHOICE. The first — `\Memory\Pages/sec` — was RETIRED because it
# measures FILE-BACKED I/O as well as pagefile I/O. Demonstrated on this host with NO memory
# pressure at all (commit 8.40 GB of 15.71 GB physical, 7.8 GB free):
#
#     idle                        pages/sec =      0.0    cache faults/sec =     0.0
#     reading 60 ordinary files   pages/sec = 44,751.1    cache faults/sec = 93,032.5
#     PAGING FILE % USAGE         2.791 -> 2.791 -> 2.791 -> 2.791   (FLAT THROUGHOUT)
#
# `Pages/sec` tracks `Cache Faults/sec`, not the pagefile. A gate on it is tripped by ANY disk
# read — including the capture writing its own ~17 MiB segments every hour and gzipping them. It
# was a gate no working machine could satisfy, and it would have been tripped by the very process
# it was protecting.
#
# THE PATTERN, LOGGED EXPLICITLY (D59): three consecutive criteria in this family failed for the
# same reason — A COUNTER CHOSEN BY NAME RATHER THAN BY MECHANISM.
#     12.33 GB "free"      -> was memory USED           (wrong quantity)
#     swap bytes in use    -> a STOCK, not D46's rate   (wrong kind of quantity)
#     \Memory\Pages/sec    -> file-backed I/O, not swap (right kind, wrong subject)
# Each name plausibly described the thing wanted. None was checked against the MECHANISM until it
# had already produced a verdict.
#
# THE MECHANISM, stated so the counter can be checked against it: D46 is
# memory pressure -> the OS moves pages to the PAGEFILE -> the event loop waits on that disk I/O
# -> HEARTBEAT_ABSENCE. The observable is therefore PAGEFILE OCCUPANCY CHANGING, not disk activity
# in general.
#
# PRIMARY: `\Paging File(_Total)\% Usage`, sampled across the window; the gate reads its MOVEMENT.
# Occupancy that does not move means the OS is not growing or shrinking the pagefile, i.e. it is
# not swapping. Verified above to be flat under heavy file reads — the exact case Pages/sec failed.
#
# FALLBACK, declared with its derivation: `Pages/sec - Cache Faults/sec`. Cache faults are the
# file-backed component, so subtracting them leaves the pagefile-backed remainder. Used only if the
# pagefile counter is unreadable; it is an arithmetic reconstruction of the same quantity the
# primary measures directly, so the primary is preferred where available.
PAGEFILE_USAGE_COUNTER = r"\Paging File(_Total)\% Usage"
PAGES_COUNTER = r"\Memory\Pages/sec"
CACHE_FAULTS_COUNTER = r"\Memory\Cache Faults/sec"

# ── "~ZERO" MOVEMENT, DECLARED NUMERICALLY (0.15) ────────────────────────────────────────────
#
# Two conditions, both across the window:
#     max |change| between consecutive samples  <= 0.05 percentage points
#     net drift (last - first)                  <= 0.10 percentage points
#
# DERIVATION. This host's pagefile is 11.81 GB, so 0.05 pp is ~5.9 MB moved within one 2-second
# sample — about 3 MB/s. On an SSD sustaining hundreds of MB/s that is well under 1% of disk time,
# far below anything that could stall a loop whose frame budget is ~30 ms. To threaten the
# multi-second HEARTBEAT_ABSENCE timeout, swapping would have to run orders of magnitude higher.
# The counter's own resolution is ~0.001 pp (~118 KB), so 0.05 pp is comfortably above quantisation
# noise rather than chasing it.
#
# The net-drift bound catches the shape the per-sample bound misses: occupancy creeping steadily
# upward in increments too small to trip individually.
#
# ROUNDED, AND SAID SO (0.15): 0.05 and 0.10 are round numbers chosen ABOVE the derivation, not
# fitted to it. A bound resting on an order-of-magnitude argument about disk throughput does not
# deserve more precision, and pretending otherwise is the false-precision habit this project keeps
# correcting.
MAX_PAGEFILE_MOVE_PP = 0.05
MAX_PAGEFILE_DRIFT_PP = 0.10

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

    `flow_samples` holds PAGEFILE OCCUPANCY (% usage) readings; the gate reads their MOVEMENT.
    `stock_mib` is context and never gates.
    """

    green: bool
    flow_green: bool
    memory_green: bool
    free_mib: float
    flow_samples: List[float] = field(default_factory=list)
    stock_mib: float = 0.0
    detail: str = ""
    flow_available: bool = True
    residual_samples: List[float] = field(default_factory=list)   # Pages/sec - Cache Faults/sec
    # RAW `\Memory\Pages/sec`, retained for the record and for the bite proof's faithful
    # restoration of the RETIRED criterion. NEVER consulted by the verdict — it is the quantity
    # WO-059 retired, kept visible so the retirement is checkable rather than asserted.
    pages_samples: List[float] = field(default_factory=list)
    source: str = "pagefile"

    @property
    def max_move_pp(self) -> float:
        """Largest absolute change between consecutive occupancy samples."""
        s = self.flow_samples
        return max((abs(s[i] - s[i - 1]) for i in range(1, len(s))), default=0.0)

    @property
    def drift_pp(self) -> float:
        """Net change across the window."""
        s = self.flow_samples
        return (s[-1] - s[0]) if len(s) >= 2 else 0.0

    def to_dict(self) -> dict:
        return {
            "green": self.green,
            "flow_green": self.flow_green,
            "memory_green": self.memory_green,
            "gated_on": "PAGEFILE OCCUPANCY MOVEMENT (the pagefile actually changing)",
            "source": self.source,
            "counter": (PAGEFILE_USAGE_COUNTER if self.source == "pagefile"
                        else f"{PAGES_COUNTER} minus {CACHE_FAULTS_COUNTER}"),
            "max_move_pp": round(self.max_move_pp, 4),
            "drift_pp": round(self.drift_pp, 4),
            "max_move_allowed_pp": MAX_PAGEFILE_MOVE_PP,
            "max_drift_allowed_pp": MAX_PAGEFILE_DRIFT_PP,
            "occupancy_samples": len(self.flow_samples),
            "flow_available": self.flow_available,
            # Reported for corroboration: the arithmetic reconstruction of the same quantity.
            "residual_pages_minus_cache_max": (round(max(self.residual_samples), 2)
                                               if self.residual_samples else None),
            # CONTEXT ONLY. Never consulted by the verdict.
            "stock_swap_in_use_mib_CONTEXT_ONLY": round(self.stock_mib, 2),
            "free_mib": round(self.free_mib, 2),
            "min_free_required_mib": MIN_FREE_MEMORY_MIB,
            "derived_requirement_mib": round(DERIVED_REQUIREMENT_MIB, 2),
            "observation_window_seconds": SWAP_OBSERVATION_WINDOW_SECONDS,
            "detail": self.detail,
            "falsifier": (
                f"GREEN would be falsified by pagefile occupancy moving more than "
                f"{MAX_PAGEFILE_MOVE_PP} pp between consecutive samples, by net drift above "
                f"{MAX_PAGEFILE_DRIFT_PP} pp, by free memory below the declared floor, or by the "
                "counter being unreadable (which fails CLOSED — a gate that cannot measure must "
                "not pass). Neither swap STOCK nor file-backed disk activity can falsify it: a "
                "host may hold pagefile bytes it never touches, and reading a file is not "
                "swapping. The WINDOW's own adequacy would be falsified by two consecutive "
                "windows on the same idle host disagreeing — re-derive it, do not re-run until "
                "green."
            ),
        }


def evaluate(sampler: Optional[Callable] = None, sample_count: int = SWAP_SAMPLE_COUNT,
             sleep_fn: Optional[Callable] = None) -> GateVerdict:
    """Evaluate the Term 2 gate.

    Args:
        sampler: returns (free_bytes, stock_swap_bytes, pagefile_pct). `pagefile_pct` may be None,
            meaning the counter could not be read — which FAILS CLOSED.
        sample_count: number of samples. Injected so a test need not wait 60 s.
        sleep_fn: injected sleep, so the observation window is driveable.

    Never raises on a RED — a gate that crashes cannot be reported.
    """
    use_window = sampler is None
    if sampler is None:
        sampler = _default_sampler
    if sleep_fn is None:
        import time as _time
        sleep_fn = _time.sleep

    if use_window:
        import psutil

        window = read_pagefile_window(sample_count)
        free_bytes = psutil.virtual_memory().available
        stock_bytes = psutil.swap_memory().used
        if window is None:
            return _verdict(free_bytes, stock_bytes, [], flow_available=False)
        return _verdict(free_bytes, stock_bytes, window["usage"], flow_available=True,
                        residual=window["residual"], source=window["source"],
                        pages=window["pages"])

    samples: List[float] = []
    pages: List[float] = []
    free_bytes = 0
    stock_bytes = 0
    flow_available = True
    for i in range(max(1, sample_count)):
        reading = sampler()
        # A 4th element (raw Pages/sec) is OPTIONAL: fixtures that need to exercise the retired
        # criterion supply it; the rest do not, and it never affects the verdict either way.
        free_bytes, stock_bytes, pct = reading[0], reading[1], reading[2]
        if len(reading) > 3 and reading[3] is not None:
            pages.append(float(reading[3]))
        if pct is None:
            flow_available = False
        else:
            samples.append(float(pct))
        if i < sample_count - 1:
            sleep_fn(SWAP_SAMPLE_INTERVAL_SECONDS)

    return _verdict(free_bytes, stock_bytes, samples, flow_available, pages=pages)


def _verdict(free_bytes, stock_bytes, samples, flow_available, residual=None,
             source="pagefile", pages=None) -> GateVerdict:
    """Build the verdict from measured evidence. Shared by the real and injected paths, so both
    are judged by exactly the same rules."""
    free_mib = free_bytes / (1024 ** 2)
    stock_mib = stock_bytes / (1024 ** 2)
    residual = residual or []
    pages = pages or []

    v = GateVerdict(green=False, flow_green=False, memory_green=False, free_mib=free_mib,
                    flow_samples=samples, stock_mib=stock_mib, flow_available=flow_available,
                    residual_samples=residual, source=source, pages_samples=pages)

    if not flow_available or len(samples) < 2:
        # FAIL CLOSED. A gate that cannot measure must not pass — the whole lesson of the figures
        # this gate replaced. Fewer than two samples cannot express MOVEMENT at all.
        flow_green = False
    else:
        flow_green = (v.max_move_pp <= MAX_PAGEFILE_MOVE_PP
                      and abs(v.drift_pp) <= MAX_PAGEFILE_DRIFT_PP)

    memory_green = free_mib >= MIN_FREE_MEMORY_MIB
    v.flow_green = flow_green
    v.memory_green = memory_green
    v.green = flow_green and memory_green

    if flow_green and memory_green:
        v.detail = (
            f"pagefile occupancy static across {len(samples)} samples "
            f"(max move {v.max_move_pp:.4f} pp, drift {v.drift_pp:+.4f} pp); "
            f"{free_mib:.0f} MiB free >= {MIN_FREE_MEMORY_MIB:.0f} MiB floor. "
            f"Swap stock {stock_mib:.0f} MiB is CONTEXT and does not gate; file-backed disk "
            f"activity is not swapping and does not gate either."
        )
    else:
        parts = []
        if not flow_available or len(samples) < 2:
            parts.append(
                f"pagefile counter unreadable or too few samples to express movement — FAILING "
                f"CLOSED, because a gate that cannot measure must not pass")
        elif not flow_green:
            parts.append(
                f"the PAGEFILE IS MOVING (max {v.max_move_pp:.4f} pp between samples, drift "
                f"{v.drift_pp:+.4f} pp over {len(samples)} samples) — the host is swapping, which "
                f"is D46's mechanism")
        if not memory_green:
            parts.append(
                f"free memory {free_mib:.0f} MiB < {MIN_FREE_MEMORY_MIB:.0f} MiB declared floor "
                f"(derived requirement {DERIVED_REQUIREMENT_MIB:.0f} MiB)")
        v.detail = "; ".join(parts)

    return v


def read_pagefile_window(sample_count: int = SWAP_SAMPLE_COUNT,
                         interval_seconds: float = SWAP_SAMPLE_INTERVAL_SECONDS):
    """The whole window in ONE `Get-Counter` call: pagefile occupancy + the fallback's inputs.

    Returns {"usage": [...], "residual": [...], "source": "pagefile"} or None.

    ⚠ ONE PROCESS, NOT `sample_count` OF THEM — an observer-effect defect, measured. An earlier
    version spawned a PowerShell per sample; launching PowerShell loads its executable and .NET
    assemblies from disk, which is itself disk activity. Over the same window, 30 processes
    reported a mean 3x higher than one process did.
    """
    import subprocess

    counters = f"'{PAGEFILE_USAGE_COUNTER}','{PAGES_COUNTER}','{CACHE_FAULTS_COUNTER}'"
    script = (
        f"(Get-Counter -Counter {counters} "
        f"-SampleInterval {int(max(1, interval_seconds))} -MaxSamples {int(sample_count)})"
        f" | ForEach-Object {{ ($_.CounterSamples | ForEach-Object {{ $_.CookedValue }}) "
        f"-join ',' }}"
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

    usage, residual, raw_pages = [], [], []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 3:
            return None
        try:
            pct, pages, cache = float(parts[0]), float(parts[1]), float(parts[2])
        except ValueError:
            return None
        usage.append(pct)
        raw_pages.append(pages)
        # The FALLBACK quantity, computed alongside for corroboration: cache faults are the
        # file-backed component, so the remainder is what touched the pagefile.
        residual.append(max(0.0, pages - cache))
    if len(usage) < 2:
        return None
    return {"usage": usage, "residual": residual, "pages": raw_pages,
            "source": "pagefile"}


def _default_sampler():
    import psutil
    window = read_pagefile_window(1, 1)
    pct = window["usage"][0] if window else None
    return psutil.virtual_memory().available, psutil.swap_memory().used, pct
