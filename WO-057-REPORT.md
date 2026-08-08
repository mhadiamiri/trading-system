# WO-057 — ABORT-CONDITION DETECTORS (1, 2, 4) + THE RE-SPECIFIED TERM 2 GATE

**NO SOCKET OPENED.** Fixtures only. **SHIP IMPACT: YES** — the capture path emits a new counter and
the preflight gained a gate. Corpus v1 `e3ab1aec…` unchanged, 38/38 capture hashes verify.

> ## ⛔ THE FINDING THAT REFRAMES THREE REPORTS
>
> The Term 2 reference — **"12.33 GB free"** — is not free memory. `LoadRecord.capture()` computes
>
> ```python
> memory_gb = psutil.virtual_memory().used / (1024 ** 3)
> ```
>
> — memory **USED**. WO-054, WO-055 and WO-056 each compared today's *available* memory against the
> WO-044 capture's *used* memory. **Two different quantities.**
>
> On this host (total 15.715 GiB):
>
> | | memory USED | => memory FREE |
> |---|---:|---:|
> | WO-044 capture (banked 12.9 h) | 12.334 GiB | **~3.381 GiB** |
> | reading during this WO | 11.141 GiB | **4.573 GiB** |
>
> **The capture that succeeded ran with LESS free memory than the readings later called RED.** The
> gate was demanding roughly 3.6× more headroom than its own reference run ever had.
>
> The swap observation was independent and stands. The free-memory ground did not.

---

## §1 STATE

HEAD `60fc007` (WO-056 close, CI 31264684723, 525/2). `git diff -- src/` clean. Baseline
**525 passed, 2 skipped**. All gates green; corpus v1 `e3ab1aec…` and 38/38 verified.

Term 2 reading at open: **4.94 GB free · 0.51 GB swap in use · 3.02% idle CPU** (informational).

---

## §2 THE RE-SPECIFIED TERM 2 GATE

Encoded in **`src/trading/data/capture_gate.py`** — committed code in the tree it certifies (D51),
so the figure the report cites and the figure the preflight enforces cannot drift apart.

### §2.1 The footprint, DERIVED

⚠ **§2.1 asks me to base this on "WO-044's *measured* process usage". WO-044 measured no such
thing** — `LoadRecord` records host-wide `virtual_memory().used`, never the capture process's own
RSS. So I measured it, by running the real capture runner over a fixture socket (no network) and
sampling `psutil.Process().memory_info().rss`:

```
bare interpreter                          27.39 MiB
+ every capture import loaded             35.68 MiB
+ a running capture, 3,000 frames         71.92 MiB   <- process baseline
```

At 3,000 frames the retention buffer held ~0.5 MiB — effectively empty. The arithmetic:

```
  process baseline (measured)              71.92 MiB
+ retention buffer at its declared cap     64.00 MiB   MAX_RETAINED_RAW_BYTES
──────────────────────────────────────────────────────
= steady-state ceiling                    135.92 MiB

+ segment-close transient                 ~18.00 MiB   ~17.26 MiB segment (measured, WO-054)
                                                       + gzip destination held at once
──────────────────────────────────────────────────────
= transient peak                          ~154 MiB
× 2  allocator fragmentation, multi-week run
──────────────────────────────────────────────────────
= DERIVED REQUIREMENT                     307.84 MiB
```

**DECLARED FLOOR: 512 MiB** — the next power of two above the derivation. Rounded up and stated as
a declared floor rather than reported as "308 MiB", because a figure resting on a fragmentation
allowance does not deserve three significant figures. The derivation is computed in code, so a
future edit to one component cannot leave the total stale — the failure mode that produced the
number this replaces.

**⚠ THE TRADE CHANNEL ADDS NOTHING TO THIS CEILING, BY CONSTRUCTION.** §2.1 asks for its increment;
the honest answer is *zero*, and the reason matters: the retention buffer is **byte**-capped
(precedence FLOOR > BYTE > COUNT), so a higher message rate does not raise the memory ceiling — it
only makes the cap bind sooner in wall-clock time.

**The trade rate remains an unmeasured ASSUMPTION** (1 trade per 8 book frames, WO-054), carried as
one and **not promoted** (WO-055 §3.8's discipline). It is not needed for the memory figure. It
*is* load-bearing for abort condition 4, where §5 carries it explicitly as an assumption.

### §2.2 "Sustained" — the observation window

**60 seconds, sampled every 2 s, 30 samples. EVERY sample must read zero swap** — not the mean, not
the median.

*Why 60/2:* a single sample is not evidence about swap, because Windows commits and reclaims pages
lazily and an instantaneous read can land in a quiet interval on a host that pages steadily. Most
Windows scheduled tasks and service ticks run on intervals of ≤30 s, so 60 s contains at least one
full period of the commonest idle churn; 2-second sampling gives 30 observations so no single
transient dominates, while staying short enough to be a preflight step.

**Falsifier for the window itself (0.12):** if two consecutive 60-second windows on the same
otherwise-idle host **disagree** — one all-zero, the next not — then 60 s is too short to
characterise this host and must be lengthened. The right response is to re-derive the window, not
to re-run until a green one appears.

### §2.3 The preflight reads it

`tools/live_corpus_capture.py` gained condition **[3.8b]**, which calls `capture_gate.evaluate()`
and records the verdict under `term2_memory_gate`. Verified **by reading the committed code**, not
by intending it — `test_the_preflight_reads_the_gate_rather_than_re_deriving_it` asserts the call
exists, the verdict is recorded, and the superseded `12.33` figure survives nowhere as live code.

**A RED gate blocks.** `test_a_red_gate_makes_the_preflight_refuse` proves it. That test matters
because every other capture test patches the gate green so it can exercise other things — without
it, the gate would be exactly the kind of thing that is patched out everywhere and never checked.

### The gate's verdict on this host, right now

```
green          : false
  swap_green   : false     max swap in use 503.8 MiB  <- RED
  memory_green : TRUE      5,029 MiB free >= 512 MiB floor
```

**Under the corrected gate, Term 2 is RED on swap alone.** The memory half — which three reports
called RED — is green by a factor of ten.

---

## §3 CONDITION 1 — THE TRADE-ACK DEADLINE

**Verified, not assumed** (§3.1): WO-056 built `_check_trade_ack_deadline()`, and this WO drove it.

| | |
|---|---|
| **BITE** | deadline passed with no ack → `TRADE_CHANNEL_SUBSCRIBE_FAILED` in the availability ledger, and **every subsequent frame carries `observable: false`** — the economic effect (0.9), not a log line |
| **DUAL** (§3.3) | an ack arriving in time → ledger empty, `observable: true`, even when checked 999 s later. *A detector that fires on every run is worse than none.* |
| also proven | does not fire before the timeout; records the outage **once** across repeated checks (a ledger that inflates is as unreadable as one that stays empty) |

**Falsifier (§3.4):** this detector would be shown unable to fire if `_trade_ack_deadline` were
never set (no subscribe sent — the WO-055 state), or if the check were never called from the frame
path. Both are asserted: the deadline is armed in `_send_subscriptions`, and the call site is on
the received-frame path.

---

## §4 CONDITION 2 — THE COMMITTED SCANNER (the centrepiece)

**`tools/corpus_fabrication_scan.py`** — committed, because a scanner in a throwaway script
certifies nothing (D51, the rule that retired `a025db1e…`).

### §4.2 Three outcomes, and the first two are never conflated

| outcome | meaning | exit |
|---|---|---|
| **(a) NOT_APPLICABLE** | no frame carries `trades.observable` — **the question cannot be asked** | `3` |
| **(b) CLEAN** | the fields exist, N frames examined, zero violations | `0` |
| **(c) VIOLATIONS** | n frames **named**, with identities | `1` |

Every report states frames **examined** *of* frames **examinable**. "0 violations" without "of N
examinable" is indistinguishable from examining nothing — which is the failure being closed.

`NOT_APPLICABLE` is deliberately **not** exit `0`: a validation run that treated it as success
would commit the WO-055 false green in a shell script instead of a report.

**What counts as fabricated:** on an `observable: true` frame, `count == 0` with a non-null
`last_price`. `running_last_price` legitimately carries forward and is separately named — confusing
the two would flag every quiet frame. A traded interval with a *missing* price is reported
separately, never merged with fabrication: two different defects.

### §4.3 Against the real corpus — the positive demonstration

```
corpus            : captures/corpus_24h/corpus_20260805
frames total      : 7,695,082
frames EXAMINABLE : 0
frames EXAMINED   : 0
OUTCOME           : NOT_APPLICABLE          (exit 3)
  "…no frame carries a `trades.observable` field, so the question cannot be asked of this
   corpus. THIS IS NOT 'zero fabricated prices'."
```

The book-only corpus correctly **refuses to answer a question it cannot**. That is the WO-055 false
green made structurally impossible.

*(7.7 M is ~2× the 3.85 M frame count because the corpus retains both `.jsonl` and `.jsonl.gz` for
every closed segment — the duplication WO-054 flagged as TERM 5 AMBER. The scanner reads both; it
does not change the outcome.)*

### §4.4 Bite proof — `tools/wo057_scanner_bite_proof.py`, **VERDICT: PASS**

**MUTATION: collapse NOT_APPLICABLE into CLEAN** — the WO-055 false green, restored.

| set | under the mutation |
|---|---|
| **NOT_APPLICABLE case** | **FAILS** |
| fabrication BITE | still passes |
| correct-corpus DUAL | still passes |

```
corpus_fabrication_scan.py sha256 BEFORE/AFTER : fc21d38e…  IDENTICAL: True
NOT_APPLICABLE case fails under the collapse : True
fabrication BITE and correct DUAL still pass : True
real corpus returns NOT_APPLICABLE           : True
```

**The asymmetry is the proof.** A scanner that only found violations would satisfy the bite *and*
the dual — and would still be the tool that reported "§3.5 PASS — zero fabricated prices" over a
book-only corpus. Only the third case distinguishes *the query spoke and found nothing* from *the
query could not speak*.

### §4.5 The production call site

`evidence/WO-057/validation_run_detectors.md` names it: WO-055 runs the scanner against the
throwaway corpus immediately after the capture closes, and **the exit code is the gate** — `0`
passes §3.5, `1` aborts, `3` is a finding and **not a pass**.

---

## §5 CONDITION 4 — THE PER-SEGMENT TRIM COUNTER

**No §5.4 STOP.** The trim path is a single site (`del buf[:drop]` in `_retain_raw_text`), so this
was exactly "instrumenting the existing trim path" as the WO anticipated.

**Why the existing counter was not enough:** `_raw_text_evicted` counts evicted **frames**. One
trim of 500 frames and 500 trims of one frame are *identical* in it — and only the second is the
condition's subject. `_raw_text_trim_events` counts the **event**.

- **Read-and-reset in one call** (`take_trim_events()`), deliberately: two separate calls could
  interleave with a trim and lose an event, understating exactly the number the condition tests.
- **Lands in the segment record** — `SegmentManifest.raw_text_trim_events`, in the corpus rather
  than only in a log (0.9). `None` (not measured) is distinct from `0` (measured zero).
- **§5.2 threshold: `RETENTION_TRIM_ABORT_THRESHOLD = 2`** — "more than once per segment", a named
  constant because a threshold that lives only in a checklist cannot be read by the code that must
  trip on it. **Proven able to trip.**
- **§5.3 DUAL:** a segment with zero or one trim does not trip. One trim is the cap working as
  designed on a busy hour.

⚠ **Carried as an assumption:** the threshold's *relevance* rests on the unmeasured trade rate
(the second channel roughly doubles message count); its *definition* does not.

---

## §6 CONDITIONS 3, 5, 6 — RE-VERIFIED, NOT INFERRED

The capture path changed materially since WO-055 (a second channel), so all three were re-driven.

| # | Was | Now | Evidence |
|---|---|---|---|
| 3 | 🟡 "armed in the library, unreachable in capture" | 🟢 **reachable and fires** | a trade arriving while the channel is recorded unobservable now goes through `_demux_non_book`. The contradiction resolves the honest way round — the evidence of our own eyes wins, the channel is marked observable, **and the outage keeps its bounds**: the ledger still says we could not see for that interval rather than pretending the gap never happened |
| 5 | 🟢 | 🟢 | `GAP_CAUSES ∩ TRADE_OUTAGE_CAUSES = ∅`, and `GAP_CAUSES` is **still 5** — the ruled four plus `HOST_SUSPEND`, not extended |
| 6 | 🟢 | 🟢 | `ThroughputRecord` and the per-frame instrument are still constructed by the live loop — asserted **on the loop**, since asserting on a bare instance would test only that `__init__` is unchanged, which is not the thing at risk |

---

## EVERY ATTEMPT

1. **Checked what `LoadRecord` actually measures before deriving anything from it** — which is how
   the used-vs-free reframing surfaced. §2.1's premise ("WO-044's measured process usage") does not
   hold: WO-044 measured host memory, never the process.
2. **Measured the footprint rather than estimating it**, by running the real runner over a fixture
   socket and sampling RSS at three separable points.
3. **Two assertions of mine initially passed/failed for the wrong reason.** The `12.33` check
   matched my own explanatory comment (the same comment-matching trap as WO-056 §5) — rewritten to
   check executable lines only. Recorded because it is now twice.
4. **A `print("\n…")` written through a heredoc became a literal newline** inside the string,
   producing a `SyntaxError` in the capture runner. Caught immediately by the witness suite.
5. **The gate's real 60-second window stalled the capture tests.** Resolved with an autouse fixture
   that patches the evaluator — *not* an env override, because an env back door in production code
   would be a hole in the gate itself. The gate's ability to refuse is proved separately.
6. **Adapter attributes that exist only inside the live loop** (`captured_raw_text`,
   `_throughput_record`) broke four first-draft tests. Fixed by establishing the same preconditions
   the loop establishes, so the tests exercise the *real* `_retain_raw_text` rather than a stand-in.
7. **No socket opened.**

---

## §7 ACCEPTANCE

- [x] Term 2 gate encoded, both declarations derived-and-cited, trade-rate assumption **carried as
      an assumption**
- [x] Conditions 1, 2, 4 — each with a detector **proven able to fire** and a **dual**
- [x] Scanner's three-outcome distinction bite-proved **with the collapse mutation asymmetry**
- [x] Scanner run against `corpus_20260805` → **NOT_APPLICABLE**
- [x] Conditions 3, 5, 6 re-verified (not inferred)
- [x] Every BUILT row's reachability cell filled — `evidence/WO-057/validation_run_detectors.md`
- [x] `corpus_20260805` untouched — v1 `e3ab1aec…`, 38/38 capture hashes
- [x] Gates: lint 6/6 · contract 6/6 · ruff · annotation 0 · preflight · partition 31/31

### Test count arithmetic

```
  525  baseline at HEAD 60fc007 (WO-056 close, CI 31264684723)
+  13  tests/test_capture_gate.py (new)
+  20  tests/test_abort_detectors.py (new)
─────
  558  expected  (+ 2 skipped)
```

| Leg | Order A | Order B (seed 57057) |
|---|---|---|
| Python 3.14.6 | **558 passed, 2 skipped** (314.71s) | **558 passed, 2 skipped** (315.05s) |
| Python 3.11.15 | **558 passed, 2 skipped** (313.84s) | **558 passed, 2 skipped** (314.36s) |

### CI

_pending — filled in on the close commit_

---

## WHAT THE LEAD SHOULD RULE

1. **Term 2's memory half was never the blocker.** Under the corrected, mechanism-tied gate the
   host clears the derived floor by 10×. The remaining RED is **swap in use at idle**, which is the
   criterion actually tied to D46.
2. **The 12.33 GB figure should be retired by name**, as `a025db1e…` was. It is cited in three
   reports as free memory and it is not.
3. `LoadRecord.memory_gb` **is misleadingly named** — it records host memory *used*. Renaming it is
   a small change with a real cost avoided; not done here (outside scope), recommended.

---

## FILES

| File | Disposition |
|---|---|
| `src/trading/data/capture_gate.py` | **NEW** — the re-specified Term 2 gate |
| `tools/corpus_fabrication_scan.py` | **NEW** — condition 2's committed scanner |
| `tools/wo057_scanner_bite_proof.py` | **NEW** — PASS, collapse-mutation asymmetry |
| `src/trading/data/adapters/kraken_v2_book.py` | **CHANGED** — trim-event counter + `take_trim_events()` |
| `tools/live_corpus_capture.py` | **CHANGED** — gate wired into preflight; trim count into the segment record |
| `tests/test_capture_gate.py` | **NEW** — 13 tests |
| `tests/test_abort_detectors.py` | **NEW** — 20 tests |
| `tests/test_live_corpus_capture.py` | **CHANGED** — autouse gate fixture, with its reason |
| `evidence/WO-057/validation_run_detectors.md` | **NEW** — the reachability table |
| `captures/corpus_24h/corpus_20260805/` | **READ-ONLY — untouched**, verified twice |
