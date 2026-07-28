# WO-037 §3 — the reason-code vocabulary, enumerated and classified at HEAD

Derived at HEAD `256c936` (the §2 closures commit). **Read-only enumeration.** Instrument:
`tools/wo037_vocabulary_audit.py`, which **reuses the operated scanners** from
`tests/test_reason_code_vocabulary.py` rather than re-implementing them — a second scanner would be a
second source of truth waiting to diverge.

## §3.4 VERDICT — **ARCHIVE-READY: YES.** §4 is certify-only.

The set of codes that can appear in a corpus-archived decision record is **complete** (every one is
declared) and **consistent** (no emitted-undeclared, no aliases, no prefix collisions). No production
change is warranted.

**One finding is reported alongside** — a latent hazard, not a live defect: see §3.5.

---

## §3.1 The declared set — 44 reason codes, 13 event types

**Reason codes** (`VALID_REASON_CODES`, `logkit/decision.py`), by layer:

- **DATA (28):** `CHECKSUM_INPUT_SYNTHESIZED_NOTATION` · `CHECKSUM_RESYNC` ·
  `CHECKSUM_WIRE_STRING_MISSING` · `CLOCK_INJECTION_REFUSED` · `DATA_RECEIVED` ·
  `FAILURE_CAPTURE_CAPPED` · `FEED_CONNECTED` · `FEED_CONNECTION_CLOSED` · `FEED_CONNECTION_ERROR` ·
  `FEED_MALFORMED_PAYLOAD` · `FEED_UNEXPECTED_PAYLOAD` · `GAP_LEDGER_INCOMPLETE` ·
  `GAP_PERSIST_UNCONFIGURED` · `HEARTBEAT_ABSENCE` · `HOST_SUSPEND` · `INSTRUMENTS_GAPPY` ·
  `LIVE_CAPABLE_BUILDER_MISSING_FORWARDED_PARAM` · `LIVE_CAPTURE_ENV_REFUSED` ·
  `LIVE_CAPTURE_UNSUPPORTED` · `MEAN_CYCLE_BASELINE_HOST_MISMATCH` ·
  `MEAN_CYCLE_BASELINE_INSTRUMENT_MISMATCH` · `PAUSE_ON_BOOK_UNAVAILABLE` ·
  `RECONNECT_CIRCUIT_BREAKER_TRIPPED` · `RECONNECT_FLAG_STRANDED` · `VENUE_CONNECTION_CLOSED`
- **COST_MODEL (1):** `ABNORMAL_SPREAD_REJECT`
- **RISK (9):** `PASS` · `CLAMP` · `VETO` · `KILL_SWITCH_ENGAGED` · `RISK_PASS` ·
  `RISK_CLAMP_MAX_POSITION` · `RISK_VETO_KILL_SWITCH` · `RISK_VETO_DAILY_LOSS` ·
  `RISK_VETO_INVALID_INPUT`
- **STRATEGY (3):** `NO_SIGNAL` · `LONG_SIGNAL` · `SHORT_SIGNAL`
- **EXECUTION (7):** `ORDER_FILLED` · `ORDER_REJECTED` · `EXEC_ORDER_FILLED` ·
  `EXEC_NO_MARKET_STATE` · `EXEC_MARKET_STATE_TIMESTAMP_MISSING` · `EXEC_STALE_MARKET_STATE`

**Event types** (`VALID_EVENT_TYPES`): FEED `feed_connected`, `feed_disconnected`, `feed_error`,
`payload_error` (lowercase, a declared §6 casing finding) · LOOP `FEED_PAUSED`,
`MARKET_DATA_RECEIVED`, `NO_SIGNAL`, `SIGNAL_GENERATED`, `ORDER_FILLED`, `ORDER_REJECTED` ·
RISK `PASS`, `CLAMP`, `VETO` (mechanically pinned to the `RiskDecision` enum).

## §3.2 The emitted set

Enumerated by the operated scanners over `src/` in all three literal forms (`"CODE:"`,
`reason_code="CODE"`, `event_type="CODE"`), with call sites, in the instrument's `.artifacts/` output.

## §3.3 The four properties — MEASURED

| Property | Result |
|---|---|
| **(a) EMITTED ⇒ DECLARED** — reason codes | **CLEAN** — no violation |
| **(a) EMITTED ⇒ DECLARED** — event types | **CLEAN** — no violation |
| **(b) DECLARED ⇒ PRODUCIBLE** — reason codes | **CLEAN** — every declared code has a producer |
| **(b) DECLARED ⇒ PRODUCIBLE** — event types | **CLEAN** |
| **(c) NO DUPLICATE / ALIASED codes** (prefix-freedom across the union) | **CLEAN** — no collisions |

These three are already enforced continuously by `tests/test_reason_code_vocabulary.py`; this
enumeration re-measures them rather than inheriting the guard's green.

### (d) CATEGORY — how each declared code reaches the world

The corpus archives **decision records**. So the archive-relevant question is not "is this code
declared" in general but "can it appear as `reason_code` in a `log_decision` / `log_feed_event`
record". Classified:

| Category | Meaning | Count |
|---|---|---|
| **ARCHIVABLE** | reaches a decision record — CAN appear in the corpus | **19** |
| **RAISED / LOGGED only** | carried in an exception message or a logger line; never a decision record's `reason_code` | 25 |

**The ARCHIVABLE set (19)** — the codes a corpus analysis can actually encounter:

`DATA_RECEIVED` · `EXEC_ORDER_FILLED` · `FEED_CONNECTED` · `FEED_CONNECTION_CLOSED` ·
`FEED_CONNECTION_ERROR` · `FEED_MALFORMED_PAYLOAD` · `FEED_UNEXPECTED_PAYLOAD` · `NO_SIGNAL` ·
`PAUSE_ON_BOOK_UNAVAILABLE` · `LONG_SIGNAL` · `SHORT_SIGNAL` · `KILL_SWITCH_ENGAGED` ·
`RISK_PASS` · `RISK_CLAMP_MAX_POSITION` · `RISK_VETO_KILL_SWITCH` · `RISK_VETO_DAILY_LOSS` ·
`RISK_VETO_INVALID_INPUT`, plus the literal feed/loop codes above.

**Every one is declared. No archivable code is emitted-undeclared, and the archivable set is
prefix-free.**

**The LOAD-TIME code, labelled:** `LIVE_CAPABLE_BUILDER_MISSING_FORWARDED_PARAM` is raised at
**import time** by `register(live_capture=True)`. It is structurally incapable of appearing in a
decision log — there is no decision loop yet when it fires. Its presence in the scanned set does
**not** affect the (a) or (b) verdicts: it is producible (the registration guard raises it) and
declared, so it satisfies both properties on its own terms and masks nothing. **Its label is
`RAISED`, recorded here.** Several other codes are likewise pre-loop refusals
(`LIVE_CAPTURE_ENV_REFUSED`, `LIVE_CAPTURE_UNSUPPORTED`, `GAP_PERSIST_UNCONFIGURED`,
`MEAN_CYCLE_BASELINE_*`, `CLOCK_INJECTION_REFUSED`) — all `RAISED`, none archivable, none masking a
gap. Re-homing them is the **post-corpus SPLIT audit's** job (D42/D37); this WO only labels.

## §3.5 THE FINDING — a latent hazard on the indirection path

**`REASON_VETO_INSUFFICIENT_BALANCE = "RISK_VETO_INSUFFICIENT_BALANCE"` (`risk/engine.py:42`) is
neither declared nor producible.** It appears **exactly once in the entire repository** — at its own
definition. No test references it; `check()` never returns it.

Why both existing properties are structurally blind to it:

- **(a) emitted ⇒ declared** never sees it, because it is not *emitted*. It is a class constant, not a
  `reason_code="…"` literal at a call site.
- **(b) declared ⇒ producible** never sees it, because it is not *declared*.

A code that is **neither declared nor emitted falls between both properties.** That is a third
category the existing guard was not built to cover.

**Why it matters despite being dead.** Three production sites emit `reason_code` **indirectly**, and
all three land in decision records — i.e. in the archive:

| Site | Source |
|---|---|
| `live.py:227` `reason_code=signal_reason` | `"LONG_SIGNAL"` / `"SHORT_SIGNAL"` (`live.py:223`) |
| `live.py:248` `reason_code=reason_code` | the risk engine's `REASON_*` constants |
| `live.py:307` `reason_code=e.reason_code` | `KillSwitchEngagedError.reason_code` (`interface.py:26`) |

`test_reason_code_vocabulary.py`'s own docstring names this as its blind spot:

> *"reason_code=<var>: the risk REASON_* constants, signal_reason, e.reason_code"*
> *"WHAT THE UNCAUGHT CASE LOOKS LIKE: a future emission adds `reason_code=new_var` … the code ships
> as a GOVERNED SYSTEM EMITTING AN UNGOVERNED CODE"*

`REASON_VETO_INSUFFICIENT_BALANCE` is that scenario **pre-loaded**: one line of wiring inside
`check()` and an undeclared code flows into a permanent archive, with every existing guard green.

**Bucket:** this is **not** an archive-readiness violation (nothing produces it, so nothing can reach
the corpus), and **not** a category leak (it is not a load-time code mixed into runtime). It is a
dead-and-ungoverned constant. Per §4 the YES branch forbids a `src/` change, and the constant harms
nothing today, so **it was not touched.** Whether to declare it or delete it is the lead's call.

**What WAS done about it:** `tests/test_archive_readiness.py` (§4) pins it by name in
`KNOWN_DEAD_RISK_CONSTANTS` with the reasoning, and
`test_every_wired_risk_reason_constant_is_declared` **fails the moment it is wired** — converting a
silent future defect into a CI failure at the exact commit that would introduce it.
