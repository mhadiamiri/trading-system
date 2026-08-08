# WO-054 §6 — PHASE B PRECONDITION CHECKLIST

**The grant is issued against this document.** D24: authorization is **per-run and
non-inheriting** — nothing below is carried over from WO-041/WO-044 without fresh verification.

Verified at HEAD `c4f40b9` + this WO's build, on **2026-08-08**.
**NO SOCKET WAS OPENED TO PRODUCE THIS DOCUMENT.** Every check is static or fixture-based.

---

## SUMMARY

| # | Term | Status |
|---|---|---|
| 1 | Host-suspend verification | 🟢 GREEN |
| 2 | Capture-loop baseline fingerprint-matched to the host | 🔴 **RED — blocking** |
| 3 | Checksum machinery green at HEAD | 🟢 GREEN |
| 4 | Gap-ledger integrity end-to-end | 🟢 GREEN |
| 5 | Disk budget + rotation | 🟡 **AMBER — green for disk, needs a retention ruling** |
| 6 | Paper-env + no-credential preflight | 🟢 GREEN |
| 7 | TRADING_ENV guard + kill-switch bite proofs | 🟢 GREEN |
| **8** | **Regime recording armed** (NEW — D53 ruling 1) | 🟢 GREEN |

**GO/NO-GO: 🔴 NO-GO on term 2 as it stands.** One blocking item, one needing a ruling. Neither is
a code defect; both are host/operator conditions, which is precisely what a non-inheriting checklist
exists to surface.

---

## TERM 1 — HOST-SUSPEND VERIFICATION (D24 red line d) — 🟢 GREEN

`HOST_SUSPEND` is present in the ruled `GAP_CAUSES` set and the detector's drift bound
(`HOST_SUSPEND_DIVERGENCE_SECONDS`) is a live constant on the adapter. The wall-vs-monotonic
divergence detector is exercised by the suite at HEAD.

**Falsifier (0.12):** the constant could have been absent from the class, or `HOST_SUSPEND` absent
from `GAP_CAUSES` — both were checked by attribute lookup, not by reading a prior report. A capture
on a host that sleeps without this armed would record the suspend as a venue problem (the
misattribution family).

## TERM 2 — CAPTURE-LOOP BASELINE FINGERPRINT-MATCHED TO THE HOST — 🔴 RED, BLOCKING

**Fresh measurement, 2026-08-08:**

| | at the WO-044 capture | **now** |
|---|---:|---:|
| host | Hadi / Windows 11 | Hadi / Windows 11 ✔ |
| interpreter | 3.14.6 | 3.14.6 ✔ |
| CPU load | 1.0% | 4.1% |
| **free memory** | **12.33 GB** | **3.26 GB** |

> ⚠ **RETIRED FIGURE — 2026-08-08 (WO-058 §2.1, D58 ruling 1, D47 form).** The `12.33 GB` above is **memory USED, misread as memory FREE**. `LoadRecord.capture()` computed it as `psutil.virtual_memory().used`. On this host (total 15.715 GiB) the WO-044 capture actually ran with **~3.381 GiB FREE** — *less* than the readings this table calls RED.
> **Consequence: an unreachable gate demanding ~3.6× more headroom than the reference capture itself ever had, blocking a capture the host was always able to run.**
> Superseded by the flow gate in `src/trading/data/capture_gate.py`. See `docs/decisions/2026-08-08-a-number-wrong-in-a-way-that-survives-being-questioned.md`. This annotates; the report is not rewritten.


**The host is not in the state the recorded baseline was taken in.** Free memory is down by ~9 GB —
a 3.8× reduction.

**Why this blocks, and it is not pedantry.** D46 is the ruling that unbounded retention →
memory pressure → swap → event-loop starvation → `HEARTBEAT_ABSENCE`, i.e. **a host problem
recorded as a venue disconnect.** A 30-day capture is exactly the duration over which that
misattribution compounds, and it would silently inflate the gap count that §4's derivation depends
on. The WO-045 retention caps bound *our* contribution to memory pressure; they do nothing about
9 GB consumed by something else on the box.

**Required before the grant:** the operator returns the host to a comparable state (or declares the
new state and re-establishes the baseline against it with
`tools/establish_mean_cycle_baseline.py` / `tools/capture_loop_baseline.py`). **This is an operator
action, not a code change.**

**Falsifier:** had free memory read ≥ ~12 GB and CPU ~1%, this term would be GREEN. It was measured
this session with `psutil`, not inherited from the WO-044 preflight — which is exactly the
inheritance §6 forbids, and it is what surfaced the difference.

## TERM 3 — CHECKSUM MACHINERY GREEN AT HEAD — 🟢 GREEN

CRC32 validation (FR-018a(d)) and the resync path are green in the full suite at HEAD, both
interpreters, both orders. An unvalidated book emits nothing, so this is the guarantee that every
captured frame was checksum-verified.

## TERM 4 — GAP-LEDGER INTEGRITY END-TO-END — 🟢 GREEN

The ruled five-cause taxonomy is intact and armed. **WO-054 did not extend it** — see §2.4: a
trade-channel outage is recorded in a *separate* availability ledger, because a gap is defined as
an interval with no validated `MarketState` and during a trade outage the book keeps emitting.
Recording one would subtract book coverage that was never lost.

New in this WO and armed: the `TradeChannelOutage` ledger with two declared, producible,
prefix-free causes.

## TERM 5 — DISK BUDGET + ROTATION — 🟡 AMBER

**Disk is ample. The retention policy needs a ruling.**

| | measured |
|---|---:|
| free disk | **858.1 GB** of 1,021.8 GB |
| compressed, with trade channel | **0.53 GB** for 720 covered hours |
| **raw `.jsonl`, if retained** | **~17.4 GB** for 720 covered hours |

Rotation is hourly with compression enabled and a 90-day retention, loaded and proven.

**The ruling needed:** `corpus_20260805` currently retains **both** the raw `.jsonl` (673 MB) **and**
the `.jsonl.gz` (24 MB) for every closed segment — a 27.7:1 duplication. At 30 days that is 17.4 GB
of redundant raw against 0.53 GB of compressed. 858 GB free absorbs it comfortably, so this is not
a capacity risk; it is a question of whether the duplication is deliberate (e.g. raw kept for
forensic replay) or an artifact. **Not changed unilaterally — deleting raw capture data is exactly
the kind of irreversible act that needs the operator's word.**

## TERM 6 — PAPER-ENV + NO-CREDENTIAL PREFLIGHT — 🟢 GREEN

`TRADING_ENV=paper`, verified fresh from `config.settings` this session. The public book and trade
channels are unauthenticated — no key, no token, no auth — so the grant boundary (public feed,
read-only, no order path) is structural for both channels, not merely configured.

## TERM 7 — TRADING_ENV GUARD + KILL-SWITCH BITE PROOFS — 🟢 GREEN

Both green in the full suite at HEAD. `RISK_VETO_KILL_SWITCH` vetoes, and the `TRADING_ENV` guard
refuses mainnet.

## TERM 8 — REGIME RECORDING ARMED (NEW — D53 ruling 1) — 🟢 GREEN

The eighth scope dimension. `src/trading/data/regime.py` is committed, under test (12 tests), and
bite-proved (a hard-coded summary fails the quiet-vs-volatile discrimination). It computes a
percentile distribution of absolute returns at 1/5/15/60-minute horizons with counts against the
cited cost thresholds, and carries its own `not_supported` list so a reader cannot over-read it.

Applied retroactively to `corpus_20260805` in
`docs/decisions/2026-08-08-corpus-20260805-regime.md`: **QUIET**.

**Falsifier:** a summary that ignored its input would produce identical output for a quiet and a
volatile path. Artifact 3 of the §3.4 bite proof constructs exactly that mutation and it fails.

---

## THE GRANT'S SHAPE — PROPOSED, FOR THE LEAD TO RULE

**Not assumed.** D24 makes every socket authorization per-run and non-inheriting, so both of the
following are the lead's to grant.

### PROPOSAL A — a short live validation run BEFORE the long capture

**Ops's read, and mine: yes.** The trade-channel merge has been validated against **fixtures only**
— no socket has been opened. Fixtures prove the merge logic; they cannot prove that Kraken's live
trade channel behaves as the published spec describes, that the subscribe is acked on the same
socket as the book subscription, or that message ordering between the two channels is what the
merge assumes. **Discovering a broken merge at week two of a 30-day capture is far worse than
spending one short grant now.**

| | proposed |
|---|---|
| **Duration** | **2 hours** of covered time |
| **Why 2 hours** | Long enough to cross at least one hourly segment rotation and, at the observed 0.515 gaps/covered-hour, to encounter ~1 reconnect — so both the rotation path and the gap path are exercised live, not just the happy path. Short enough that nothing is lost if it fails. |
| **Scope** | `DATA_SOURCE=kraken_v2`, `TRADING_ENV=paper`, BTC/USD, book **and** trade channels, no order path |
| **Product** | a throwaway validation corpus — **not** phase B data, not to be merged into the long capture |

**Abort conditions — any one aborts the run and blocks the long capture:**

1. the trade subscribe is not acked within `SUBSCRIBE_ACK_TIMEOUT_SECONDS` (10 s);
2. any frame is written with `observable: true` and a **fabricated** `last_price` (i.e. a non-null
   price on a zero-count interval) — the D48 substitution reaching production;
3. a trade arrives while the channel is recorded unobservable (the ledger/frames contradiction —
   already a hard refusal in code, so this would surface as a raised error);
4. the trade channel's message rate drives the WO-045 retention caps to trim more than once per
   segment, indicating the caps were sized for a book-only feed;
5. any `GapRecord` is written with a trade-channel cause (would mean §2.4's separation failed);
6. book-frame throughput drops materially below the recorded baseline, indicating the second
   channel is starving the book loop.

**Success criterion:** a corpus whose frames carry non-null `count`/`volume` on intervals with
trades, `count: 0` with `last_price: null` on quiet intervals, and an availability ledger that is
either empty or populated with declared causes only.

### PROPOSAL B — the long capture

| | proposed |
|---|---|
| **Target** | see the §4 finding below — **the naive 720-hour target is unreachable and needs a ruling first** |
| **Mechanism** | resumable corpus under one corpus-id, seams declared per D45 |
| **Env** | `DATA_SOURCE=kraken_v2` explicit, `TRADING_ENV=paper`, detached |
| **Expected shape at 720 covered hours** | ~39 runs, ~20 seams, ~371 in-run gaps, ~0.53 GB compressed |
| **Grant expiry** | to be declared by the lead; the WO-044 anchor (2026-08-19) has **13 days** left, which does not cover a 30-day capture — **a new expiry must be issued** |

### ⚠ THE RULING PROPOSAL B DEPENDS ON

WO-054 §4 found that **a 24-hour horizon cannot be evaluated at any capture length under the
current segmentation rule.** The longest continuous segment ever observed is 7.73 hours; mean 1.76;
zero segments reach 12 h. Capturing 30 days yields ~410 more segments of the same length, not
longer ones.

**The lead must rule on the horizon ceiling before the long capture's target can be set** — see the
WO-054 report §4 for the three options and their costs. Setting a 720-hour target now would commit
30 days of capture to a horizon the machinery cannot evaluate.
