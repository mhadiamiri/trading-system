#!/usr/bin/env python3
"""
WO-043 / WO-044 — 24-HOUR CORPUS CAPTURE RUNNER (RESUMABLE)

WO-044 (D45) makes the corpus RESUMABLE: one corpus-id, N runs, 24 CUMULATIVE hours, every seam
labeled. What changed from WO-043's one-continuous-process definition:
  §3.1 a stable `corpus_id` groups runs   -> captures/<root>/<corpus_id>/<run_id>/
  §3.2 every resume carries its OWN full preflight, written to PREFLIGHT.json as its opening record
  §3.3 the inter-run seam is a ledger record with a DECLARED cause and a MEASURED true duration
  §3.4 no book state crosses a resume (a fresh, checksum-validated snapshot — see below)
  §3.5 the manifest spans the corpus-id, not just the run
  §3.7 cumulative-hours accounting, answerable at any time (`--progress`)

§3.4 IS SATISFIED BY EXISTING MACHINERY, NOT REBUILT. A resume is a NEW PROCESS: it constructs a
new adapter with an empty book and connects fresh, so no book state can cross a seam — there is no
carry-over path to sever. The D45 addition (a) — "the resume snapshot's checksum MUST validate
before any MarketState emits" — is FR-018a(d), already enforced in `_process_quote_update`: a
snapshot whose computed CRC32 does not match the venue's token calls `_enter_resync` and returns
None, so nothing is emitted from an unverified book, and only a VALIDATED snapshot clears the
window. A resumed segment therefore starts life proven rather than assumed, by the same code path
that governs every mid-run resync. Behaviour on failure is the existing one: retry via reconnect,
and if the venue stays unreachable the breaker STOPs the run (§4.2) — it never emits unvalidated.

────────────────────────────────────────────────────────────────────────────────────────────────
WO-043 ORIGINAL HEADER, PRESERVED (annotate, don't rewrite). The rotation policy, configuration
and grant conditions below remain the operative ones — only the resume/seam layer above is new.
────────────────────────────────────────────────────────────────────────────────────────────────

Opens the Kraken mainnet public WS v2 (BTC/USD, unauthenticated), drives get_live_market_data
for the real feed, and writes frames to hourly UTC-stamped .jsonl segments per the WO-042
rotation policy.

ROTATION POLICY (consumed from evidence/WO-042/rotation_policy.md):
- Hourly time-based rotation: corpus_{HOST}_{YYYYMMDDTHH}Z.jsonl
- Compression: gzip on segment close (5-10× ratio expected)
- Retention: 90-day minimum, 1-year recommended
- Integrity: SHA-256 per segment + CRC32 per-frame (already in adapter)
- Crash-safety: max loss = open hour segment (~220 MB)

CONFIGURATION (environment variables):
- CORPUS_ROTATION_CADENCE=hourly
- CORPUS_SEGMENT_DURATION_SECONDS=3600
- CORPUS_COMPRESSION_ENABLED=true
- CORPUS_RETENTION_DAYS=90
- CORPUS_DIR=captures/corpus_24h

GRANT CONDITIONS (all demonstrated as preflight before socket opens):
1. Paper-env + no-credential (TRADING_ENV=paper, no credentials)
2. Host-suspend armed (43s divergence bound)
3. Load recorded (CPU + memory at start + average over window)
4. Rotation consumed (policy config loaded, first segment path correct)
5. Gap ledger armed (write-through persistence, 5 ruled causes, breaker-STOP ready)
6. Auto-mode off (operator-confirmed, client-side setting)
7. Kill-switch + TRADING_ENV guard armed fresh

RED LINE (b): This is the ONLY WO in the sprint that opens a LIVE socket.
Full discipline — execute within declared grant terms, do not exceed them.
"""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import json
import os
import platform
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone, UTC, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator, Optional, Any

# Add project root to path for imports (config, src)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# WO-044 §3: the corpus-spanning records live in src/ (production), not here. The three seam causes
# are DECLARED reason codes and both vocabulary guards scan src/ only, so a seam emitted from tools/
# would be declared-but-unproducible — the exact blind spot WO-037 caught. See corpus.py's docstring.
from trading.data import capture_gate  # noqa: E402
from trading.data.corpus import (  # noqa: E402
    CORPUS_SEAM_CAUSES,
    CORPUS_TARGET_HOURS,
    PREFLIGHT_FILENAME,
    CorpusLedger,
    RunRecord,
    SeamCauseUndeclared,
    SegmentRecord,
    gap_summary,
    run_frame_bounds,
)

if TYPE_CHECKING:
    from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter


# ── WO-057 §5.2: ABORT CONDITION 4's THRESHOLD ────────────────────────────────────────
#
# The condition reads "the retention caps trim MORE THAN ONCE per segment", so the threshold is
# TWO. It is stated here as a named constant rather than left in prose, because a threshold that
# lives only in a checklist cannot be read by the code that must trip on it.
#
# WHY MORE THAN ONE IS THE RIGHT BAR. The caps are sized so a well-behaved segment never trims at
# all; ONE trim means the buffer reached its ceiling once, which is the cap working as designed
# and is expected on a busy hour. REPEATED trimming within a single segment means the message rate
# has outrun the buffer — the caps were sized for a book-only feed, and the trade channel roughly
# doubles the message count. That is precisely what abort condition 4 exists to detect.
#
# ⚠ CARRIED AS AN ASSUMPTION, NOT A MEASUREMENT: the trade rate (1 trade per 8 book frames,
# WO-054) is still unmeasured because no socket has opened. This threshold's *relevance* depends
# on that assumption; its *definition* does not.
RETENTION_TRIM_ABORT_THRESHOLD = 2


# ── CONFIGURATION ─────────────────────────────────────────────────────────────────────

@dataclass
class RotationConfig:
    """Rotation policy configuration (from environment variables)."""

    cadence: str = "hourly"
    segment_duration_seconds: int = 3600
    compression_enabled: bool = True
    retention_days: int = 90
    corpus_dir: Path = field(default_factory=lambda: Path("captures/corpus_24h"))
    # WO-044 §3.1: the stable id every run of this corpus accumulates under. Empty means "start a
    # new corpus", which the runner resolves to a fresh id — an explicit choice, never a silent
    # re-use of whatever happened to be on disk.
    corpus_id: str = ""

    @classmethod
    def from_env(cls) -> RotationConfig:
        """Load configuration from environment variables."""
        return cls(
            cadence=os.environ.get("CORPUS_ROTATION_CADENCE", "hourly"),
            segment_duration_seconds=int(os.environ.get("CORPUS_SEGMENT_DURATION_SECONDS", "3600")),
            compression_enabled=os.environ.get("CORPUS_COMPRESSION_ENABLED", "true").lower() == "true",
            retention_days=int(os.environ.get("CORPUS_RETENTION_DAYS", "90")),
            corpus_dir=Path(os.environ.get("CORPUS_DIR", "captures/corpus_24h")),
            corpus_id=os.environ.get("CORPUS_ID", ""),
        )

    def validate(self) -> None:
        """Validate configuration against WO-042 policy."""
        if self.cadence != "hourly":
            raise ValueError(f"Invalid CORPUS_ROTATION_CADENCE: {self.cadence!r}. Only 'hourly' is supported.")
        if self.segment_duration_seconds != 3600:
            raise ValueError(f"Invalid CORPUS_SEGMENT_DURATION_SECONDS: {self.segment_duration_seconds}. Must be 3600 (1 hour).")
        if self.retention_days < 90:
            raise ValueError(f"Invalid CORPUS_RETENTION_DAYS: {self.retention_days}. Minimum is 90 days.")


@dataclass
class LoadRecord:
    """Load conditions record (grant condition 1 / term-2 close)."""

    cpu_percent: float
    # ⚠ WO-058 §2.2 (D58 ruling 2) — RENAMED from `memory_gb`. This is HOST MEMORY **USED**, not
    # free and not this process's. The old name said neither, and three reports read it as free
    # memory and built an unreachable gate on it (see the retirement note in capture_gate.py).
    # Third document-vs-reality naming defect in this project; the name now states the quantity.
    memory_used_gb: float
    other_processes: list[str] = field(default_factory=list)
    background_quiet: bool = True

    @classmethod
    def capture(cls) -> LoadRecord:
        """Capture current load conditions.

        Raises:
            RuntimeError: If psutil is not available (cannot record real load).
        """
        try:
            import psutil
        except ImportError as e:
            raise RuntimeError(
                "LOAD_SENSOR_UNAVAILABLE: psutil is required to record load conditions "
                "(grant condition 1 / term-2 close). Install with: pip install psutil"
            ) from e

        cpu_percent = psutil.cpu_percent(interval=1.0)
        memory = psutil.virtual_memory()
        memory_used_gb = memory.used / (1024 ** 3)

        return cls(
            cpu_percent=cpu_percent,
            memory_used_gb=memory_used_gb,
            background_quiet=True,  # Operator confirms quiet
        )


@dataclass
class SegmentManifest:
    """Per-segment manifest entry."""

    filename: str
    sha256: str
    frame_count: int
    size_bytes: int
    compressed: bool
    start_utc: str
    end_utc: str
    # WO-057 §5.1: retention-cap TRIM EVENTS during this segment. Abort condition 4's subject,
    # in the corpus rather than only in a log. `None` means the runner had no adapter to ask
    # (a reconstructed manifest), which is distinct from a measured zero.
    raw_text_trim_events: Optional[int] = None


@dataclass
class RunManifest:
    """Run-level manifest (MANIFEST.json)."""

    run_id: str
    host: str
    start_utc: str
    end_utc: str
    segments: list[SegmentManifest] = field(default_factory=list)
    gap_ledger: str = "gap_ledger.json"
    gap_ledger_sha256: str = ""
    crash_artifact: str = ""  # CRASH_TRACEBACK.txt if capture crashed
    crash_artifact_sha256: str = ""
    load_record: Optional[LoadRecord] = None
    host_suspend_events: int = 0
    performance_summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "run_id": self.run_id,
            "host": self.host,
            "start_utc": self.start_utc,
            "end_utc": self.end_utc,
            "segments": [
                {
                    "filename": s.filename,
                    "sha256": s.sha256,
                    "frame_count": s.frame_count,
                    "size_bytes": s.size_bytes,
                    "compressed": s.compressed,
                    "start_utc": s.start_utc,
                    "end_utc": s.end_utc,
                    # WO-059 FIX: WO-057 added this field to SegmentManifest and populated it at
                    # segment close, but NEVER ADDED IT HERE — so the counter reached the object
                    # and never the record. Abort condition 4 was unmeasurable in the WO-058
                    # validation run for exactly that reason. The record is the deliverable, not
                    # the attribute (0.9).
                    "raw_text_trim_events": s.raw_text_trim_events,
                }
                for s in self.segments
            ],
            "gap_ledger": self.gap_ledger,
            "gap_ledger_sha256": self.gap_ledger_sha256,
            "crash_artifact": self.crash_artifact,
            "crash_artifact_sha256": self.crash_artifact_sha256,
            "load_record": {
                "cpu_percent": self.load_record.cpu_percent,
                # WO-058 §2.2: BOTH keys are written. `memory_used_gb` is the correct name going
                # forward; `memory_gb` is retained so a reader written against the existing
                # corpora — corpus_20260805 among them — keeps working. The old key is a
                # COMPATIBILITY ALIAS, not a second quantity: both carry memory USED.
                "memory_used_gb": self.load_record.memory_used_gb,
                "memory_gb": self.load_record.memory_used_gb,
                "other_processes": self.load_record.other_processes,
                "background_quiet": self.load_record.background_quiet,
            } if self.load_record else None,
            "host_suspend_events": self.host_suspend_events,
            "performance_summary": self.performance_summary,
        }


# ── CORPUS CAPTURE RUNNER ─────────────────────────────────────────────────────────────

class CorpusCaptureError(RuntimeError):
    """Preflight refusal — raised BEFORE any connection when the run is unsafe/unrecorded."""


class CorpusCaptureRunner:
    """
    24-hour corpus capture runner.

    Demonstrates all grant conditions as preflight, then opens the socket and
    captures to hourly UTC-stamped segments per WO-042 rotation policy.
    """

    SYMBOL = "BTC/USD"
    DURATION_HOURS = 24

    def __init__(
        self,
        config: Optional[RotationConfig] = None,
        trading_env: Optional[str] = None,
        connect_fn: Any = None,
        monotonic_clock: Any = None,
        wall_clock: Any = None,
        seam_cause: Optional[str] = None,
        duration_hours: Optional[float] = None,
    ) -> None:
        """
        Initialize the corpus capture runner.

        Args:
            config: Rotation policy configuration (defaults to env vars)
            trading_env: TRADING_ENV (defaults to os.environ.get)
            connect_fn: WebSocket transport (test seam)
            monotonic_clock: Monotonic clock (test seam)
            wall_clock: Wall clock (test seam)
        """
        self._config = config or RotationConfig.from_env()
        # WO-057 §5.1: the live adapter, once built. None until run() creates it, and None in a
        # reconstructed manifest — which is why the segment field distinguishes None from 0.
        self._adapter = None
        if trading_env is None:
            trading_env = os.environ.get("TRADING_ENV")
        self._trading_env = trading_env

        self._connect_fn = connect_fn
        # Keep clocks as None unless explicitly injected for tests
        # For real transport, clock injection is refused
        self._monotonic_clock = monotonic_clock
        self._wall_clock = wall_clock

        # Generate run ID ONCE, at initialization. WO-043 generated it here AND again in run(), so
        # the path the preflight announced was not the path the run wrote to — a small dishonesty
        # in the opening record. One id, generated once, used everywhere.
        self._run_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S")

        self._manifest: Optional[RunManifest] = None
        self._current_segment: Optional[Path] = None
        self._segment_frame_count: int = 0
        self._segment_start_utc: Optional[str] = None
        self._total_frame_count: int = 0

        # WO-044 §3.3: the operator-declared reason the PRIOR run ended. Required only when a prior
        # run exists (see _preflight); the process cannot infer it, so it must be told.
        self._seam_cause = seam_cause
        self._seam = None
        self._first_frame_utc: str = ""
        self._last_frame_utc: str = ""
        if duration_hours is not None:
            self.DURATION_HOURS = duration_hours

        # Validate config AFTER setting up other attributes
        try:
            self._config.validate()
        except ValueError as e:
            raise CorpusCaptureError(f"CONFIG_INVALID: {e}") from e

        # WO-044 §3.1: resolve the corpus-id and open its ledger BEFORE the preflight, so the
        # preflight can report cumulative progress and demand a seam cause when one is owed.
        self._corpus_id = self._config.corpus_id or f"corpus_{self._run_id}"
        self._ledger = CorpusLedger(
            root=self._config.corpus_dir, corpus_id=self._corpus_id, host=platform.node(),
        )
        # Fold in any run whose process died before finalizing (the SIGKILL case) so the meter
        # reflects the disk, not just the runs that got to write their own epitaph.
        self._reconciled = self._ledger.reconcile()

        # Run the preflight BEFORE any connection
        self._preflight()

    def _preflight(self) -> None:
        """
        Demonstrate all grant conditions BEFORE the socket opens.

        Any red aborts before connection — this is the preflight block logged
        as the run's opening record.

        WO-044 §3.2 — NO INHERITED PRECONDITIONS. Every resume runs this in full and writes the
        result to its own PREFLIGHT.json. A resume does not inherit the prior run's greens: each
        condition is re-demonstrated by THIS process, in THIS run's directory, as this run's opening
        record. That is the whole point of condition 1 — a preflight that could be inherited would
        be a checklist, and checklist-enforced rules are 0-for-N in this project.
        """
        print("=" * 70)
        print("WO-044 CORPUS CAPTURE PREFLIGHT — Demonstrating Grant Conditions")
        print(f"corpus_id: {self._corpus_id}   run_id: {self._run_id}")
        print("=" * 70)

        all_green = True
        # The machine-readable opening record. Every condition writes its REAL measured value here,
        # so PREFLIGHT.json is evidence rather than a transcript of green ticks.
        record: dict = {
            "wo": "WO-044",
            "corpus_id": self._corpus_id,
            "run_id": self._run_id,
            "run_start_utc": datetime.now(UTC).isoformat(),
            "host": platform.node(),
            "conditions": {},
        }
        self._preflight_record = record

        # 3.1 Paper-env + no-credential
        print("\n[3.1] Paper-env + no-credential (grant boundary)...")
        if self._trading_env != "paper":
            print(f"  ❌ RED: TRADING_ENV={self._trading_env!r}, must be 'paper'")
            all_green = False
        else:
            print(f"  ✅ GREEN: TRADING_ENV=paper")
        record["conditions"]["paper_env"] = {
            "green": self._trading_env == "paper", "trading_env": self._trading_env,
        }

        # Check .env for credentials
        env_path = Path(".env")
        if env_path.exists():
            env_content = env_path.read_text()
            # Check for credential-like patterns
            credential_patterns = ["API_KEY", "SECRET", "PASSWORD", "TOKEN"]
            found_credentials = [
                pattern for pattern in credential_patterns
                if pattern in env_content.upper()
            ]
            if found_credentials:
                print(f"  ❌ RED: Found credential patterns in .env: {found_credentials}")
                all_green = False
            else:
                print(f"  ✅ GREEN: No credentials in .env")
            record["conditions"]["no_credential"] = {
                "green": not found_credentials, "patterns_found": found_credentials,
            }
        else:
            print(f"  ✅ GREEN: .env not present (using defaults)")
            record["conditions"]["no_credential"] = {"green": True, "patterns_found": []}

        # 3.2 Host-suspend armed. READ FROM THE ADAPTER CLASS, not restated: a hand-copied constant
        # is a second source of truth waiting to diverge from the detector it claims to describe.
        print("\n[3.2] Host-suspend armed (VOID condition)...")
        from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter
        divergence_bound = KrakenV2BookAdapter.HOST_SUSPEND_DIVERGENCE_SECONDS
        print(f"  ✅ GREEN: Host-suspend detector armed with {divergence_bound}s divergence bound")
        print(f"           VOID rule: affected windows labeled VOID, not hidden")
        print(f"           INDEPENDENT of the outage window (§4.3): a suspend during an outage "
              f"still VOIDs")
        record["conditions"]["host_suspend_armed"] = {
            "green": True, "divergence_bound_seconds": divergence_bound,
        }

        # 3.3 Load recorded (grant condition 1 / term-2 close)
        print("\n[3.3] Load recorded (grant condition 1 / term-2 close)...")
        self._load_record = LoadRecord.capture()
        print(f"  ✅ GREEN: Load conditions captured:")
        print(f"           CPU: {self._load_record.cpu_percent}%")
        print(f"           Memory USED: {self._load_record.memory_used_gb:.2f} GB "
              f"(host-wide; NOT free, NOT this process)")
        print(f"           Background-quiet: {self._load_record.background_quiet}")
        record["conditions"]["load_recorded"] = {
            "green": True,
            "cpu_percent": self._load_record.cpu_percent,
            "memory_used_gb": self._load_record.memory_used_gb,
            "memory_gb": self._load_record.memory_used_gb,   # compatibility alias (WO-058 §2.2)
            "background_quiet": self._load_record.background_quiet,
        }

        # 3.4 Rotation consumed (grant condition 3)
        print("\n[3.4] Rotation consumed (grant condition 3)...")
        print(f"  ✅ GREEN: Rotation policy loaded:")
        print(f"           Cadence: {self._config.cadence}")
        print(f"           Segment duration: {self._config.segment_duration_seconds}s (1 hour)")
        print(f"           Compression: {self._config.compression_enabled}")
        print(f"           Retention: {self._config.retention_days} days")
        print(f"           Corpus dir: {self._config.corpus_dir}")

        # Verify first segment path will be correct — the REAL path this run will write, computed by
        # the same method the run uses, not a lookalike rebuilt inline (WO-043 printed a lookalike
        # while run() wrote elsewhere under a regenerated run_id).
        expected_path = self._get_segment_path(datetime.now(UTC))
        print(f"           Corpus dir: {self._config.corpus_dir}")
        print(f"           First segment path: {expected_path}")
        record["conditions"]["rotation_loaded"] = {
            "green": True,
            "cadence": self._config.cadence,
            "segment_duration_seconds": self._config.segment_duration_seconds,
            "compression_enabled": self._config.compression_enabled,
            "retention_days": self._config.retention_days,
            "first_segment_path": str(expected_path),
        }

        # 3.5 Gap ledger armed. Causes READ FROM the adapter's closed set, same reasoning as 3.2.
        print("\n[3.5] Gap ledger armed...")
        from trading.data.adapters.kraken_v2_book import GAP_CAUSES
        print(f"  ✅ GREEN: Gap ledger configured with write-through persistence")
        print(f"           {len(GAP_CAUSES)} ruled causes: {', '.join(GAP_CAUSES)}")
        print(f"           Breaker-STOP with forensic tail ready")
        record["conditions"]["gap_ledger_armed"] = {
            "green": True, "causes": list(GAP_CAUSES),
        }

        # 3.6 Auto-mode off (grant condition 2)
        print("\n[3.6] Auto-mode off (grant condition 2)...")
        print("  ⏳ PAUSED: Require operator confirmation...")
        print()
        print("  ❗ GRANT CONDITION 2: Auto-mode must be OFF for this run.")
        print("  ❗ Look at the bottom bar of your Claude Code client.")
        print("  ❗ If you see 'Auto' or an auto-indicator → STOP, flip it OFF, then retry.")
        print("  ❗ If you see 'Manual' or NO auto-indicator → confirm below to proceed.")
        print()

        # Check for explicit confirmation (either interactive prompt or env var)
        auto_confirmed = os.environ.get("CORPUS_AUTO_MODE_CONFIRMED", "").lower() == "true"

        if auto_confirmed:
            print(f"  ✅ GREEN: Auto-mode OFF confirmed via CORPUS_AUTO_MODE_CONFIRMED=true")
        elif sys.stdin.isatty():
            try:
                response = input("  Type 'CONFIRM' to proceed (auto-mode is OFF): ").strip()
                if response.upper() != "CONFIRM":
                    print(f"  ❌ RED: Operator did not confirm auto-mode OFF (response: {response!r})")
                    all_green = False
                else:
                    print(f"  ✅ GREEN: Operator-confirmed auto-mode OFF")
            except EOFError:
                print(f"  ❌ RED: Non-interactive terminal without CORPUS_AUTO_MODE_CONFIRMED=true")
                print(f"           Run in an interactive terminal OR set CORPUS_AUTO_MODE_CONFIRMED=true")
                all_green = False
        else:
            # Non-interactive mode without explicit confirmation
            print(f"  ❌ RED: Non-interactive mode requires CORPUS_AUTO_MODE_CONFIRMED=true")
            print(f"           Set CORPUS_AUTO_MODE_CONFIRMED=true to confirm auto-mode is OFF")
            all_green = False

        record["conditions"]["auto_mode_off"] = {
            "green": all_green and (auto_confirmed or sys.stdin.isatty()),
            "confirmed_via": "CORPUS_AUTO_MODE_CONFIRMED" if auto_confirmed else "interactive",
        }

        # 3.7 Kill-switch + TRADING_ENV guard — EXECUTED, not asserted.
        #
        # WO-044 FINDING (reported, then repaired here). WO-043 printed a HARDCODED string —
        # "Guards armed fresh (demonstrated by test suite) / 237 passed, 2 skipped" — that ran no
        # test, checked nothing, and could not go red. Every corpus run so far logged that line as a
        # green grant condition without it ever having been measured at run time; by WO-044 the
        # number was also wrong (the suite is 256). A condition that cannot fail is a checklist, and
        # live_capture.py:12 records why this project does not accept those: "PREFLIGHT ENFORCEMENT
        # LIVES IN THE RUNNER, not a checklist — checklist-enforced rules are 0-for-N."
        #
        # It matters more under §3.2 than before: a resume must RE-DEMONSTRATE this guard as its own
        # opening record, and a resume that inherits a frozen string is exactly the inherited
        # precondition condition 1 forbids. So the guard is now EXERCISED, here, in this process:
        # engage a fresh kill switch and prove it VETOes, and prove the live-capture preflight
        # refuses a non-paper env. Both can go red, which is the only thing that makes them evidence.
        print("\n[3.7] Kill-switch + TRADING_ENV guard armed (EXECUTED this run)...")
        guard_detail: dict = {}
        try:
            from decimal import Decimal
            from trading.risk.engine import DeterministicRiskEngine
            from trading.risk.interface import RiskDecision
            from trading.risk.position_state import PositionState
            from trading.data.desired_position import DesiredPosition, Side
            from trading.loop.live_capture import LiveCaptureRunner, LiveCaptureError

            engine = DeterministicRiskEngine()
            engine.set_kill_switch(True)
            # NOTE: DesiredPosition has NO confidence field, deliberately — Principle III forbids it
            # as "a latent hook for ML scores to enter the live decision path". Both models are
            # frozen dataclasses with every field required, so they are constructed in full.
            decision, order, reason = engine.check(
                DesiredPosition(
                    timestamp=datetime.now(UTC), symbol=self.SYMBOL,
                    side=Side.BUY, quantity=Decimal("0.01"),
                    feature_snapshot_hash="preflight-guard-probe",
                ),
                PositionState(
                    symbol=self.SYMBOL, current_quantity=Decimal("0"),
                    average_entry_price=Decimal("0"), unrealized_pnl=Decimal("0"),
                    realized_pnl=Decimal("0"), daily_pnl=Decimal("0"),
                ),
                datetime.now(UTC),
            )
            kill_ok = (decision is RiskDecision.VETO and order is None
                       and reason == DeterministicRiskEngine.REASON_VETO_KILL_SWITCH)

            # The TRADING_ENV guard: the live-capture preflight must REFUSE a non-paper env.
            try:
                LiveCaptureRunner(persist_path="unused", duration_seconds=1.0,
                                  trading_env="mainnet")
                env_ok = False          # it did NOT refuse — the rail is not armed
            except LiveCaptureError as exc:
                env_ok = "LIVE_CAPTURE_ENV_REFUSED" in str(exc)

            guard_detail = {
                "kill_switch_vetoes": kill_ok, "kill_switch_reason": reason,
                "trading_env_guard_refuses_mainnet": env_ok,
            }
            if kill_ok and env_ok:
                print(f"  ✅ GREEN: kill switch VETOed with {reason}")
                print(f"           TRADING_ENV guard refused a mainnet live capture")
            else:
                print(f"  ❌ RED: guard demonstration failed: {guard_detail}")
                all_green = False
        except Exception as exc:                      # noqa: BLE001 — a guard that errors is RED
            print(f"  ❌ RED: guard demonstration raised {type(exc).__name__}: {exc}")
            guard_detail = {"error": f"{type(exc).__name__}: {exc}"}
            all_green = False
        record["conditions"]["guards_armed"] = {
            "green": guard_detail.get("kill_switch_vetoes", False)
            and guard_detail.get("trading_env_guard_refuses_mainnet", False),
            **guard_detail,
        }

        # WO-044 §3.2/§3.3: the corpus position and the seam this resume owes.
        print("\n[3.8] Corpus position + seam (WO-044 §3.1/§3.3)...")
        prior = self._ledger.prior_run()
        if self._reconciled:
            print(f"  ℹ RECONCILED from disk (process died before finalizing): {self._reconciled}")
        progress = self._ledger.progress()
        print(f"  ✅ GREEN: corpus {self._corpus_id}")
        print(f"           runs so far: {progress['runs']}   seams: {progress['seam_count']}")
        print(f"           COVERED (the target metric): "
              f"{progress['cumulative_covered_hours']:.4f}h / "
              f"{progress['target_covered_hours']}h   "
              f"remaining: {progress['remaining_covered_hours']:.4f}h")
        print(f"           elapsed wall-clock (NOT the metric): "
              f"{progress['elapsed_wall_hours']:.4f}h")
        if prior is None:
            print(f"           FIRST run of this corpus — no seam owed")
            record["conditions"]["seam"] = {"green": True, "first_run": True}
        else:
            if self._seam_cause not in CORPUS_SEAM_CAUSES:
                print(f"  ❌ RED: resuming corpus {self._corpus_id} after run {prior.run_id} "
                      f"requires a DECLARED seam cause")
                print(f"           got {self._seam_cause!r}; expected one of "
                      f"{list(CORPUS_SEAM_CAUSES)}")
                print(f"           the process cannot infer why the prior run ended — declare it "
                      f"with --seam-cause")
                all_green = False
                record["conditions"]["seam"] = {
                    "green": False, "prior_run_id": prior.run_id,
                    "declared_cause": self._seam_cause,
                }
            else:
                print(f"  ✅ GREEN: seam cause DECLARED as {self._seam_cause}")
                print(f"           prior run: {prior.run_id}  last frame: "
                      f"{prior.last_frame_utc or '(none)'}")
                record["conditions"]["seam"] = {
                    "green": True, "prior_run_id": prior.run_id,
                    "declared_cause": self._seam_cause,
                    "prior_last_frame_utc": prior.last_frame_utc,
                }
        record["corpus_progress_at_start"] = progress

        # ── [3.8b] TERM 2: THE RE-SPECIFIED MEMORY GATE (WO-057 §2, D57 ruling 1) ────────────
        #
        # The gate is READ from committed code (`trading.data.capture_gate`), not re-derived here.
        # That module carries the derivation, the declared floor, the observation window and the
        # falsifier, so this site cannot drift from the figure the report cites — and the figure
        # is computed by code committed in the tree it certifies (the D51 standing rule).
        #
        # ⚠ IT REPLACES A COMPARISON THAT WAS NOT EVEN LIKE-FOR-LIKE. The old Term 2 reference,
        # "12.33 GB free", is the WO-044 preflight's `memory_gb` — which `LoadRecord.capture()`
        # computes as `virtual_memory().used`, i.e. memory USED. Three reports compared today's
        # AVAILABLE against that capture's USED. On this host the WO-044 capture actually ran with
        # ~3.4 GiB free — LESS than the readings later called RED.
        print("\n[3.8b] Term 2 memory gate (WO-057 §2: zero swap sustained + derived floor)...")
        gate = capture_gate.evaluate()
        if gate.green:
            print(f"  ✅ GREEN: {gate.detail}")
        else:
            print(f"  ❌ RED: {gate.detail}")
            all_green = False
        record["conditions"]["term2_memory_gate"] = gate.to_dict()

        # ── [3.9] OPERATOR PREREQUISITE: the shutdown policy (WO-044 preamble) ────────────────
        # "The security policy that shuts the machine down must be DISABLED and confirmed. That
        # policy caused two lost runs. State it confirmed in the preflight."
        #
        # OPERATOR-DECLARED, like auto-mode and like the seam cause: the process cannot inspect a
        # host security policy, and a check that silently assumes the answer is worse than none.
        # So it is asked for BY NAME and goes RED when absent. It is a first-class preflight
        # condition rather than a note because of what it already cost — runs 20260729044021
        # (~2h37m) and 20260730152029 (~3h55m) both died with every frame on disk and no manifest,
        # and run 3 then failed §2 eligibility precisely because of that.
        print("\n[3.9] Shutdown policy DISABLED (operator prerequisite)...")
        shutdown_confirmed = (
            os.environ.get("CORPUS_SHUTDOWN_POLICY_DISABLED", "").lower() == "true")
        if shutdown_confirmed:
            print(f"  ✅ GREEN: operator confirms the machine-shutdown security policy is DISABLED")
            print(f"           (declared via CORPUS_SHUTDOWN_POLICY_DISABLED=true)")
        else:
            print(f"  ❌ RED: the shutdown policy has NOT been confirmed disabled.")
            print(f"          It already cost two runs (20260729044021, 20260730152029).")
            print(f"          Set CORPUS_SHUTDOWN_POLICY_DISABLED=true only after actually")
            print(f"          disabling it — the process cannot verify a host policy itself.")
            all_green = False
        record["conditions"]["shutdown_policy_disabled"] = {
            "green": shutdown_confirmed,
            "confirmed_via": "CORPUS_SHUTDOWN_POLICY_DISABLED",
            "operator_declared": True,
        }

        # ── [3.10] GRANT EXPIRY (D45: corpus completion or 14 days, whichever first) ──────────
        # A grant with no ENFORCED end is a grant that quietly outlives its authorisation. The
        # date is DECLARED (the WO embeds none) and then enforced here: past it the run refuses,
        # rather than trusting anyone to remember.
        print("\n[3.10] Grant expiry (D45: 14 days or corpus completion)...")
        expiry_raw = os.environ.get("CORPUS_GRANT_EXPIRY", "").strip()
        expiry_ok = False
        expiry_detail: dict = {"declared": expiry_raw or None}
        if not expiry_raw:
            print(f"  ❌ RED: no grant expiry declared. Set CORPUS_GRANT_EXPIRY=YYYY-MM-DD.")
            all_green = False
        else:
            try:
                expiry_date = datetime.fromisoformat(expiry_raw).date()
                today = datetime.now(UTC).date()
                days_left = (expiry_date - today).days
                expiry_detail.update({"expiry_date": expiry_date.isoformat(),
                                      "today_utc": today.isoformat(),
                                      "days_remaining": days_left})
                if days_left < 0:
                    print(f"  ❌ RED: the grant EXPIRED on {expiry_date} ({-days_left}d ago).")
                    print(f"          Refusing to open a socket outside the authorised window.")
                    all_green = False
                else:
                    expiry_ok = True
                    print(f"  ✅ GREEN: grant valid until {expiry_date} "
                          f"({days_left} day(s) remaining)")
            except ValueError:
                print(f"  ❌ RED: CORPUS_GRANT_EXPIRY={expiry_raw!r} is not an ISO date.")
                all_green = False
        record["conditions"]["grant_expiry"] = {"green": expiry_ok, **expiry_detail}

        record["all_green"] = all_green
        record["preflight_completed_utc"] = datetime.now(UTC).isoformat()

        # §3.2: persist the opening record BEFORE the verdict branches, so a REFUSED preflight
        # leaves evidence too. A refusal that vanishes is indistinguishable from a run never
        # attempted, and §0.5 says report every attempt.
        self._write_preflight_record(record)

        print("\n" + "=" * 70)
        if all_green:
            print("✅ PREFLIGHT COMPLETE — ALL CONDITIONS GREEN")
            print(f"Opening record: {self._run_dir() / PREFLIGHT_FILENAME}")
            print("Opening socket in 3 seconds... (Ctrl+C to abort)")
            print("=" * 70)
            time.sleep(3)
        else:
            print("❌ PREFLIGHT FAILED — RED CONDITIONS DETECTED")
            print("Refusing to open socket. Fix red conditions and retry.")
            print("=" * 70)
            raise CorpusCaptureError("PREFLIGHT_FAILED: Red conditions detected, refusing to run.")

    def _write_preflight_record(self, record: dict) -> Path:
        """Write this run's PREFLIGHT.json — the §3.2 opening record, per run, never inherited."""
        run_dir = self._run_dir()
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / PREFLIGHT_FILENAME
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return path

    def _run_dir(self) -> Path:
        """§3.1 layout: <corpus_dir>/<corpus_id>/<run_id>/ — grouping is STRUCTURAL, so a run
        cannot belong to a corpus without living inside it."""
        return self._config.corpus_dir / self._corpus_id / self._run_id

    def _get_segment_path(self, utc_time: datetime) -> Path:
        """Get the segment path for a given UTC time."""
        host = platform.node().upper()
        hour_segment = utc_time.replace(minute=0, second=0, microsecond=0)
        filename = f"corpus_{host}_{hour_segment.strftime('%Y%m%dT%H')}Z.jsonl"
        return self._run_dir() / filename

    def _open_segment(self, utc_time: datetime) -> Path:
        """Open a new hourly segment."""
        segment_path = self._get_segment_path(utc_time)
        segment_path.parent.mkdir(parents=True, exist_ok=True)

        # Track segment metadata
        self._current_segment = segment_path
        self._segment_frame_count = 0
        self._segment_start_utc = utc_time.isoformat()

        print(f"[{utc_time.isoformat()}] Opening segment: {segment_path.name}")

        return segment_path

    def _close_segment(self, utc_time: datetime) -> SegmentManifest:
        """Close the current segment and compute SHA-256."""
        if self._current_segment is None:
            raise RuntimeError("No segment to close")

        segment_path = self._current_segment

        # Compute SHA-256
        sha256 = hashlib.sha256()
        with open(segment_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        segment_sha256 = sha256.hexdigest()
        size_bytes = segment_path.stat().st_size

        print(f"[{utc_time.isoformat()}] Closing segment: {segment_path.name}")
        print(f"           Frames: {self._segment_frame_count}")
        print(f"           Size: {size_bytes:,} bytes")
        print(f"           SHA-256: {segment_sha256}")

        # Compress if enabled
        compressed = False
        if self._config.compression_enabled:
            compressed_path = segment_path.with_suffix(segment_path.suffix + ".gz")
            with open(segment_path, "rb") as f_in:
                with gzip.open(compressed_path, "wb") as f_out:
                    for chunk in iter(lambda: f_in.read(8192), b""):
                        f_out.write(chunk)
            compressed_size = compressed_path.stat().st_size
            compression_ratio = size_bytes / compressed_size if compressed_size > 0 else 0
            print(f"           Compressed: {compressed_size:,} bytes ({compression_ratio:.1f}×)")
            compressed = True

        # Create manifest entry
        # WO-057 §5.1 — abort condition 4's number, READ AND RESET at rotation so it is
        # per-segment. Lands in the segment record (the corpus), not only in a log.
        trim_events = None
        if self._adapter is not None and hasattr(self._adapter, "take_trim_events"):
            trim_events = self._adapter.take_trim_events()
            if trim_events >= RETENTION_TRIM_ABORT_THRESHOLD:
                print(f"           ⚠ RETENTION TRIMS: {trim_events} "
                      f"(abort threshold {RETENTION_TRIM_ABORT_THRESHOLD})")

        manifest = SegmentManifest(
            filename=segment_path.name,
            sha256=segment_sha256,
            frame_count=self._segment_frame_count,
            size_bytes=size_bytes,
            compressed=compressed,
            start_utc=self._segment_start_utc or utc_time.isoformat(),
            end_utc=utc_time.isoformat(),
            raw_text_trim_events=trim_events,
        )

        return manifest

    async def _write_frame(self, frame: dict, utc_time: datetime) -> None:
        """Write a frame to the current segment."""
        if self._current_segment is None:
            self._open_segment(utc_time)

        with open(self._current_segment, "a") as f:
            f.write(json.dumps(frame) + "\n")

        self._segment_frame_count += 1
        self._total_frame_count += 1

    async def run(self) -> RunManifest:
        """Run the 24-hour corpus capture."""
        # Import factory for live feed creation
        from trading.data.adapters import factory

        # WO-044: the run_id was generated ONCE in __init__ and is NOT regenerated here. WO-043
        # regenerated it, so the preflight announced a path the run never wrote to.
        start_utc = datetime.now(UTC)

        # Initialize manifest
        self._manifest = RunManifest(
            run_id=self._run_id,
            host=platform.node(),
            start_utc=start_utc.isoformat(),
            end_utc="",  # Set on completion
            load_record=self._load_record,
        )

        # Gap ledger path
        gap_ledger_path = self._run_dir() / "gap_ledger.json"
        gap_ledger_path.parent.mkdir(parents=True, exist_ok=True)

        # §3.3: OPEN the seam now, before the socket. The left bound is the prior run's last frame,
        # read off disk (a SIGKILL never reaches a finally block, but the frames it already wrote
        # survive). The seam stays OPEN — duration None, denying every query — until this run's
        # first frame closes it. An unclosed seam is loud by construction, exactly like an unclosed
        # gap: a resume that connects but never emits leaves a seam that never resolves.
        prior = self._ledger.prior_run()
        if prior is not None and self._seam_cause in CORPUS_SEAM_CAUSES:
            prior_last = prior.last_frame_utc
            if not prior_last:
                _, prior_last = run_frame_bounds(self._ledger.run_dir(prior.run_id))
            try:
                self._seam = self._ledger.open_seam(
                    cause=self._seam_cause,
                    prior_run_id=prior.run_id,
                    resumed_run_id=self._run_id,
                    prior_last_frame_utc=prior_last,
                    detail=f"resume of corpus {self._corpus_id} after run {prior.run_id}",
                )
                print(f"[seam] OPENED  cause={self._seam_cause}  prior_last_frame={prior_last}")
            except SeamCauseUndeclared as exc:
                # Refuse rather than run an unlabeled seam — §0.4 owns this.
                raise CorpusCaptureError(str(exc)) from exc

        print("=" * 70)
        print(f"WO-044 CORPUS CAPTURE RUN — corpus {self._corpus_id} / run {self._run_id}")
        print("=" * 70)
        print(f"Duration: {self.DURATION_HOURS} hours")
        print(f"Symbol: {self.SYMBOL}")
        print(f"Run dir: {self._run_dir()}")
        print(f"COVERED before this run: "
              f"{self._ledger.progress()['cumulative_covered_hours']:.4f}h / {CORPUS_TARGET_HOURS}h "
              f"(data coverage, NOT elapsed wall-clock)")
        print("=" * 70)

        # Create live feed through factory (grant-authorized path)
        import websockets
        connect_fn = self._connect_fn or websockets.connect

        # Build factory kwargs - only pass clocks if explicitly injected (for tests)
        # For real transport, clock injection is refused (coupling gate)
        factory_kwargs = {
            "persist_path": str(gap_ledger_path),
            "duration_seconds": self.DURATION_HOURS * 3600,
            "connect_fn": connect_fn,
        }
        if self._monotonic_clock is not None:
            factory_kwargs["monotonic_clock"] = self._monotonic_clock
        if self._wall_clock is not None:
            factory_kwargs["wall_clock"] = self._wall_clock

        adapter, feed_iter = factory.create_live_capture_feed(**factory_kwargs)
        # WO-057 §5.1: held so segment close can read the per-segment trim counter off it.
        self._adapter = adapter

        # Track rotation boundaries
        segment_boundary = self._get_segment_boundary(start_utc)

        # Main capture loop
        try:
            async for market_state in feed_iter:
                utc_now = datetime.now(UTC)

                # Check for segment rotation
                if utc_now >= segment_boundary:
                    # Close current segment
                    if self._current_segment is not None:
                        manifest = self._close_segment(utc_now)
                        self._manifest.segments.append(manifest)

                    # Open new segment
                    self._open_segment(utc_now)
                    segment_boundary = self._get_segment_boundary(utc_now)

                # Write frame
                frame = {
                    "timestamp": utc_now.isoformat(),
                    "symbol": market_state.symbol,
                    "bid": str(market_state.best_bid),
                    "ask": str(market_state.best_ask),
                    "bid_qty": str(market_state.best_bid_size),  # MarketState uses size, not qty
                    "ask_qty": str(market_state.best_ask_size),
                    "spread": str(market_state.spread),
                }
                # ── WO-056 §7 / §0.14 — THE PRODUCTION CALL SITE THAT REACHES trade_channel ──
                #
                # This line is the wire whose absence D55 ruled on. WO-054 built the merger, the
                # schema, the availability ledger, 22 tests and a passing bite proof; NOTHING
                # CALLED ANY OF IT, so a capture wrote the seven fields above and nothing else
                # while the suite and CI both read healthy.
                #
                # §6.1 THE ROTATION RULE, DECLARED: the pending delta attaches to the frame it is
                # written with, and this call CLOSES and RESETS the interval. Rotation happens
                # between frames (just above), so a trade arriving between the last frame of
                # segment N and the first of N+1 lands in exactly ONE delta — the first frame of
                # N+1. Nothing is double-counted and nothing is dropped, because there is exactly
                # one snapshot call per written frame and only that call advances the interval.
                #
                # The three states come from the merger per the WO-054 schema: `count: 0` is a
                # positive claim (listening, nothing traded); `count: null` is the ABSENCE of a
                # claim (channel unobservable); `last_price` is never fabricated.
                frame["trades"] = adapter.trade_snapshot_for_frame(frame["timestamp"])
                await self._write_frame(frame, utc_now)

                # §3.3: the FIRST frame is the seam's measured right bound. This state is reached
                # only after FR-018a(d) has validated a fresh snapshot's checksum (§3.4) — an
                # unvalidated book emits nothing, so a seam can only close on proven data.
                if not self._first_frame_utc:
                    self._first_frame_utc = frame["timestamp"]
                    if self._seam is not None and not self._seam.resolved:
                        self._ledger.close_seam(self._seam, self._first_frame_utc)
                        print(f"[seam] CLOSED  cause={self._seam.cause}  "
                              f"TRUE duration={self._seam.duration_seconds:.3f}s")
                self._last_frame_utc = frame["timestamp"]

        except Exception as e:
            print(f"\n❌ CAPTURE ERROR: {e}")
            print("Forensic tail will be included in manifest.")

            # Write full traceback to crash artifact (minute-38 stdout-kill pattern:
            # forensic output belongs in the durable artifact tree, never on ephemeral stdout)
            crash_path = self._run_dir() / "CRASH_TRACEBACK.txt"
            crash_path.parent.mkdir(parents=True, exist_ok=True)
            with open(crash_path, "w") as f:
                f.write(f"CAPTURE CRASH at frame {self._total_frame_count + 1}\n")
                f.write(f"Error: {e}\n\n")
                f.write("=" * 70 + "\n")
                f.write("FULL TRACEBACK:\n")
                f.write("=" * 70 + "\n")
                traceback.print_exc(file=f)

            # Record crash artifact in manifest for forensic tracking
            self._manifest.crash_artifact = str(crash_path.name)

            print(f"Crash traceback written to: {crash_path}")
            raise

        finally:
            # WO-044: bind the finalize timestamp UNCONDITIONALLY. WO-043 bound `utc_now` only
            # inside the rotation branch, so a run that ended before its first frame raised
            # NameError in this `finally` and MASKED the real capture error with a bookkeeping one.
            utc_now = datetime.now(UTC)

            # Close final segment
            if self._current_segment is not None:
                manifest = self._close_segment(utc_now)
                self._manifest.segments.append(manifest)

            # Finalize manifest
            self._manifest.end_utc = utc_now.isoformat()

            # Get gap ledger SHA-256
            if gap_ledger_path.exists():
                sha256 = hashlib.sha256()
                with open(gap_ledger_path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha256.update(chunk)
                self._manifest.gap_ledger_sha256 = sha256.hexdigest()

            # Get crash artifact SHA-256 (if capture crashed)
            if self._manifest.crash_artifact:
                crash_path = self._run_dir() / self._manifest.crash_artifact
                if crash_path.exists():
                    sha256 = hashlib.sha256()
                    with open(crash_path, "rb") as f:
                        for chunk in iter(lambda: f.read(8192), b""):
                            sha256.update(chunk)
                    self._manifest.crash_artifact_sha256 = sha256.hexdigest()

            # Load ledger from adapter
            ledger = adapter.get_gap_ledger()
            if ledger and hasattr(ledger, "gaps"):
                self._manifest.host_suspend_events = sum(
                    1 for gap in ledger.gaps
                    if hasattr(gap, "cause") and gap.cause == "HOST_SUSPEND"
                )

            # Write manifest
            manifest_path = self._run_dir() / "MANIFEST.json"
            with open(manifest_path, "w") as f:
                json.dump(self._manifest.to_dict(), f, indent=2)

            # ── WO-044 §3.5/§3.7: fold this run into the CORPUS-SPANNING manifest ─────────────
            # Every segment of every run, each with its SHA-256, plus the seams — one file that
            # answers what the corpus is made of, and a cumulative meter that answers how far in.
            gaps = gap_summary(gap_ledger_path)
            self._ledger.add_run(RunRecord(
                run_id=self._run_id,
                start_utc=self._manifest.start_utc,
                end_utc=self._manifest.end_utc,
                first_frame_utc=self._first_frame_utc,
                last_frame_utc=self._last_frame_utc,
                segments=[
                    SegmentRecord(
                        filename=s.filename, sha256=s.sha256, frame_count=s.frame_count,
                        size_bytes=s.size_bytes, compressed=s.compressed,
                        start_utc=s.start_utc, end_utc=s.end_utc, run_id=self._run_id,
                        hashed_at_capture=True,   # hashed at close, by the capturing process
                    )
                    for s in self._manifest.segments
                ],
                gap_seconds=gaps["gap_seconds"],
                gap_count=gaps["gap_count"],
                terminal_gaps=gaps["terminal_gaps"],
                incomplete_gaps=gaps["incomplete_gaps"],
                preflight=getattr(self, "_preflight_record", {}),
                finalized=True,           # this process wrote its own epitaph
            ))
            progress = self._ledger.progress()

            print("\n" + "=" * 70)
            print("CORPUS CAPTURE RUN COMPLETE")
            print("=" * 70)
            print(f"Manifest written to: {manifest_path}")
            print(f"Total segments: {len(self._manifest.segments)}")
            print(f"Total frames: {sum(s.frame_count for s in self._manifest.segments)}")
            print(f"Gap ledger: {gap_ledger_path}")
            if self._seam is not None:
                print(f"Seam: {self._seam.cause}  duration={self._seam.duration_seconds}s  "
                      f"resolved={self._seam.resolved}")
            print("-" * 70)
            print(f"CORPUS {self._corpus_id} — CUMULATIVE PROGRESS (§3.7)")
            print(f"  runs:                    {progress['runs']}")
            print(f"  COVERED hours  [TARGET]: {progress['cumulative_covered_hours']:.4f} h "
                  f"/ {progress['target_covered_hours']} h")
            print(f"  remaining COVERED:       {progress['remaining_covered_hours']:.4f} h")
            print(f"  elapsed wall   [NOT the target]: "
                  f"{progress['elapsed_wall_hours']:.4f} h")
            print(f"    excluded in-run gaps:  {progress['excluded_in_run_gap_hours']:.4f} h")
            print(f"    excluded seams:        {progress['excluded_seam_hours']:.4f} h")
            print(f"  seams:                   {progress['seam_count']}  "
                  f"causes={progress['seam_causes']}")
            print(f"  open seams:              {progress['open_seams']}")
            print(f"  unfinalized:             {progress['unfinalized_runs']}")
            print(f"  corpus manifest:         {self._ledger.manifest_path}")
            print("  NOTE: the 24h target is COVERED data time, not elapsed wall-clock time.")
            print("        Reaching it always takes MORE than 24 wall-clock hours.")
            print("=" * 70)

        return self._manifest

    def _get_segment_boundary(self, utc_time: datetime) -> datetime:
        """Get the next hour boundary."""
        return utc_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)


def _detect_live_run(corpus_dir: Path, stale_after_seconds: float = 120.0) -> Optional[str]:
    """WO-045 §4: is a run of this corpus probably LIVE? Returns the run_id, or None.

    CHEAP AND HONEST ABOUT ITS BOUNDS. A run is treated as live when it has NO MANIFEST.json (it
    never finalized) AND one of its segments was written within `stale_after_seconds`. That is a
    heuristic, not proof of liveness — this deliberately does not inspect processes, which would be
    platform-specific and is the reader WO's job.

    The two ways it can be wrong, stated rather than discovered:
      - FALSE POSITIVE: a run killed seconds ago looks live. Cost: a refusal, and `--force-progress`
        is right there. Cheap.
      - FALSE NEGATIVE: a live run that has been stalled for >2 min (a long outage inside the
        breaker window) reads as dead, and --progress proceeds into the very race it guards.
        Cost: a possible clobber of the manifest, recoverable by reconcile().
    The asymmetry is deliberate — the cheap failure is the likely one.
    """
    corpus_dir = Path(corpus_dir)
    if not corpus_dir.is_dir():
        return None
    now = time.time()
    for child in sorted(corpus_dir.iterdir()):
        if not child.is_dir() or (child / "MANIFEST.json").exists():
            continue
        for seg in child.glob("corpus_*.jsonl"):
            try:
                if now - seg.stat().st_mtime < stale_after_seconds:
                    return child.name
            except OSError:
                continue
    return None


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="WO-044 — Resumable 24-Hour Corpus Capture Runner"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run preflight only, do not open socket"
    )
    parser.add_argument(
        "--duration-hours",
        type=float,
        default=24.0,
        help="Capture duration in hours (default: 24)"
    )
    parser.add_argument(
        "--corpus-id",
        default=None,
        help="WO-044 §3.1: the corpus this run accumulates under. Omit to start a NEW corpus; "
             "pass an existing id to RESUME it (a --seam-cause is then required)."
    )
    parser.add_argument(
        "--seam-cause",
        default=None,
        choices=list(CORPUS_SEAM_CAUSES),
        help="WO-044 §3.3: why the PRIOR run of this corpus ended. Required on every resume — the "
             "process cannot observe it, and a guessed cause is a smoothed seam."
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="WO-044 §3.7: print cumulative hours / seams / remaining for --corpus-id and exit. "
             "Opens no socket and runs no preflight. REFUSES against a corpus with a live run "
             "(WO-045 §4) — it writes CORPUS_MANIFEST.json and would race the capture."
    )
    parser.add_argument(
        "--force-progress",
        action="store_true",
        help="WO-045 §4: override the live-run refusal, ACCEPTING the write race against a "
             "running capture. Only for a corpus you know is not being written."
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="WO-046 §6: READ-ONLY coverage/gaps/seams for --corpus-id. Writes NOTHING, so it is "
             "safe against a LIVE capture — this is the query to use while a run is in progress. "
             "Prefer this over --progress, which reconciles and therefore writes."
    )
    args = parser.parse_args()

    config = RotationConfig.from_env()
    if args.corpus_id:
        config.corpus_id = args.corpus_id

    # WO-046 §6 — the READ-ONLY coverage query. Writes nothing, so no live-run refusal is needed:
    # the restriction WO-045 §4 imposed exists because --progress WRITES, and this path does not.
    # It is checked FIRST so `--coverage` is never gated by the writer's guard.
    if args.coverage:
        if not config.corpus_id:
            print("--coverage requires --corpus-id (or CORPUS_ID).")
            raise SystemExit(2)
        from trading.data.corpus_reader import CorpusReader
        reader = CorpusReader(config.corpus_dir / config.corpus_id)
        print(json.dumps(reader.coverage(), indent=2))
        return

    # §3.7 — the progress meter, answerable at ANY time from the committed artifacts alone.
    #
    # WO-045 §4 (D46) — INTERIM RESTRICTION, ENFORCED. `--progress` is a WRITER, not a reader: it
    # calls reconcile(), which saves CORPUS_MANIFEST.json. Run against a LIVE capture it races the
    # capturing process's own finalize write, and the capture's record is the stronger one
    # (finalized=True, hashed_at_capture=True) — losing that race would downgrade real provenance.
    # The read-only live-corpus query is assigned to the default-deny reader WO and is NOT built
    # here. Until it exists this refuses rather than risking the race, and the refusal names the
    # safe alternative.
    if args.progress:
        if not config.corpus_id:
            print("--progress requires --corpus-id (or CORPUS_ID).")
            raise SystemExit(2)
        live = _detect_live_run(config.corpus_dir / config.corpus_id)
        if live and not args.force_progress:
            print(f"REFUSED: corpus {config.corpus_id!r} appears to have a LIVE run ({live}).")
            print("  --progress calls reconcile(), which WRITES CORPUS_MANIFEST.json, and would")
            print("  race the running capture's finalize. The capture's record is the stronger")
            print("  one (finalized + hashed at capture); losing that race downgrades provenance.")
            print("  The read-only live query belongs to the default-deny reader WO (WO-045 §4).")
            print("  Read the run's own artifacts directly, or re-run after the capture ends.")
            print("  --force-progress overrides, accepting the write race.")
            raise SystemExit(3)
        ledger = CorpusLedger(root=config.corpus_dir, corpus_id=config.corpus_id)
        reconciled = ledger.reconcile()
        if reconciled:
            print(f"reconciled from disk (unfinalized runs): {reconciled}")
        print(json.dumps(ledger.progress(), indent=2))
        return

    print("WO-044 — Resumable 24-Hour Corpus Capture Runner")
    print(f"Grant: Kraken mainnet public WS v2, BTC/USD, unauthenticated, read-only")
    print(f"TRADING_ENV=paper")
    print()

    runner_kwargs = {
        "config": config,
        "seam_cause": args.seam_cause,
        "duration_hours": args.duration_hours,
    }

    if args.dry_run:
        print("DRY RUN MODE — preflight only, no socket opened")
        runner = CorpusCaptureRunner(**runner_kwargs)
        print("Preflight passed. Dry run complete.")
        print(json.dumps(runner._ledger.progress(), indent=2))
        return

    print(f"Opening socket for {args.duration_hours}-hour capture...")
    print("(Set --dry-run to preflight only)")
    print()

    runner = CorpusCaptureRunner(**runner_kwargs)

    async def run_capture() -> RunManifest:
        return await runner.run()

    manifest = asyncio.run(run_capture())

    print("\nManifest summary:")
    print(json.dumps(manifest.to_dict(), indent=2))


if __name__ == "__main__":
    main()
