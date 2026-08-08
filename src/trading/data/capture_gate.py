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

  A. ZERO SWAP IN USE AT IDLE, SUSTAINED.
     This is the primary criterion because it is tied directly to D46's causal chain:
     memory pressure -> swap -> event-loop starvation -> HEARTBEAT_ABSENCE, i.e. a host problem
     recorded as a venue disconnect. Swap in use at idle means the first link is not a risk but a
     present condition. Unlike a free-memory threshold, this needs no reference number: the
     mechanism says zero.

  B. FREE MEMORY >= THE CAPTURE'S OWN DERIVED FOOTPRINT, WITH DECLARED MARGIN.
     Derived below from measurement plus the declared retention caps — not from a remembered
     figure.
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
    """The gate's answer, with the evidence that produced it."""

    green: bool
    swap_green: bool
    memory_green: bool
    free_mib: float
    swap_samples_mib: List[float] = field(default_factory=list)
    detail: str = ""

    @property
    def max_swap_mib(self) -> float:
        return max(self.swap_samples_mib) if self.swap_samples_mib else 0.0

    def to_dict(self) -> dict:
        return {
            "green": self.green,
            "swap_green": self.swap_green,
            "memory_green": self.memory_green,
            "free_mib": round(self.free_mib, 2),
            "min_free_required_mib": MIN_FREE_MEMORY_MIB,
            "derived_requirement_mib": round(DERIVED_REQUIREMENT_MIB, 2),
            "max_swap_in_use_mib": round(self.max_swap_mib, 2),
            "swap_samples": len(self.swap_samples_mib),
            "observation_window_seconds": SWAP_OBSERVATION_WINDOW_SECONDS,
            "detail": self.detail,
            "falsifier": (
                "GREEN would be falsified by any single sample reading non-zero swap in use, or "
                "by free memory below the declared floor. The WINDOW's own adequacy would be "
                "falsified by two consecutive windows on the same idle host disagreeing."
            ),
        }


def evaluate(sampler: Optional[Callable] = None, sample_count: int = SWAP_SAMPLE_COUNT,
             sleep_fn: Optional[Callable] = None) -> GateVerdict:
    """Evaluate the Term 2 gate.

    Args:
        sampler: returns (free_bytes, swap_used_bytes). Injected in tests; defaults to psutil.
        sample_count: number of swap samples. Injected so a test need not wait 60 s.
        sleep_fn: injected sleep, so the observation window is driveable.

    Returns a `GateVerdict`. Never raises on a RED — a gate that crashes cannot be reported.
    """
    if sampler is None:
        sampler = _psutil_sampler
    if sleep_fn is None:
        import time as _time
        sleep_fn = _time.sleep

    swap_samples = []
    free_bytes = 0
    for i in range(max(1, sample_count)):
        free_bytes, swap_used = sampler()
        swap_samples.append(swap_used / (1024 ** 2))
        if i < sample_count - 1:
            sleep_fn(SWAP_SAMPLE_INTERVAL_SECONDS)

    free_mib = free_bytes / (1024 ** 2)
    # EVERY sample must be zero — not the mean. The question is whether the host pages at all.
    swap_green = all(s == 0 for s in swap_samples)
    memory_green = free_mib >= MIN_FREE_MEMORY_MIB

    if swap_green and memory_green:
        detail = (f"zero swap across {len(swap_samples)} samples; "
                  f"{free_mib:.0f} MiB free >= {MIN_FREE_MEMORY_MIB:.0f} MiB floor")
    else:
        parts = []
        if not swap_green:
            parts.append(
                f"swap IN USE at idle (max {max(swap_samples):.1f} MiB over "
                f"{len(swap_samples)} samples) — D46's first link is present, not hypothetical")
        if not memory_green:
            parts.append(
                f"free memory {free_mib:.0f} MiB < {MIN_FREE_MEMORY_MIB:.0f} MiB declared floor "
                f"(derived requirement {DERIVED_REQUIREMENT_MIB:.0f} MiB)")
        detail = "; ".join(parts)

    return GateVerdict(
        green=swap_green and memory_green,
        swap_green=swap_green,
        memory_green=memory_green,
        free_mib=free_mib,
        swap_samples_mib=swap_samples,
        detail=detail,
    )


def _psutil_sampler():
    import psutil
    return psutil.virtual_memory().available, psutil.swap_memory().used
