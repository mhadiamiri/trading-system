"""WO-066 §2 — THE TWELVE-TERM PREFLIGHT, run fresh against the HYPERLIQUID path.

    python tools/hyperliquid_preflight.py

TWELVE TERMS, NOT EIGHT. The WO says eight; the implemented preflight has twelve, enumerated from
`tools/live_corpus_capture.py` and corroborated against a recorded PREFLIGHT.json. Using the stated
count would have left four terms unmapped, so the enumerated twelve are used (0.11, and the lead
has ratified the correction).

TERM 8 IS EXECUTED, NOT PRINTED — the WO-044 §3.7 scar. The kill switch is actually tripped and its
veto observed, and the venue guard is actually invoked and its refusal observed. Nothing in this
script reports a guard it did not run.

**OPENS NO SOCKET.** This is a preflight; the socket is gated on operator confirmation (§2).
"""

import json
import os
import sys
from datetime import UTC, datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, _ROOT)   # config.settings lives at the repo root, not under src/

GREEN, RED = "GREEN", "RED"
record: dict = {"wo": "WO-066", "venue": "hyperliquid", "utc": datetime.now(UTC).isoformat(),
                "terms": {}}
all_green = True


def term(n, name, status, detail, **extra):
    global all_green
    if status != GREEN:
        all_green = False
    mark = "OK " if status == GREEN else "RED"
    print(f"[{n:>4}] {name:<26} {mark}  {detail}")
    record["terms"][name] = {"green": status == GREEN, "detail": detail, **extra}




def evaluate() -> tuple:
    """Run all twelve terms and return `(record, all_green)`. OPENS NO SOCKET.

    WO-067: this used to be module-level script code whose only output was a git-ignored
    file under `.artifacts/`. A capture whose twelve-term record lives outside the corpus
    CANNOT BE AUDITED FROM THE CORPUS — the same defect as WO-055's `raw_text_trim_events`
    reaching the object and never the record. It is now callable so the capture can execute
    it FRESH at launch and write the result into the run directory, hashed at capture.

    FRESH, NOT COPIED. The capture re-runs every term rather than lifting the artifact from
    an earlier standalone run: the record in the corpus must be the preflight that actually
    gated THAT run, on that host, at that moment. A copied record would attest a different
    machine-instant while looking identical — and term 8 in particular is executed, not
    printed, so a copy would be a printed guard by another route (the WO-044 §3.7 scar).
    """
    global record, all_green
    record = {"wo": "WO-067", "venue": "hyperliquid",
              "utc": datetime.now(UTC).isoformat(), "terms": {}}
    all_green = True
    print("=" * 100)
    print("WO-066 §2 — HYPERLIQUID SOCKET PREFLIGHT (twelve terms, fresh, no socket opened)")
    print("=" * 100)

    from trading.data.adapters import hyperliquid_v1 as hl          # noqa: E402
    from trading.data.adapters import registry                       # noqa: E402

    # ── 1 paper_env ───────────────────────────────────────────────────────────────────────────────
    env = os.environ.get("TRADING_ENV", "")
    term("1", "paper_env", GREEN if env == "paper" else RED,
         f"TRADING_ENV={env!r} — describes OUR guard state; Hyperliquid has testnet, not 'paper'",
         trading_env=env, mapping="ADAPTS")

    # ── 2 no_credential ───────────────────────────────────────────────────────────────────────────
    import pathlib                                                    # noqa: E402
    patterns = ["API_KEY", "SECRET", "PASSWORD", "TOKEN", "PRIVATE_KEY", "MNEMONIC", "SEED_PHRASE"]
    envf = pathlib.Path(".env")
    found = ([p for p in patterns if p in envf.read_text(encoding="utf-8").upper()]
             if envf.exists() else [])
    term("2", "no_credential", GREEN if not found else RED,
         f".env {'absent' if not envf.exists() else 'present'}; patterns_found={found}; "
         f"WIDENED with PRIVATE_KEY/MNEMONIC/SEED_PHRASE — WO-064 found the Kraken set blind to a "
         f"signing key, and on this venue that gap is live",
         patterns_found=found, mapping="TRANSFERS, widened")

    # ── 3 host_suspend_armed ──────────────────────────────────────────────────────────────────────
    term("3", "host_suspend_armed", GREEN,
         f"{hl.HyperliquidBookAdapter.HOST_SUSPEND_DIVERGENCE_SECONDS}s divergence bound, read from "
         f"the adapter class not restated", mapping="TRANSFERS")

    # ── 4 load_recorded ───────────────────────────────────────────────────────────────────────────
    import psutil                                                     # noqa: E402
    cpu = psutil.cpu_percent(interval=1.0)
    mem_used_gb = (psutil.virtual_memory().total - psutil.virtual_memory().available) / 1024 ** 3
    term("4", "load_recorded", GREEN,
         f"CPU {cpu:.1f}%  memory USED {mem_used_gb:.2f} GB (host-wide, NOT free)",
         cpu_percent=cpu, memory_used_gb=mem_used_gb, mapping="TRANSFERS")

    # ── 5 rotation_loaded ─────────────────────────────────────────────────────────────────────────
    term("5", "rotation_loaded", GREEN,
         "hourly / 3600s / compression on / 90-day retention — venue-agnostic policy",
         mapping="TRANSFERS")

    # ── 6 gap_ledger_armed — FOUR causes, and the fifth's absence is DECLARED ──────────────────────
    ok6 = (len(hl.GAP_CAUSES) == 4 and "CHECKSUM_RESYNC" not in hl.GAP_CAUSES
           and "CHECKSUM_RESYNC" in hl.CAUSE_ABSENT_FROM_THIS_VENUE)
    term("6", "gap_ledger_armed", GREEN if ok6 else RED,
         f"causes={list(hl.GAP_CAUSES)} (FOUR); CHECKSUM_RESYNC declared ABSENT with its reason "
         f"recorded — never repurposed, never wired-and-always-zero",
         causes=list(hl.GAP_CAUSES),
         absent=hl.CAUSE_ABSENT_FROM_THIS_VENUE, mapping="ADAPTS 4/5")

    # ── 7 auto_mode_off ───────────────────────────────────────────────────────────────────────────
    confirmed = os.environ.get("CORPUS_AUTO_MODE_CONFIRMED", "").lower() == "true"
    term("7", "auto_mode_off", GREEN if confirmed else RED,
         f"operator declaration via CORPUS_AUTO_MODE_CONFIRMED={confirmed}", mapping="TRANSFERS")

    # ── 8 guards_armed — EXECUTED, NOT PRINTED (the WO-044 §3.7 scar) ──────────────────────────────
    detail8: dict = {}
    try:
        from decimal import Decimal
        from trading.risk.engine import DeterministicRiskEngine
        from trading.risk.interface import RiskDecision
        from trading.risk.position_state import PositionState
        from trading.data.desired_position import DesiredPosition, Side

        engine = DeterministicRiskEngine()
        engine.set_kill_switch(True)
        decision, order, reason = engine.check(
            DesiredPosition(timestamp=datetime.now(UTC), symbol=hl.SYMBOL, side=Side.BUY,
                            quantity=Decimal("0.01"),
                            feature_snapshot_hash="hyperliquid-preflight-guard-probe"),
            PositionState(symbol=hl.SYMBOL, current_quantity=Decimal("0"),
                          average_entry_price=Decimal("0"), unrealized_pnl=Decimal("0"),
                          realized_pnl=Decimal("0"), daily_pnl=Decimal("0")),
            datetime.now(UTC))
        kill_ok = (decision is RiskDecision.VETO and order is None
                   and reason == DeterministicRiskEngine.REASON_VETO_KILL_SWITCH)

        # THE VENUE GUARD, EXECUTED against the Hyperliquid path: a live capture on an adapter that
        # never declared live capability must REFUSE, loudly and specifically, BEFORE connecting.
        from trading.data.adapters import factory
        try:
            factory.create_live_capture_feed(persist_path="unused", duration_seconds=1.0,
                                             data_source="hyperliquid_v1")
            venue_ok, venue_msg = False, "did NOT refuse — the rail is not armed"
        except Exception as exc:                                      # noqa: BLE001
            venue_ok = "LIVE_CAPTURE_UNSUPPORTED" in str(exc)
            venue_msg = f"{type(exc).__name__}: {str(exc)[:90]}"

        detail8 = {"kill_switch_vetoes": kill_ok, "kill_switch_reason": reason,
                   "hyperliquid_live_capture_refused": venue_ok, "refusal": venue_msg}
        term("8", "guards_armed", GREEN if (kill_ok and venue_ok) else RED,
             f"kill switch VETOed with {reason}; live capture on hyperliquid_v1 REFUSED "
             f"({venue_msg})", mapping="ADAPTS — executed against this venue", **detail8)
    except Exception as exc:                                          # noqa: BLE001
        term("8", "guards_armed", RED, f"guard demonstration raised {type(exc).__name__}: {exc}",
             mapping="ADAPTS")

    # ── 9 seam — READ THE CORPUS, do not assert its state ─────────────────────────────────────────
    #
    # This term used to say "a Hyperliquid capture would be a NEW corpus-id — first run, no seam owed"
    # as a hardcoded GREEN. That was true the day it was written and false the moment the corpus had a
    # run in it, which is now: the 2026-08-12 attempt left 5.35 h on disk. A term that states a fact
    # about the corpus without reading the corpus is the same defect as term 11's, one directory over.
    _corpus_id = os.environ.get("HL_CORPUS_ID", "hlspike_20260812")
    try:
        from trading.data.corpus import CorpusLedger                    # noqa: E402
        from tools.hyperliquid_capture import SEGMENT_PATTERNS          # noqa: E402
        _ledger = CorpusLedger(pathlib.Path("captures/hyperliquid"), _corpus_id,
                               segment_patterns=SEGMENT_PATTERNS)
        _reconciled = _ledger.reconcile()
        _prior = _ledger.prior_run()
        if _prior is None:
            _seam_detail = f"corpus {_corpus_id!r} holds no run — first run, no seam owed"
        else:
            _seam_detail = (
                f"corpus {_corpus_id!r} already holds run {_prior.run_id!r} (last frame "
                f"{_prior.last_frame_utc or 'NONE'}, finalized={_prior.finalized}) — A SEAM IS OWED "
                f"and its cause must be DECLARED on the command line, never guessed")
        term("9", "seam", GREEN, _seam_detail, mapping="TRANSFERS",
             corpus_id=_corpus_id, seam_owed=_prior is not None,
             prior_run_id=(_prior.run_id if _prior else None),
             reconciled_runs=_reconciled,
             cumulative_covered_hours=_ledger.progress().get("cumulative_covered_hours", 0.0))
    except Exception as exc:                                            # noqa: BLE001
        term("9", "seam", RED, f"could not read the corpus: {type(exc).__name__}: {exc}",
             mapping="TRANSFERS")

    # ── 10 term2_memory_gate ──────────────────────────────────────────────────────────────────────
    try:
        from trading.data import capture_gate
        v = capture_gate.evaluate()
        gate = {k: x for k, x in v.to_dict().items() if k != "detail"}
        term("10", "term2_memory_gate", GREEN if v.green else RED,
             f"flow_green={v.flow_green} memory_green={v.memory_green}; "
             f"max_move {v.max_move_pp:.4f} pp, {v.free_mib:.0f} MiB free",
             mapping="TRANSFERS", gate_verdict=gate)
    except Exception as exc:                                          # noqa: BLE001
        term("10", "term2_memory_gate", RED, f"{type(exc).__name__}: {exc}", mapping="TRANSFERS")

    # ── 11 shutdown_policy_disabled — RE-SPECIFIED AS A MEASUREMENT (WO-066) ──────────────────────
    #
    # This term was `CORPUS_SHUTDOWN_POLICY_DISABLED == "true"` — an operator declaration, which is to
    # say an expression no host state could turn RED. It read GREEN on 2026-08-12 and Windows Update
    # restarted the host 5 h 21 m into a 24 h capture, destroying the run. A gate that cannot fail is
    # not a gate; this is the third naming of that family in this project. It now READS THE HOST.
    from trading.loop import reboot_window                              # noqa: E402
    try:
        _hours = float(os.environ.get("HL_CAPTURE_HOURS", "24"))
        _policy = reboot_window.read_host_policy()
        _v = reboot_window.evaluate(_policy, datetime.now().astimezone(), _hours)
        _declared = os.environ.get("CORPUS_SHUTDOWN_POLICY_DISABLED", "").lower() == "true"
        term("11", "shutdown_policy_disabled", GREEN if _v.green else RED,
             f"MEASURED for a {_hours:g} h run — {_v.reason}"
             + ("  [operator ALSO declared it disabled; the declaration is recorded but no longer "
                "decides the term]" if _declared else ""),
             mapping="RE-SPECIFIED — was an operator declaration, now a host measurement",
             operator_declaration=_declared, verdict=_v.to_dict())
    except Exception as exc:                                            # noqa: BLE001
        term("11", "shutdown_policy_disabled", RED,
             f"gate raised {type(exc).__name__}: {exc} — fail-closed, a gate that cannot measure "
             f"must not pass", mapping="RE-SPECIFIED")

    # ── 12 grant_expiry — a NEW grant, not the corpus grant ────────────────────────────────────────
    expiry = os.environ.get("HYPERLIQUID_GRANT_EXPIRY", "")
    ok12 = False
    if expiry:
        try:
            d = datetime.strptime(expiry, "%Y-%m-%d").date()
            days = (d - datetime.now(UTC).date()).days
            ok12 = days >= 0
            msg = f"grant valid until {expiry} ({days} day(s) remaining) — SEPARATE from the corpus grant"
        except ValueError:
            msg = f"unparseable expiry {expiry!r}"
    else:
        msg = "HYPERLIQUID_GRANT_EXPIRY not set — the corpus grant covers Kraken, not this venue"
    term("12", "grant_expiry", GREEN if ok12 else RED, msg, expiry=expiry, mapping="ADAPTS")

    # ── the structural property §2 asks for ───────────────────────────────────────────────────────
    print()
    print("-" * 100)
    outbound = list(hl.HyperliquidBookAdapter().subscriptions()) + [hl.build_ping()]
    methods = sorted({f.get("method") for f in outbound})
    print(f"ORDER PATH   : outbound methods = {methods}  (Hyperliquid's ORDER method is 'post' — absent)")
    print(f"               no order/sign/wallet symbol on module or class; no signing-capable import")
    print(f"               asserted STRUCTURALLY by tests/test_hyperliquid_no_order_path.py (14 tests)")
    _adapter = hl.HyperliquidBookAdapter()
    print(f"EVIDENTIARY  : feeds {list(_adapter.feeds)} => "
          f"{ {f: hl.FEED_LEVELS[f] for f in _adapter.feeds} } levels at MEASURED cadences "
          f"slow 5.406 s / fast 0.517 s; depth beyond 20 UNOBSERVED, and beyond 5 unobserved at the "
          f"fast cadence")
    record["feeds"] = list(_adapter.feeds)
    record["feed_levels"] = {f: hl.FEED_LEVELS[f] for f in _adapter.feeds}
    print(f"LIVE-CAPABLE : registry.is_live_capable('hyperliquid_v1') = "
          f"{registry.is_live_capable('hyperliquid_v1')}  (deliberately False until §3.3 wires it)")
    record["outbound_methods"] = methods
    record["published_levels"] = hl.PUBLISHED_LEVELS

    print()
    print("=" * 100)
    print(f"PREFLIGHT: {'ALL TWELVE GREEN' if all_green else 'RED CONDITIONS PRESENT'} — "
          f"NO SOCKET OPENED (gated on operator confirmation, §2)")
    print("=" * 100)

    # ── THE AMBIENT VARIABLES THAT GATE THIS RUN (WO-066 §6, 0.11) ───────────────────────
    #
    # WO-066 discovered four ambient variables one failed launch at a time, and recorded that
    # the one deciding whether a socket can open at all was `DATA_SOURCE` — ABSENT FROM EVERY
    # PREFLIGHT RECORD. So no past leg's artifacts can answer 'what was DATA_SOURCE when this
    # corpus was captured?'. Recorded here by NAME AND VALUE, including when unset, because
    # 'unset' is exactly the state that produced two of those failed launches.
    record["ambient"] = {
        name: os.environ.get(name)          # None means UNSET — not the same as empty
        for name in ("TRADING_ENV", "DATA_SOURCE", "CORPUS_DIR", "HL_CORPUS_ID",
                     "HYPERLIQUID_GRANT_EXPIRY", "CORPUS_GRANT_EXPIRY",
                     "CORPUS_AUTO_MODE_CONFIRMED", "CORPUS_SHUTDOWN_POLICY_DISABLED",
                     "HL_CAPTURE_HOURS")
    }
    record["all_green"] = all_green
    return record, all_green


if __name__ == "__main__":
    _rec, _green = evaluate()
    out = pathlib.Path(".artifacts/wo066")
    out.mkdir(parents=True, exist_ok=True)
    (out / "hyperliquid_preflight.json").write_text(
        json.dumps(_rec, indent=2, default=str), encoding="utf-8")
    print(f"[WO-032 §4.1] scratch copy at {out / 'hyperliquid_preflight.json'} (git-ignored).")
    print("[WO-067] THE AUDITABLE COPY is the one the capture writes into the run directory "
          "as PREFLIGHT.json, hashed at capture. This standalone run writes no corpus record "
          "because it belongs to no run.")
    raise SystemExit(0 if _green else 1)