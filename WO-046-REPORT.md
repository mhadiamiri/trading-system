# WO-046 — 008c VALIDATION PHASE: THE DEFAULT-DENY CORPUS READER — REPORT

**Date:** 2026-08-07
**Base:** WO stated `89e5857`; actual HEAD `744ba1e` = `89e5857` + a **docs-only** commit
(`WO-045-REPORT.md`, CI run numbers). Recorded as a base annotation, not a STOP — `git diff --stat
89e5857..HEAD` is one markdown file.
**Interpreters:** CPython 3.14.6 (dev) · 3.11.15 (acceptance, throwaway uv venv)
**SHIP IMPACT: YES** — new production module `src/trading/data/corpus_reader.py`; `decision.py` +2 codes.
**NOT IN SCOPE:** the backtest, strategy, cost model. This builds the READ boundary only.

---

## §1 CONFIRM STATE + THE CONTRACT

| Item | Measured | |
|---|---|---|
| HEAD | `744ba1e` (= stated base + docs-only) | ✅ annotated |
| `git diff -- src/` at base | EMPTY | ✅ |
| Test count at base | **301** | ✅ matches CI `31185950085` |
| import-linter | 6 kept / 0 broken (with the new module) | ✅ |
| `corpus_20260805` snapshot before any work | 88 files, digest `a025db1e…` | ✅ |

**Baseline run note (§0.5).** As in WO-045, the baseline suite raced my own edit: the
raised⇒declared guard reads `src/` from disk at test time and saw `CORPUS_READ_REFUSED` emitted
before it was declared. `300 passed + 1 failed = 301`, matching CI. Not a tree defect.

### The gap-record schema, as WO-014c-2 §1.2 declared it

```python
@dataclass
class GapRecord:
    cause: str                         # one of the ruled causes
    reason_code: str                   # the DECLARED audit code emitted (links gap -> vocab)
    open_monotonic: float              # gap OPEN = last frame received / failing frame
                                       #   (NOT the threshold-trip instant)
    close_monotonic: Optional[float]   # first validated emit after recovery;
                                       #   None => UNRESOLVED / TERMINAL (open-ended)
    resumed: bool                      # True once a validated MarketState closed the window
    terminal: bool                     # True if this gap ENDS the capture (breaker trip)
    last_validated_book: Optional[dict]# {best_bid,best_ask,last_checksum,at} at OPEN
    retry_ladder: list                 # [{attempt,at,delay_s,error}]; [] for a same-socket resync
    detail: str                        # human trigger text
    open_server_ts: Optional[str]      # CORROBORATION only; the AUTHORITATIVE bound is monotonic

    @property
    def duration_s(self) -> Optional[float]:
        return None if self.close_monotonic is None else close_monotonic - open_monotonic
```

Run level: `run_wall_anchor` (ISO-8601 UTC, ONCE per run), `run_monotonic_anchor`,
`run_start_monotonic`, `run_end_monotonic`, `gaps`, `gaps_detected`, `frames_captured`,
`evidentiary_bounds`, `.incomplete`.

**Ruled clock discipline:** every gap bound is `time.monotonic()`. Calendar location comes from the
once-per-run anchor and never from a per-gap wall timestamp:

```
wall(t_mono) = run_wall_anchor + (t_mono − run_monotonic_anchor)
```

**The reader's contract, as §1.3 specified it:** one clock ⇒ total, cheap interval intersection;
`close = None` read as **+infinity** so default-deny falls out of the schema rather than being
bolted on; and *"no intersection"* trustworthy **only** against a ledger known to be COMPLETE.

### Divergence check — the real ledger vs the declared schema: **NO DIVERGENCE**

Checked field-for-field across all 38 persisted gap records of `corpus_20260805`:

```
declared-but-ABSENT   : (none)
EXTRA beyond declared : (none)
derived present       : duration_s
impl-added present    : gap_id
all gap records share ONE field set: True
run_start declared-but-ABSENT: (none)      run_end declared-but-ABSENT: (none)
19 gap opens · causes {KEEPALIVE_RECONNECT, VENUE_DISCONNECT}
reason codes {HEARTBEAT_ABSENCE, VENUE_CONNECTION_CLOSED}
```

`gap_id` is the implementation's per-occurrence identity (WO-014c-2 §2), additive to the §1.2
sketch; `venue`/`mode` on `run_start` are additive context. Neither is a divergence — no declared
field is missing, no declared semantics contradicted. **No STOP.**

### ⚠ FINDING — two rulings conflict on the intersection test (reported, resolved to the later spec)

WO-014c-2 §1.3 sketched the test with **STRICT** inequalities on a half-open interval:

```
intersects([t0,t1]) == t0 < (g.close_monotonic or +inf) AND g.open_monotonic < t1
```

Corpus precondition 5 (WO-022 §3.2), the `GapLedger` docstring, and **WO-046 §2.3** all rule
**INCLUSIVE** bounds with a zero-duration gap being a real gap.

They disagree at the boundary. Under the strict form a zero-width gap at instant `c` does **not**
intersect a window ending at `c` or starting at `c` — so a query touching the gap's exact instant
would be served as continuous. **This module implements the INCLUSIVE form**: the later ruling is
explicit, is a hard spec, is stated in production (`GapLedger`: *"a zero-width gap still intersects
a query spanning its instant"*), and errs toward refusing. Reported rather than silently resolved.

### The seam's shape, and D45

`SeamRecord`: `seam_id`, `cause`, `reason_code`, `prior_run_id`, `resumed_run_id`,
`prior_last_frame_utc`, `resumed_first_frame_utc`, `resolved`, `duration_seconds`, `detail`.

**A structural difference exists and must be stated: gap bounds are per-run MONOTONIC floats; seam
bounds are WALL-CLOCK UTC.** Monotonic is not comparable across runs — `corpus_20260805`'s two runs
carry anchors `115471.34` and `169506.05`.

**D45 HOLDS.** The reader normalises everything onto one wall-clock timeline using the anchor
formula the schema declared for exactly this purpose, and after normalisation there is no
seam-specific branch anywhere in the refusal path. The normalisation is **not** seam-special: a
multi-run corpus needs it for GAPS regardless, since raw monotonic cannot be compared across runs.
Not a finding; stated because "needs no separate reader logic" is true at the level D45 asserted it
(refusal semantics) and would be false if read as "needs no clock handling".

---

## §2/§3 THE READER AS BUILT

`src/trading/data/corpus_reader.py` — Data layer, `lint-imports` **6/6 unchanged**.

| Contract | How |
|---|---|
| **2.1 default-deny** | `read_window()` raises `CorpusReadRefused` naming each unacknowledged discontinuity's `identity`, cause, bounds and duration |
| **2.1 not expressible** | a permitted read returns `CorpusWindow.segments` only — **no** `.frames` / `.series` / `.concat()`. Acknowledgment buys permission to READ, never to render continuous |
| **2.2 acknowledgment** | `Acknowledge(cause, max_duration_seconds=None, accept_open_ended=False, reason="")` — explicit, per-request, class-aware; a cause outside the closed set raises at construction |
| **2.3 zero-duration + inclusive** | `Discontinuity.intersects` uses `start <= end_utc and start_utc <= end`, with `None` end read as +infinity |
| **2.4 seams** | one `Discontinuity` type for gaps and seams; no branch on kind in the refusal path |
| **2.5 read-only** | opens files for reading only, creates nothing; enforced mechanically by a source scan test |

Beyond the stated contract, two properties the schema demanded:

- **Open-ended ⇒ deny forever after.** `close = None` reads as +infinity (§1.3(3)), and accepting
  one requires `accept_open_ended=True` — a duration bound cannot speak to a window with no
  measured width, so however generous `max_duration_seconds` is, it never sweeps up a terminal gap.
- **Incomplete ledger ⇒ deny everything.** `LedgerIncomplete` (§1.3(4)) — a run with a declared
  `incomplete` count, a missing anchor, or a torn JSONL line cannot answer "no gap here", so the
  reader denies rather than returning a silence it cannot stand behind.

**Two reason codes added**, both genuinely producible and prefix-free: `CORPUS_READ_REFUSED`,
`ACKNOWLEDGMENT_CAUSE_UNDECLARED`.

---

## §4 BITE PROOFS — `tools/wo046_reader_bite_proof.py` — **VERDICT: PASS**

Fixtures are **synthetic and in-repo**, built from the declared schema. No test depends on the
700 MB artifact.

| Artifact | Result |
|---|---|
| 1 — PRISTINE | 21 passed |
| 2 — **MUTATION A** (default-deny neutered: `unacknowledged` forced empty) | **13 failed, 8 passed** — 9 refusal tests fail, **0 duals fail**, all 7 duals pass |
| 3 — **MUTATION B** (blanket accept: cause-class comparison removed) | **2 failed, 19 passed** — **only** the 2 class-awareness tests; refusal half untouched |
| 4 — RESTORED | 21 passed |
| sha256 exact-restore | `bf611e09704f2d51d046ccd167e8b1657ac6a34aeec7f79f86750e4451bdb7bc` **IDENTICAL** |

```
MUTATION A discriminates (refusal fails, duals hold) : True
MUTATION B discriminates (class only, refusal intact): True
```

- **§4.1 (S13, both shapes in ONE test)** — `test_d20_refusal_and_preservation_in_one_test`:
  the same window on the same reader refuses unacknowledged (naming `run:run_a/gap:0`,
  `KEEPALIVE_RECONNECT`, `HEARTBEAT_ABSENCE`, `10.000000s`) and serves acknowledged, as **2
  segments** of 50 s and 90 s — covered 140 s against a 150 s request, the 10 s gap being absence
  of data rather than coverage.
- **§4.2 zero-duration** — a gap with `open == close` refuses, and inclusive bounds are pinned at
  each boundary: window END equal to the instant, window START equal to it, and the degenerate
  window that *is* the instant. All three would be **served** under the strict half-open form.
- **§4.3 seam-spanning** — refuses by default naming `corpus/seam:0`, serves acknowledged as 2
  segments; a mixed window names both a gap and a seam in one refusal.
- **§4.4 class-awareness** — acknowledging `KEEPALIVE_RECONNECT` leaves `HOST_SUSPEND` refused; a
  duration bound is part of the acknowledgment; a typo'd cause fails loudly at construction; and
  no single `Acknowledge` admits more than its own class.
- **§4.5 read-only** — a digest around construction + query + refused read + acknowledged read is
  unchanged, plus a **source scan** rejecting any write-mode `open`, `write_text`, `write_bytes`,
  `mkdir`, `unlink`, `rmdir` or `shutil` in the module.

---

## §5 REAL-CORPUS VALIDATION (evidence, not a committed test)

```
gaps seen : 19   seams seen: 1   incomplete runs: ()
causes    : gaps=[KEEPALIVE_RECONNECT, VENUE_DISCONNECT]  seams=[PROCESS_RESTART]

EVERY discontinuity, window spanning it:
  windows requested : 20
  refusals          : 20
  refusals naming a REAL ledger discontinuity : 20
  refusals naming anything NOT in the ledger  : (none)

ACKNOWLEDGED reads served (segmented)          : 20/20
Clear windows inside a continuous stretch      : 19 tried, 19 served CONTINUOUS

CLASS-AWARENESS at corpus scale:
  ack KEEPALIVE_RECONNECT -> still refused, remaining: [PROCESS_RESTART, VENUE_DISCONNECT]
  ack PROCESS_RESTART     -> still refused, remaining: [KEEPALIVE_RECONNECT, VENUE_DISCONNECT]
  ack VENUE_DISCONNECT    -> still refused, remaining: [KEEPALIVE_RECONNECT, PROCESS_RESTART]

corpus digest BEFORE/AFTER the validation pass : UNCHANGED
```

**All 19 gaps and the 1 seam are visible to the reader and each triggers default-deny.** Every
refusal named a real ledger discontinuity; none invented one.

### A declared difference between two honest coverage numbers

The reader reports **36.887 h**; `CORPUS_MANIFEST.json` reports **36.8867 h**. Delta **1.080 s** over
36.9 hours. Not a discrepancy — two different bounds:

- the **manifest** measures FIRST FRAME → LAST FRAME (the ratified figure);
- the **reader** measures the ledger's declared emission window (`run_start_monotonic` →
  `run_end_monotonic`), which is slightly wider because the anchor is stamped at capture start
  before the first frame arrives (0.74 s / 0.39 s) and `run_end` in the `finally` block after the
  last (0.03 s / 0.12 s).

The reader uses ledger bounds because reading frame timestamps would mean opening ~700 MB of
segments. `coverage()` now states its basis in the output (`bounds_basis`,
`manifest_bounds_basis`) so the two can never be silently compared.

---

## §6 FINDING 3 — THE READ-ONLY LIVE QUERY

`CorpusReader.coverage()` answers coverage / gaps / seams **writing nothing**, exposed as
`python tools/live_corpus_capture.py --corpus-id <id> --coverage`.

**`--progress` disposition: KEPT for the writing path, NARROWED in reach — not retired.**

- `--progress` still calls `reconcile()`, which **saves** `CORPUS_MANIFEST.json`. It is a writer,
  and WO-045 §4's live-run refusal is exactly right for it. Retiring the heuristic would re-open the
  race it was built to prevent, so it stays.
- `--coverage` needs no such guard **because it writes nothing**, and is checked *before* the
  `--progress` branch so the writer's guard never gates the reader. The heuristic's reach is thereby
  narrowed to the only path that ever needed it.
- Recommended usage flips: **`--coverage` is the query to use while a run is in progress**;
  `--progress` is for reconciling a corpus that is not being written.

**No-write proof.** Three independent lines: (a) `test_the_reader_writes_nothing` digests a fixture
corpus around construction, `coverage()`, a refused read and an acknowledged read; (b)
`test_the_reader_module_opens_nothing_for_writing` scans the module source for any write path
(the WO-032 evidence-write-boundary precedent); (c) the §5 real-corpus pass, whose digest is
unchanged across 20 refusals, 20 acknowledged reads and 19 clear-window reads.

**Honest limit:** (c) ran against a corpus with no live capture — the WO's "closest safe
equivalent". A genuinely concurrent live-run test would mean opening a real socket, which is outside
this WO's grant. What IS proved mechanically is that the reader contains no write path at all, which
is the property that makes concurrency safe; the concurrency itself is inferred from that, and the
inference is stated rather than dressed as a measurement.

---

## §7 ACCEPTANCE

- [x] Schema read and conformed to; **no divergence** (field-for-field against the real ledger)
- [x] Default-deny per §2.1–2.5; acknowledgment explicit / per-request / class-aware
- [x] Bite proofs 4.1–4.5, four artifacts, sha256 exact-restore, **two discriminating mutations**
- [x] Real-corpus validation: **19 gaps + 1 seam all trigger default-deny**; digest unchanged
- [x] Read-only live query built; `--progress` disposition stated (kept for the writer, narrowed)
- [x] `corpus_20260805` byte-untouched — digest before and after
- [x] Test count with arithmetic, both interpreters, both orders
- [x] lint 6/6 · contract 6/6 · ruff · annotation 0 · preflight · partition 31/31

### Test results

| Leg | Interpreter | Order | Result |
|---|---|---|---|
| dev | 3.14.6 | `-p no:randomly` | **322 passed, 2 skipped** (313.60s) |
| acceptance | 3.11.15 (uv venv) | `-p no:randomly` | **322 passed, 2 skipped** (312.80s) |
| order-dependence | 3.14.6 | `--randomly-seed=20260807` | **322 passed, 2 skipped** (313.94s) |

**Arithmetic:** 301 at base + 21 (`tests/test_corpus_reader.py`) = **322**.

### CI — the real run on this commit

**Commit `ceb1cd0`** (pushed `744ba1e..ceb1cd0`) · **CI run `31191726876`** · triggered via push.

| Job | ID | Duration | Result |
|---|---|---|---|
| `test (3.14)` | 92909909250 | 10m41s | ✅ **322 passed, 2 skipped** (303.77s) |
| `test (3.11)` | 92909909372 | 10m26s | ✅ **322 passed, 2 skipped** (300.96s) |

Counts pulled from the job logs, not inferred from the ✓ — a green checkmark says the job exited
zero, not what it ran. Both legs ran the randomized-order step and reported 322/2, matching all
three local legs.

Gates: `lint-imports` **6 kept / 0 broken** · ruff clean · annotation **0** · preflight PASS ·
`wo029_reverify_partition` **PASS 31/31** · `git status --porcelain evidence/` empty.

### Corpus untouched

```
88 files
before : a025db1ea224e6fdcbf519c747e05d6c51277ad73e8c5f7016d6f65049c29c45
after  : a025db1ea224e6fdcbf519c747e05d6c51277ad73e8c5f7016d6f65049c29c45
CORPUS BYTE-UNTOUCHED: TRUE
```

### src disposition

```
NEW        bf611e09704f2d51d046ccd167e8b1657ac6a34aeec7f79f86750e4451bdb7bc  corpus_reader.py
CHANGED    b3e6618415843a26677023854c62560b62159a09a0fdcc6d85e9cd0be869e3b0  decision.py (+2 codes)
UNCHANGED  7fe6409aafe087e1b93466ebeca416ef3cbd6c12724f2b2341f55c6f68131608  kraken_v2_book.py
UNCHANGED  56e0a931740a39801ec1f484683a8625ebec5b268106e728d87f8d41e7ad4121  corpus.py
```

---

## EVERY ATTEMPT

1. Snapshotted the corpus (88 files, `a025db1e…`) before any work.
2. Read the WO-014c-2 schema in full **before** writing the reader; ran a field-for-field
   conformance check against the real ledger. No divergence → no STOP.
3. Found the half-open vs inclusive conflict between two rulings; implemented the later hard spec
   and reported the conflict.
4. Baseline suite raced my own edit (guard reads `src/` at test time) → 300+1 = 301, matching CI.
5. Vocabulary guard required declaring `CORPUS_READ_REFUSED` and
   `ACKNOWLEDGMENT_CAUSE_UNDECLARED` — the third consecutive WO in which it bit and was right.
6. Discovered the reader's coverage differs from the manifest's by 1.080 s; traced it to
   emission-window vs frame bounds and made the basis explicit in the output rather than papering
   over it.
