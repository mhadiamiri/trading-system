# WO-045 — BOUNDED RETENTION + THE TERMINATION-LOG-LEVEL FIX — REPORT

**Date:** 2026-08-07
**Base HEAD:** `e4dde21` (WO-044 complete, `corpus_20260805` ratified)
**Interpreters:** CPython 3.14.6 (dev) · 3.11.15 (acceptance, throwaway uv venv)
**SHIP IMPACT: YES** — `kraken_v2_book.py` retention path + log levels; `decision.py` (+4 codes).
**NOT IN SCOPE:** finding 3 (read-only live-corpus query) — declared and enforced, not built.

---

## §1 CONFIRM STATE

| Item | Measured | |
|---|---|---|
| HEAD | `e4dde21` | ✅ as the WO states |
| `git diff -- src/` at base | EMPTY | ✅ |
| `kraken_v2_book.py` sha256 at base | `3cb16565f881488509e4b4c1ec72c6fe15301c64f80e422258bc34ec24c7a3af` | ✅ matches WO-044's stated hash |
| Test count at base | **284** | ✅ matches CI run `31050446103` |
| import-linter | 6 kept / 0 broken | ✅ |
| ruff · annotation · preflight · partition | clean · 0 · PASS · **31/31** | ✅ |
| `corpus_20260805` | 88 files snapshotted before any edit | baseline digest `a025db1e…` |

**Baseline run note (§0.5 — report every attempt).** The first local baseline run reported
`1 failed, 283 passed`. The failure was `test_every_emitted_reason_code_is_declared`, and it was
**my own edit racing the running suite**: that guard reads `src/` from disk at test time, so it saw
`RAW_RETENTION_CAPPED` emitted in `kraken_v2_book.py` before I had declared it in `decision.py`.
283 + 1 = **284**, matching the authoritative CI baseline. Not a tree defect; recorded rather than
quietly re-run.

---

## §2 BOUNDED RETENTION

### §2.1 The precedent, as read

`FAILURE_CAPTURE_CAPPED` (`_capture_checksum_failure`, `_announce_capture_capped`):

- **Cap constants**, declared with derivation: `MAX_FAILURE_CAPTURES = 200`,
  `MAX_FAILURE_CAPTURE_BYTES = 8 MiB`; instance-overridable via `self._max_failure_captures` etc.
- **Enforced at the append site** — count cap checked before building the artifact, byte cap after
  sizing it. The two bind **independently**: "a cluster of large frames exhausts bytes before
  count; a cluster of small ones exhausts count first."
- **Count-past-cap**: `self._checksum_failure_count += 1` happens FIRST and is never capped —
  *"'3 failures' and '40,000 failures' are different worlds and both must stay reportable."*
  Past the cap a one-line summary is still recorded (`_record_failure_summary`).
- **Announce ONCE** via a `_capped` boolean guard, at `_log_error` (→ `logger.error`).
- **Never terminates the run** — *"the breaker owns termination."*
- **Keep FIRST N**, because *"the ONSET is the most diagnostic part."*

### §2.2 The cap

`MAX_RETAINED_RAW_FRAMES = 50_000` · `MAX_RETAINED_RAW_BYTES = 64 MiB` · `RAW_TEXT_TRIM_BATCH = 500`

The append at `kraken_v2_book.py:2956` moved behind `_retain_raw_text()`, so the bound lives with
the buffer rather than at one call site a future caller could bypass.

Mirrors the precedent on every axis — declared dual cap, count-past-cap surfaced, announce-once via
`RAW_RETENTION_CAPPED`, never terminates the run — and **diverges on exactly one, which is forced
rather than chosen:**

> **KEEP-LAST, NOT KEEP-FIRST.** The only in-code consumer, `_capture_checksum_failure`, reads
> `captured_raw_text[-1]` (the failing frame) and `[-(n+1):-1]` (its run-up). A keep-first ring
> would starve the very path this buffer exists to serve.

**Declared precedence: FLOOR > BYTE CAP > COUNT CAP.** The floor (21 = the failure-capture window)
is a hard minimum; the effective bound is `max(cap, floor)`. At the production cap of 50,000 against
a floor of 21 the floor never binds — but it does under a misconfigured tiny cap, and it should.
Surfaced in the docstring and pinned by `test_the_floor_outranks_both_caps` rather than left as
emergent behaviour someone later "fixes".

**Bounded, not constant.** Batched eviction makes the buffer oscillate within
`[cap − trim_batch, cap]`. The declared guarantee is the CEILING plus O(1) growth in run length.
Batching exists because evicting one entry per message would pay an O(n) list memmove (~400 KB at
50k entries) on every message past the cap, against WO-040's measured 0.031 ms/frame budget.

### §2.3 The derivation (against the measured 35–48 MB/h, as D46 requires)

```
Run 1 retained 1,114,367 raw messages over 12.9035 h   ->  ~86,360 messages/h
At the upper measured rate 48 MB/h:  48 MB / 86,360    ->  ~583 B retained per message
Cross-check at 35 MB/h:                                ->  ~425 B per message
Sizing on the conservative 583 B:  50,000 x 583 B      ->  ~29 MB, CONSTANT (not per-hour)
```

**The derivation was then validated by measurement**, not left as arithmetic: the bite proof
measured **32,302,076 B across 49,700 retained entries = 650 B/entry** for 600-byte messages
(`sys.getsizeof` of a 600-char `str` is 649 B). The predicted 583 B/message and the measured
650 B/entry agree to within the difference in message size.

**In messages and MB:** 50,000 messages ≈ **29 MB** predicted, **32 MB** measured at 600 B/message.
**Hours of trailing history:** 50,000 / 86,360 ≈ **35 minutes** of wire history retained — versus
the 21 entries (~1 second) the only consumer requires, i.e. **~2,380× its need**.

### §2.4 What the cap makes safe (a claim someone can check)

Raw-text retention is now **O(1) in run length**. A 7-day capture costs the same ~32 MB as a
1-hour one.

| | Uncapped (WO-044 behaviour) | Capped |
|---|---|---|
| 24 h | ~1.15 GB (observed: ~1.6 GB private) | ≤ 64 MiB |
| 7 days | ~8 GB at 48 MB/h | ≤ 64 MiB |

**The condition is SCALE-DEPENDENT.** 1.6 GB peaked comfortably on this host (15.7 GB RAM, 3.1 GB
free); the next host or the next duration may not. D46's failure mode is not OOM but
**MISATTRIBUTION**: memory pressure → swap → event-loop starvation → `HEARTBEAT_ABSENCE`, a HOST
problem entering the gap ledger wearing a VENUE problem's cause code.

### §2 BITE PROOF — `tools/wo045_retention_bite_proof.py` — **VERDICT: PASS**

| Artifact | Result |
|---|---|
| 1 — PRISTINE | 12 passed; measured **32,494,376 B → 32,302,076 B** across 50k→200k messages (FLAT) |
| 2 — MUTATED (cap neutered) | **7 failed, 5 passed**; measured **32,494,376 B → 129,824,056 B** (GROWS 4×) |
| 3 — RESTORED | 12 passed; bound holds again |
| 4 — sha256 exact-restore | `7fe6409aafe087e1b93466ebeca416ef3cbd6c12724f2b2341f55c6f68131608` **IDENTICAL** |

`DISCRIMINATION (mutation breaks the bite, not the dual): True` — all 7 bite assertions fail under
the mutation while all 5 duals still pass. **The memory bound is MEASURED, not asserted**: the
mutant retains **4.0× more** at 200k messages, and the pristine buffer does not grow at all between
50k and 200k.

The mutation restores the exact defect D46 ruled on (unbounded append), so the proof watches the
bound disappear rather than testing something adjacent.

**Three defects in my own implementation were caught by these tests before commit**, all one root
cause plus one bad assertion: the floor silently outranked both caps (undeclared precedence — now
declared and pinned), and the O(1) assertion demanded exact equality where batched eviction makes
the buffer oscillate. Recorded per §0.5.

**A bite-proof mechanism defect, also caught:** the multi-line mutation anchor was `\n`-joined while
the source is CRLF (3,496 CRLF lines, 0 bare LF), so the uniqueness assert found 0 matches and
**refused to mutate** — correctly. Earlier bite proofs used single-line anchors and never met this.
The anchor is now joined with the newline the file actually uses.

---

## §3 THE TERMINATION-LOG-LEVEL FIX

**Doctrine, ratified and recorded verbatim** in
`docs/decisions/2026-08-07-the-line-that-says-why-it-ended.md`:

> For unattended runs, any message that explains a TERMINATION logs at WARNING or above.
> **The line that says why it ended must never be the line that gets dropped.**

### §3.2 The full enumeration — and the larger instance it found

| # | Termination path | Before | After | Raised? |
|---|---|---|---|---|
| 1 | **Deadline elapsed** | **NO LOG AT ALL** | `CAPTURE_ENDED_DEADLINE` @ WARNING | ✅ **YES** |
| 2 | **Clean venue close (1000/1001)** | `logger.info` | `CAPTURE_ENDED_CLEAN_VENUE_CLOSE` @ WARNING | ✅ **YES** |
| 3 | Breaker STOP | `_log_error` → ERROR | unchanged | no |
| 4 | `RECONNECT_FLAG_STRANDED` | raise only, **no log** | ERROR, then raise | ✅ **YES** |
| 5 | Pre-connection guard refusals | raise before capture starts | unchanged | n/a — a refusal to START is not a termination |

**"Enumerate, don't fix the one you found" paid.** The reported defect was #2 (INFO). The
enumeration found **#1 logs nothing whatsoever** — the ordinary planned end of every bounded
capture, and the exit that ended corpus run `20260806130401`. A strictly larger hole than the one
that bit, and invisible to anyone fixing only the reported symptom.

**#4** raised with the reason only inside the exception. That is not equivalent to a log: the corpus
runner CATCHES exceptions and writes the traceback to `CRASH_TRACEBACK.txt`, so the log stream could
carry no explanation at all — the very gap §3 closes. Now log-then-raise, matching the breaker.

### The mechanism — centralised, not per-exit

Each normal exit sets `termination_reason`; **one guaranteed WARNING** fires after the loop. A
future `break` that forgets logs `CAPTURE_ENDED_UNDECLARED` — loud by construction rather than
silent by omission. Logging at each break site would leave the next author free to add a silent exit.

**The three causes are declared reason codes**, not free text. This was forced by the
raised⇒declared guard, which correctly read code-shaped text in a log message as governed
vocabulary. The honest resolution was to govern it rather than reword it into invisibility — a
termination cause **is** an audit fact. (Recorded per §0.5: the guard bit twice during this WO, once
for `RAW_RETENTION_CAPPED` and once for the three termination causes. Both times it was right.)

### §3.3 Evidence

`tests/integration/test_termination_log_level.py` — **5 tests**, driving the real
`get_live_market_data` over scripted transport and filtering `caplog` to **WARNING and above**, i.e.
reproducing exactly what a detached run retains:

- deadline termination survives the filter and names `CAPTURE_ENDED_DEADLINE`
- clean-close termination survives it and names `CAPTURE_ENDED_CLEAN_VENUE_CLOSE` (driven with a
  real `ConnectionClosedOK(Close(1000, "normal closure"))`)
- **preservation dual**: the line is not merely present but INFORMATIVE — it carries frames received
  and states emitted. A line saying only "ended" would satisfy a level check and still leave the
  reader guessing.
- the sentinel exists and the reason defaults to unset
- the three causes are declared

**Why this and not a four-artifact bite proof (§3.3 permits stating the evidence):** the mutation
for a log-level change is the level itself, and these tests *are* that mutation's detector — they
assert against a WARNING filter, so reverting any path to INFO or to no-log fails them directly.
A separate mutate-restore harness would re-prove what the filter already proves. Stated rather than
skipped, and not padded.

### §3.4 Recorded against the corpus provenance

`corpus_20260805`'s record states that run `20260805220327`'s termination cause remains
**inference (cause-by-elimination)**, honestly labelled per D46, and that this fix makes the next
such fact directly readable. The corpus is not re-derived and not re-labelled.

---

## §4 FINDING-3 RESTRICTION — DECLARED, AND ENFORCED (not built)

D46 assigned the read-only live-corpus query to the default-deny reader WO. **Nothing was built for
it here.**

The restriction is recorded in `progress.md` and enforced cheaply: `--progress` **REFUSES (exit 3)**
when the target corpus has a run with no `MANIFEST.json` whose segments were written within 120 s,
and the refusal names the safe alternative. `--force-progress` overrides, explicitly accepting the
race.

```
REFUSED: corpus 'corpus_x' appears to have a LIVE run (run_a).
  --progress calls reconcile(), which WRITES CORPUS_MANIFEST.json, and would
  race the running capture's finalize. ...
```

**The detector is a HEURISTIC and its failure modes are declared, not left to be discovered:** a run
killed seconds ago reads as live (cost: a refusal, overridable — cheap); a live run stalled >120 s
reads as dead (cost: the race it guards, recoverable via `reconcile()`). The asymmetry is
deliberate — the cheap failure is the likely one. It deliberately does not inspect processes, which
would be platform-specific and is the reader WO's job.

---

## §5 ACCEPTANCE

- [x] Cap declared with derivation stated against 35–48 MB/h; count-past-cap surfaced, not silent
- [x] Bite proof: bite + dual + necessity mutation, four artifacts, sha256 exact-restore, memory
      bound **MEASURED** (32.3 MB flat vs 129.8 MB unbounded)
- [x] All termination paths enumerated; every reason logs WARNING+; evidence stated
- [x] Doctrine decision doc committed
- [x] Finding-3 restriction declared **and enforced**
- [x] `captures/corpus_24h/corpus_20260805/` **byte-untouched — 88 files, digest `a025db1e…`
      identical before and after**
- [x] src hashes below; `factory.py` / `registry.py` unchanged
- [x] Test count with arithmetic, both interpreters, both orders
- [x] lint 6/6 · contract 6/6 · ruff · annotation 0 · preflight · partition 31/31

### Test results

| Leg | Interpreter | Order | Result |
|---|---|---|---|
| dev | 3.14.6 | `-p no:randomly` | **301 passed, 2 skipped** (309.20s) |
| acceptance | 3.11.15 (uv venv) | `-p no:randomly` | **301 passed, 2 skipped** (307.34s) |
| order-dependence | 3.14.6 | `--randomly-seed=20260807` | **301 passed, 2 skipped** (309.02s) |

**Arithmetic:** 284 at base + 12 (`tests/test_raw_retention_cap.py`) + 5
(`tests/integration/test_termination_log_level.py`) = **301**.

### src disposition

```
BEFORE  3cb16565f881488509e4b4c1ec72c6fe15301c64f80e422258bc34ec24c7a3af  kraken_v2_book.py
AFTER   7fe6409aafe087e1b93466ebeca416ef3cbd6c12724f2b2341f55c6f68131608  kraken_v2_book.py
AFTER   2fdff10a37f74e65d5d229cf7045df21811ccfe06a183b4a021be2418f7fcf1f  decision.py  (+4 codes)
UNCHANGED 56e0a931740a39801ec1f484683a8625ebec5b268106e728d87f8d41e7ad4121  corpus.py
UNCHANGED 103a8ba793c6c1d2bff6012095e9616a9e7ab5d92f428eadd7f2b194a041834c  factory.py
UNCHANGED 5bf833c78fd3b91e055e91c08026da2439801cf124c485928ecf8f492ba38a68  registry.py
```

`git diff --stat -- src/`: `kraken_v2_book.py` +222/−6, `decision.py` +32/−0.

**Four reason codes added** (all genuinely producible, all prefix-free across the union):
`RAW_RETENTION_CAPPED`, `CAPTURE_ENDED_DEADLINE`, `CAPTURE_ENDED_CLEAN_VENUE_CLOSE`,
`CAPTURE_ENDED_UNDECLARED`.

---

## EVERY ATTEMPT

1. Snapshotted `corpus_20260805` (88 files) before any edit, so untouched is provable not asserted.
2. Baseline suite raced my own edit → 1 failed / 283 passed; diagnosed, count confirmed 284.
3. Read the failure-capture precedent before writing anything (§2.1).
4. Implemented cap → vocabulary guard failed on undeclared `RAW_RETENTION_CAPPED` → declared it.
5. Implemented termination reasons → vocabulary guard failed on 3 code-shaped strings → promoted
   them to declared codes rather than rewording them.
6. Retention tests: 3 failed on first run (floor precedence ×2, over-strict O(1) assertion) →
   declared the precedence in code, corrected the assertions, used realistic caps.
7. Bite proof refused to mutate (CRLF vs `\n` anchor) → made the anchor line-ending agnostic.
8. Bite proof PASS; three full suite legs; all gates; corpus re-verified untouched.

## STOP

Per the WO. Next: 008c validation phase — the default-deny reader with gap enforcement (finding 3
folded in) → the first backtest against `corpus_20260805`.
