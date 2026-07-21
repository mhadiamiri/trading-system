# WO-015 — FINAL REPORT (live-capture runner + HOST_SUSPEND cause + Ops decision-log)

**Status:** COMPLETE. STOP for review. **Opens NO socket** (build only).
**Baseline:** `989600b` (WO-014c-3 addendum; 177 passed both orders). **Authority:** constitution.md.
**Venue connection:** NO — every test/bite proof drives simulated transport (websockets.connect patched).

---

## What was built

### 1. The live-capture runner — `src/trading/loop/live_capture.py`
The entrypoint the re-run assumed but that never existed. `LiveCaptureRunner` DRIVES the
INSTRUMENTED transport `get_live_market_data` (the factory path drove only `get_market_data` —
fixtures) end-to-end through Data→Strategy→Risk→Execution(paper), **wiring the existing instruments**
(gap ledger, failure capture, host-suspend detection, lag/pong/throughput — all already inside
`get_live_market_data`) rather than reimplementing them. The paper loop is reused via a minimal,
backward-compatible `feed=` override on `LiveTradingLoop.run()` (unchanged when `feed is None`; all
16 existing live-loop tests still pass).

**BOUNDARY (Principle IV/VII, import-linter-enforced).** The runner lives in `trading.loop`, which
MUST NOT import a concrete adapter (contracts "Forbid loop from importing adapters directly" /
"Registry is the sole adapter resolution path"). So it resolves the LIVE adapter through the
FACTORY: a new `factory.create_live_capture_feed(persist_path, duration)` calls
`registry.create("kraken_v2", mode="live", gap_persist_path=…)` (the registry builder now accepts a
mode + persist path), returning `(adapter, live_feed_iterator)`. It resolves the v2 **book** adapter
explicitly — the instrumented live transport exists only there, so a live capture is that adapter by
definition (this also avoids passing a live-only kwarg to a non-live builder, which an order-shuffled
test caught). The runner treats the adapter as a
duck-typed object — no concrete-adapter import. Contracts stay **6 kept / 0 broken** (the first cut
broke two; the boundary was respected, not weakened — rule 0.4). Tests inject an adapter directly
(tests are exempt); a separate test exercises the production factory-resolution path.

**Preflight enforcement lives IN the runner** (checklist-enforced rules are 0-for-N here):
- **Refuses a non-paper `TRADING_ENV`** (`LIVE_CAPTURE_ENV_REFUSED`) — the order-capable path must
  be unreachable and no live capture may risk a real order.
- **Refuses an unconfigured persistence path** (`GAP_PERSIST_UNCONFIGURED`) — before any component
  is built; the adapter is the second line of the same refusal.
It measures the **per-minute MarketStates-EMITTED series** (§2.2's re-run deliverable) at the yield
boundary, and returns the gap ledger, failure captures/summaries/count, and diagnostic counters.

**Honest limit (0.1f):** opening a REAL socket is production only. This runner has never held a
real venue socket — that is the re-run's job, under the per-run authorization, on a non-suspending
host. Stated in the module docstring.

### 2. HOST_SUSPEND — the ruled fifth gap-ledger cause (addendum A)
Added to `GAP_CAUSES`; reason code `HOST_SUSPEND` declared in `decision.py` **in the same commit**.
Detection: each transport-loop iteration compares its WALL delta against its MONOTONIC delta; a
divergence beyond the declared drift bound (`HOST_SUSPEND_DIVERGENCE_SECONDS = 43.0`, the WO-014c-3
§0.3 worst-case whole-run drift — a per-iteration jump beyond it cannot be drift) is a host suspend.
**Role is DIAGNOSTIC** (record a HOST_SUSPEND gap, report LOUDLY, do **not** terminate) — the corpus
WO makes it window-invalidating. Without it a mid-capture suspend masquerades as catastrophic
starvation, a wrong verdict at the discrimination layer.

**Does HOST_SUSPEND fit the existing GapRecord schema unchanged? YES — say so, no STOP.** It uses
`cause`/`reason_code`/`open_monotonic`/`close_monotonic`/`resumed`/`terminal`/`detail` exactly as the
other causes; the divergence magnitude rides in `detail`. A structured `divergence_s` field is the
**corpus WO's** call, when the role turns from diagnostic to window-invalidating. No new field, no STOP.

### 3. Ops decision-log entry (addendum B)
`docs/decisions/2026-07-21-orders-that-operate-what-they-should-build.md` — "orders written to
OPERATE a thing the order was implicitly supposed to BUILD" (WO-008b, WO-014 §1, the re-run's runner),
with the ruled checklist item: every future order that operates anything states where it was built and
verified, or declares itself the builder.

## Bite proofs — 4 artifacts each, sha256 exact-restore (simulated transport)
| Guard | Real FAIL when weakened | Evidence |
|---|---|---|
| HOST_SUSPEND detection | divergence check disabled → no suspend gap recorded | `evidence/WO-015/bite_host_suspend_detection.txt` |
| runner refuse non-paper | env check disabled → capture would run outside paper | `evidence/WO-015/bite_runner_refuse_non_paper.txt` |
| runner refuse no-persistence | check disabled → silently-unpersisted capture would run | `evidence/WO-015/bite_runner_refuse_no_persistence.txt` |

## Verification
- Both orders: `pytest tests/ -p no:randomly -rX` and `--randomly-seed=20260725 -rX` — 186 passed,
  0 failed / 0 xfailed / 0 xpassed. **Delta vs `989600b` (177 → 186, +9):** `test_host_suspend.py`
  (3) + `test_live_capture.py` (6). No existing test changed outcome; the `LiveTradingLoop.run()`
  `feed=` addition is backward-compatible (16 live-loop tests green).
- import-linter **6 kept / 0 broken**, contract 6/6, ruff clean. New reason codes `HOST_SUSPEND`
  and `LIVE_CAPTURE_ENV_REFUSED` declared in the same commit; vocabulary guard green. HEADs at push.

## Answers
- **Venue connection?** NO. WO-015 opens no socket. **HTTPS doc fetch?** NO.
- **Prose standing in for output?** NO — bite proofs, pasted suite summaries, decision docs.
- **Changed but not asked?** All in service of the runner, disclosed: `instructions.md` (the WO-015
  text, committed with its WO); `src/trading/loop/live.py` (backward-compatible `feed=` override);
  `src/trading/data/adapters/factory.py` (`create_live_capture_feed` — the sanctioned resolution
  path); the `_build_kraken_v2` registry builder (now accepts `mode`/`gap_persist_path`);
  `src/trading/logkit/decision.py` (`HOST_SUSPEND` + `LIVE_CAPTURE_ENV_REFUSED`);
  `src/trading/data/adapters/kraken_v2_book.py` (HOST_SUSPEND cause + detection). Nothing else.
- **Authorization (addendum C, no action):** noted — the first real venue socket is authorized
  PER-RUN, effective when WO-015 clears review; WO-015 itself opens none.
- **What could not be completed?** Nothing in WO-015. The re-run remains a separate WO for a fresh
  session on a non-suspending host (sleep is now set to 2h, per Hadi).

**STOP for review.** Do not open the socket here.
