# WO-055 — LIVE VALIDATION RUN: **NOT LAUNCHED**

> # ⛔ THE SOCKET WAS NOT OPENED. TWO INDEPENDENT BLOCKERS.
>
> **STOP 1 — TERM 2 (the named gate, §1.1).** Free memory **3.01 GB** against the WO-044 reference of
> **12.33 GB**, and **swap is already in use (0.96 GB)**. Memory pressure is not hypothetical here;
> it is present before the capture process starts. §1.1 says stop, so I stopped.
>
> **STOP 2 — THE TRADE CHANNEL IS NOT WIRED INTO THE CAPTURE PATH.** This is mine, from WO-054.
> `trade_channel.py` is a library validated against fixtures; **nothing calls it from
> `live_corpus_capture.py`, and the adapter discards every non-`book` message.** The run would have
> produced a **book-only corpus**, and **every one of §3.1–3.8 would have been unestablishable** —
> with §3.5 returning a **false green**.
>
> **The grant was not spent.** Per 0.13 an abort is a successful outcome; a pre-flight abort that
> costs no grant is the cheapest version of it.

**No code was changed.** SHIP IMPACT: none. `corpus_20260805` untouched — v1 `e3ab1aec…`, 88 files,
38/38 capture hashes verified at open and close.

---

## §1.1 TERM 2 — THE HARD GATE: 🔴 **RED**

Measured now, on this host, this session:

| | WO-044 capture | WO-054 | **now (2026-08-08)** |
|---|---:|---:|---:|
| free memory | **12.33 GB** | 3.26 GB | **3.01 GB** |
| memory used | — | — | **82.2%** |
| **swap in use** | — | — | **0.96 GB (8.1%)** |
| idle CPU load | 1.0% | 4.1% | 1.64% |
| total RAM | — | — | 16.87 GB |

**Verdict: the gate fails.** Free memory has not been restored — it is **0.25 GB lower** than the
figure that made WO-054 RED. CPU load has recovered (1.64%, essentially the reference), which
isolates the problem cleanly to memory.

**The decisive observation is the swap, not the headline number.** D46's chain is *memory pressure
→ swap → event-loop starvation → `HEARTBEAT_ABSENCE`* — a host problem wearing a venue cause code.
§1.1 asks whether free memory is at a level that makes that chain **implausible**. It cannot be
implausible when the machine is **already paging at idle**, before a capture process with a 64 MiB
retention buffer and a two-channel message rate is added. The first link of the chain is not a risk
here; it is the current state.

**Falsifier (0.12):** had this measured ≥ ~12 GB free with swap at 0, Term 2 would be GREEN and the
socket would have opened. The number came from `psutil` this session, not from WO-054's report —
which is the non-inheriting re-verification that caught it in the first place.

**Actionable for the operator** — top consumers, aggregated:

```
chrome.exe          6.16 GB      MemCompression   0.95 GB
svchost.exe         1.80 GB      Code.exe         0.91 GB
Wispr Flow.exe      1.18 GB      claude.exe       0.53 GB
```

**~9.31 GB must be freed to match the WO-044 reference.** Chrome alone is 6.16 GB. This is an
operator action, not a code change.

---

## §1 STATE, AND THE REMAINING SEVEN TERMS — re-verified fresh, not inherited

HEAD `a06784b` (WO-054 close, CI 31235288242, 509/2). `git diff -- src/` clean.

| # | Term | Status | Evidence, measured this session |
|---|---|---|---|
| 1 | Host-suspend armed | 🟢 | `HOST_SUSPEND_DIVERGENCE_SECONDS = 43.0`; `HOST_SUSPEND` present in `GAP_CAUSES` |
| **2** | **Host baseline fingerprint** | 🔴 | **above — BLOCKING** |
| 3 | Checksum machinery green at HEAD | 🟢 | `test_checksum_capture_replay` executed, passing |
| 4 | Gap-ledger integrity | 🟢 | `test_outage_policy` + vocabulary guard executed — 54 passed |
| 5 | Disk budget + rotation | 🟢 | **857.9 GB free** of 1,021.8 GB |
| 6 | Paper-env + no-credential | 🟢 | `TRADING_ENV = paper`, read fresh from `config.settings` |
| 7 | TRADING_ENV guard + kill switch | 🟢 | **EXECUTED, not printed** — see below |
| 8 | Regime recording armed | 🟢 | `test_regime.py` 12 tests executed, passing |

### Term 7 — executed, with its dual (the WO-044 §3.7 scar)

WO-044's condition 3.7 was a **hardcoded string for four runs** — a condition that could not go red.
So this one was run, not asserted:

```
kill switch ENGAGED    -> order BLOCKED with KillSwitchEngagedError   (the guard fired)
kill switch DISENGAGED -> order FILLED  qty=0.1  price=64001.0        (the DUAL)
```

The dual matters: a client that refused *every* order would satisfy the first line and be broken.
**Falsifier:** had the engaged call returned a fill, or the disengaged call raised, Term 7 is RED.

---

## §1.3 THE SIX ABORT CONDITIONS — restated verbatim, with detectors and falsifiers

From `evidence/WO-054/phase_b_preconditions.md`. §1.3 warns that *an abort condition that cannot
fire is a checklist, and this project has that scar*. **Auditing them is what surfaced STOP 2.**

| # | Condition (verbatim) | Detector | Would it fire? |
|---|---|---|---|
| 1 | *"the trade subscribe is not acked within `SUBSCRIBE_ACK_TIMEOUT_SECONDS` (10 s)"* | none — **no trade subscribe is ever sent** | 🔴 **CANNOT FIRE** |
| 2 | *"any frame is written with `observable: true` and a **fabricated** `last_price`"* | none — **no corpus scanner exists, and no frame carries `last_price` at all** | 🔴 **CANNOT FIRE — and returns a FALSE GREEN** |
| 3 | *"a trade arrives while the channel is recorded unobservable"* | `TradeMerger.observe()` raises `TRADE_CHANNEL_CAUSE_UNDECLARED` — **real, tested** | 🟡 armed in the library, **unreachable in capture** |
| 4 | *"the trade channel's message rate drives the WO-045 retention caps to trim more than once per segment"* | caps exist (`50_000` frames / `64 MiB`, precedence FLOOR > BYTE > COUNT) but **no per-segment trim counter is emitted** | 🔴 **NOT MEASURABLE as written** |
| 5 | *"any `GapRecord` is written with a trade-channel cause"* | `GapRecord` rejects undeclared causes; trade causes are in a separate set | 🟢 **would fire** |
| 6 | *"book-frame throughput drops materially below the recorded baseline"* | `capture_loop_baseline` / `mean_cycle` instruments exist | 🟢 would fire |

### Condition 2 is the one §1.3 singles out, and it is the worst case

> A scan of a book-only corpus for *frames with `observable: true` and an unbacked `last_price`*
> returns **zero** — because no frame has an `observable` field, or a `last_price`, at all.

That zero would have been reported as "**§3.5 PASS — zero fabricated prices**". It is precisely the
specimen this project ratified two work orders ago in
`docs/decisions/2026-08-08-an-empty-result-from-a-query-that-cannot-fail.md`:

> **An empty result from a query that cannot fail is not evidence.**

Rule 0.12 — *state what would have falsified it* — is what caught it. The falsifier for "no
fabricated prices were found" is *a frame that has a `last_price` field to be wrong about*. There
are none. The query could not speak.

---

## STOP 2 — THE TRADE CHANNEL IS NOT WIRED INTO THE CAPTURE PATH

**This is a gap in my own WO-054 delivery, and I am stating it plainly.** WO-054 §2.2 said *"Merge
trade events into the capture so a frame can carry `last_price`, `total_volume`, `trade_count`."* I
built the merge component, the schema, the availability ledger, the tests and the bite proof — and
**did not connect any of it to `live_corpus_capture.py`.** WO-054's acceptance line read "trade
channel built and fixture-validated", which was true and is why it passed; the capture integration
was in scope and I neither delivered nor flagged it.

**Verified four independent ways, not inferred from one grep:**

1. `tools/live_corpus_capture.py` imports nothing from `trading.data.trade_channel` — full import
   list checked.
2. `kraken_v2_book.py` contains **zero** occurrences of `"trade"` as a channel name.
3. The adapter's parser discards it explicitly:
   ```python
   if raw_frame.get("channel") != "book":
       return []
   ```
   So even a trade message that arrived would be dropped on the floor.
4. `_build_subscribe_message()` sends the **book** subscription only; nothing sends the trade one.

The frame writer at `live_corpus_capture.py:869` writes exactly
`timestamp, symbol, bid, ask, bid_qty, ask_qty, spread` — **byte-identical in shape to
`corpus_20260805`.**

### What the run would have produced, and what it would have "proved"

| §3 item | Outcome had the socket opened |
|---|---|
| 3.1 live trade channel matches the cited spec | **unestablishable** — no subscription sent |
| 3.2 acked on the same socket as book | **unestablishable** — nothing to ack |
| 3.3 inter-channel ordering | **unestablishable** — one channel |
| 3.4 the three states in live data | **unestablishable** — no `trades` object written |
| 3.5 no fabricated `last_price` | **FALSE GREEN — zero, vacuously** |
| 3.6 retention caps at higher message rate | **unestablishable** — rate unchanged from book-only |
| 3.7 regime summary | achievable (operates on bars, not trades) |
| 3.8 measure the live trade rate | **unestablishable** — no trade messages received |

**Seven of eight unestablishable; one of those a false pass.** Two hours of grant, spent to learn
nothing, and to produce a document asserting the merge had survived contact with Kraken when it had
never been offered to it.

### Why I did not fix it here

§0.13 and the WO's SHIP IMPACT line are explicit: *"NO code change expected — this OPERATES what
WO-054 built. If a fix is needed mid-run, that is an ABORT and a finding, not an inline repair."*
Wiring a second channel through the adapter's read loop, the subscribe/ack path, the reconnect and
resubscribe path, and the frame writer is a **substantial capture-path change** — SHIP IMPACT YES
work with its own bite proofs. Doing it inside a WO scoped to operating existing code, unreviewed
and un-pre-registered, is exactly the discretion §0.1 forbids.

---

## §2 THE RUN — NOT PERFORMED

No socket was opened. No corpus was created. No `validation_YYYYMMDD` id was allocated. The grant
is **unspent** and its 14-day expiry is intact.

## §3 WHAT THE RUN MUST ESTABLISH — NOT ESTABLISHED

None of §3.1–3.8 is answered, and none is claimed. §3.8's live trade rate remains **an assumption**:
WO-054's budget multiplier (×1.50 compressed) still rests on the declared *1 trade per 8 book
frames*, and that assumption is **unchanged and still declared**, not silently promoted to a
measurement.

---

## EVERY ATTEMPT

1. **Measured Term 2 before anything else**, as §1.1 orders — including swap, which is what turned a
   marginal-looking 3.01 GB into an unambiguous RED.
2. **Enumerated the memory consumers** so the operator has an actionable number (9.31 GB, Chrome
   6.16 GB) rather than a verdict.
3. **Audited the six abort conditions for whether they can fire**, per §1.3 — which is what found
   STOP 2. Had I only restated them, the run would have launched under STOP 1's absence alone once
   memory was freed.
4. **Verified STOP 2 four independent ways** before asserting it, rather than trusting a single
   grep — the claim is strong enough to deserve it.
5. **Executed Term 7 rather than printing it**, with its dual, per the WO-044 §3.7 scar.
6. **Did not repair and continue** (0.13). Two blockers, both reported, neither fixed inline.
7. **Did not open the socket.**

---

## §4 ACCEPTANCE

- [x] Term 2 measured and gated — **RED, socket not opened**
- [x] Remaining seven terms re-verified fresh; Term 7 **executed** with its dual
- [x] Six abort conditions restated verbatim with detectors **and** falsifiers — **three cannot
      fire**, which is the finding
- [ ] 2 covered hours captured — **NO. Clean pre-flight abort, named cause, grant unspent** (0.13)
- [ ] §3.1–3.8 answered — **NO, and not claimed**
- [x] `corpus_20260805` untouched — v1 `e3ab1aec…`, 88 files, 38/38 capture hashes, verified at open
      and close
- [x] No throwaway corpus created (none was allocated)
- [x] Gates green; no code changed

---

## WHAT THE LEAD NEEDS TO RULE

1. **Term 2 is an operator action.** ~9.31 GB to free. Until then no capture of any length should
   start — this blocks the long capture too, not just this validation.
2. **A WO is needed to WIRE the trade channel into the capture path** — adapter subscribe/ack,
   reconnect + resubscribe, the read loop's channel demultiplex, the frame writer, and the
   `TradeMerger` lifecycle across segment rotation. SHIP IMPACT YES, with bite proofs.
3. **Abort conditions 1, 2 and 4 need real detectors before any validation run** — in particular a
   committed corpus scanner for condition 2, so that "zero fabricated prices" is a claim a query
   could have contradicted.
4. **WO-055 should be re-issued after (1)–(3)**, against the same grant shape. Nothing about the
   2-hour design or its abort conditions is wrong; the machinery they test simply is not connected
   yet.
