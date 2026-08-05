# WO-044 — RESUMABLE 24-HOUR CORPUS — REPORT

**Date:** 2026-08-05
**Base HEAD:** `0425ec6` — WO-043 — Add psutil to requirements for load recording
**Interpreter:** CPython 3.14.6 (3.11 acceptance leg via throwaway uv venv)
**Scope executed:** §1 confirm state · §2 run-3 eligibility verdict · §3 resume support · §4 the
15-minute outage policy
**Scope NOT executed:** §5 (run and accumulate) — gated on §5.1 (commit green + CI) and on the
operator prerequisite, both open at the time of writing.
**SHIP IMPACT: YES** — `src/trading/data/adapters/kraken_v2_book.py`,
`src/trading/logkit/decision.py`, and a new production module `src/trading/data/corpus.py`.

---

## §1 CONFIRM STATE

| Item | WO says | Measured | Disposition |
|---|---|---|---|
| Test count | 237 both interpreters | **256** at base HEAD | **WO figure is STALE** — see below |
| `git diff -- src/` | clean | EMPTY at base | ✅ |
| import-linter | 6/6 | 6 kept, 0 broken | ✅ |
| ruff | clean | All checks passed | ✅ |
| annotation scan | 0 | 0 | ✅ |
| preflight path check | pass | PASS | ✅ |
| `wo029_reverify_partition` | 31/31 | PASS 31/31 | ✅ |

### §1 FINDING — the WO's 237 baseline is stale (code wins, §0.1)

The WO instructs "confirm 237 both interpreters." The tree measures **256 passed, 2 skipped**
(`297.32s`, 3.14, `-p no:randomly`). This is not a discrepancy to chase but an arithmetic one to
state: WO-043 added `tests/test_live_corpus_capture.py` with **19** tests, and **237 + 19 = 256**.
The WO's figure predates the commit it is based on. Carried forward as 256.

### §1 GRANT TERMS

- Amended grant (D45): one corpus-id, all resume runs toward **24 CUMULATIVE hours**.
- Expiry: corpus completion or **14 days**, whichever first. `instructions.md` was authored
  2026-08-05, so the stated expiry is **2026-08-19**. ⚠ The WO does not date the grant explicitly;
  this is read from the instruction file's own timestamp and is flagged for confirmation.
- **OPERATOR PREREQUISITE — NOT CONFIRMED.** The WO requires the security policy that shuts the
  machine down to be DISABLED and confirmed before any run. That confirmation has **not** been
  given, and it cannot be established from inside the repo. §5 is therefore not begun. This is a
  stated blocker, not an omission.

---

## §2 RUN-3 RETROACTIVE ELIGIBILITY — **VERDICT: MACHINERY-VALIDATION-ONLY**

Run `20260730152029`. Measured with the new `trading.data.corpus` readers over the preserved
artifacts (not from memory, not from a report):

```
segments on disk : 5  (4 complete + 1 partial 19Z)
MANIFEST.json    : False
first frame      : 2026-07-30T15:20:31.199458+00:00
last frame       : 2026-07-30T19:15:09.268063+00:00
measured span    : 14078.1s = 3.9106 h
gaps             : 1 gap, 1.7266s closed, 0 terminal, 0 incomplete
covered          : 3.9101 h
```

The run is real, substantial, and its data is intact. It still does not qualify. The four
conditions, judged as demonstrable evidence:

**(a) Full preflight evidence EXISTS for that run — ❌ FAILS.**
No preflight artifact exists for run_id `20260730152029`. The only surviving preflight transcript
is `corpus_stdout.log`, whose mtime is `2026-07-30 15:19:34Z` and whose run header reads
`WO-043 CORPUS CAPTURE RUN — 20260730151934` — **a different run**, the one that died immediately on
`LIVE_CAPTURE_UNSUPPORTED` (`DATA_SOURCE=simulated`) without opening a socket. Run 3 started ~55
seconds later and its preflight went to a console that was never captured. Its run directory
contains ten files: five `.jsonl`, four `.gz`, and `gap_ledger.json`. No preflight record.
The condition asks whether evidence EXISTS. For this run_id it does not.

**(b) Segments are HASHED in a manifest — ❌ FAILS.**
No `MANIFEST.json` was written (the process was killed before its `finally` block). Hashes *can* be
computed now — `reconcile_run_from_disk` does exactly that. **My reading: post-hoc hashing does not
satisfy this condition.** A hash computed today attests what the file contains *today*; it cannot
witness the interval between capture and hashing. At-capture hashing attests the bytes as written by
the process that wrote them. These are different claims, and provenance is the stronger one the
condition asks for. The WO's own instruction is decisive: *"if uncertain, it does NOT count —
provenance must be demonstrable."*
This distinction is now enforced in code rather than left to judgement: `SegmentRecord` carries
`hashed_at_capture`, set `False` by reconciliation, so a post-hoc hash can never later be mistaken
for at-capture provenance.

**(c) Gaps are LEDGERED — ✅ HOLDS.**
`gap_ledger.json` is present and complete in the gap sense. One gap: `VENUE_DISCONNECT` /
`VENUE_CONNECTION_CLOSED`, opened at monotonic `18333.028`, resolved at `18334.755`, TRUE duration
**1.7266s**, `resumed=true`, `terminal=false`, carrying `last_validated_book` and
`open_server_ts=2026-07-30T17:45:53.384034Z`. Zero incomplete gaps. The 17:45:53 reconnect the WO
names is confirmed present and closed.
Noted for completeness: the ledger has a `run_start` record but **no** finalize/`terminal_summary`
record, because the process was killed. Gap completeness holds; run-level closure does not.

**(d) Same proven machinery at a HEAD-adjacent state — ✅ HOLDS.**
Same `tools/live_corpus_capture.py`, same adapter, same gap ledger, at WO-043 commits immediately
preceding this WO's base.

**VERDICT: two of four conditions fail. Run 3 is MACHINERY-VALIDATION-ONLY. Cumulative starts
fresh at 0.**

### The partial-hour question (§2, explicitly asked)

**Partial segments count; measured span is what counts.** An hourly segment boundary is a *rotation
policy* — an archival artifact — not an epistemic one. A genuine 55-minute partial segment is 55
minutes of real captured data, and refusing to count it would UNDERSTATE the corpus, which §0.4
forbids in the same breath as overstating. `RunRecord.covered_seconds` therefore measures
frame-to-frame and subtracts recorded in-run gap time; it never consults segment completeness.
What disqualifies a run is missing **provenance**, never an untidy hour boundary — which is exactly
why run 3 fails on (a) and (b) rather than on its partial 19Z segment.

### Why this verdict costs less than it appears

Run 3's 3.91 hours are not lost to the project — they remain on disk, readable, and were the data
that measured §4's window. They simply cannot be *counted* toward a corpus whose whole claim is
demonstrable provenance. The resume machinery built in §3 means the next 3.91 hours will carry
their own preflight, their own at-capture hashes, and a ledgered seam.

---

## §3 RESUME SUPPORT — BUILT

New production module: **`src/trading/data/corpus.py`**.

**Why it is in `src/` and not `tools/`** — the load-bearing constraint. The three seam causes are
DECLARED reason codes, and both vocabulary guards resolve `SRC = parents[1] / "src"`
(`test_reason_code_vocabulary.py:52`, `test_archive_readiness.py:36`). A seam emitted from `tools/`
would be **declared-but-not-producible** — invisible to the guard built to catch precisely that,
which is the blind spot WO-037 §3 found a dead constant living in.

### §3.1 Corpus-id spanning runs — scheme

```
captures/corpus_24h/<corpus_id>/
├── CORPUS_MANIFEST.json          # spans every run + every seam
├── seam_ledger.jsonl             # write-through, one line per seam state change
└── <run_id>/
    ├── PREFLIGHT.json            # this run's opening record (§3.2)
    ├── corpus_<HOST>_<YYYYMMDDTHH>Z.jsonl[.gz]
    ├── gap_ledger.json
    └── MANIFEST.json             # per-run, unchanged from WO-043
```

Grouping is **structural**: a run cannot belong to a corpus without living inside that corpus's
directory, so "which corpus is this run part of" is never a judgement call. `corpus_id` comes from
`--corpus-id` / `CORPUS_ID`; omitting it starts a NEW corpus (an explicit choice, never a silent
re-use of whatever is on disk).

### §3.2 Per-resume full preflight — no inherited preconditions

Every run writes `PREFLIGHT.json` with the **real measured value** of each condition, not a
transcript of green ticks. Persisted *before* the pass/fail branch, so a REFUSED preflight also
leaves evidence (§0.5: report every attempt).

**FINDING — repaired.** WO-043's condition 3.7 printed a hardcoded string:

```python
print(f"  ✅ GREEN: Guards armed fresh (demonstrated by test suite)")
print(f"           237 passed, 2 skipped (both interpreters)")
```

It ran no test, checked nothing, and **could not go red**. Every corpus run to date logged it as a
green grant condition without it ever being measured at run time; by WO-044 its number was also
wrong. A condition that cannot fail is a checklist, and `live_capture.py:12` records why this
project rejects those: *"PREFLIGHT ENFORCEMENT LIVES IN THE RUNNER, not a checklist — checklist-
enforced rules are 0-for-N in this project."* It matters more under §3.2 than before: a resume that
inherits a frozen string is exactly the inherited precondition condition 1 forbids.

Condition 3.7 now **executes** in-process: it engages a fresh kill switch and asserts a `VETO` with
`RISK_VETO_KILL_SWITCH`, and asserts `LiveCaptureRunner` refuses `TRADING_ENV=mainnet` with
`LIVE_CAPTURE_ENV_REFUSED`. Both can go red — which they did, loudly, on a wrong constructor
signature during development. Conditions 3.2 and 3.5 likewise now **read** the divergence bound and
the gap-cause set from the adapter instead of restating them, so a hand-copied constant cannot
drift from the detector it describes.

### §3.3 The seam — declared cause, measured duration

Cause codes declared in `VALID_REASON_CODES["DATA"]`: **`PROCESS_RESTART`**, **`POLICY_SHUTDOWN`**,
**`OPERATOR_STOP`**, plus the refusal **`SEAM_CAUSE_UNDECLARED`**.

- **Genuinely emitted, not merely constants.** `CorpusLedger.open_seam` validates the cause against
  the closed set and writes it as the seam record's `reason_code`.
  `test_every_seam_cause_is_genuinely_producible` drives all three through the real writer and reads
  each back **off disk**. The vocabulary guard's own docstring admits its weak half —
  *"declared⇒producible is satisfied ... by its CONSTANT DEFINITION, or even a COMMENT/DOCSTRING
  mention, not only by a genuine emit"* — so a tuple alone would have passed the scan while emitting
  nothing.
- **The cause is operator-declared, never inferred.** A process cannot observe why it died: a policy
  SIGKILL, a manual stop and a host crash are byte-identical from inside. `open_seam` REFUSES an
  undeclared cause, and the runner's preflight goes RED when a resume owes one. A guessed cause is a
  smoothed seam (§0.4).
- **TRUE duration, measured at both ends.** `resumed_first_frame_utc − prior_last_frame_utc`. The
  left bound is read from the **last line of the prior run's newest segment** — which survives a
  SIGKILL, unlike a manifest written in a `finally` block. A torn trailing line is skipped, never
  guessed. An OPEN seam reports duration `None`, never `0.0`.

**SEAM_CAUSE_UNDECLARED was itself caught by the guard.** On first run the vocabulary scan failed:
`reason codes EMITTED in production but NOT DECLARED: ['SEAM_CAUSE_UNDECLARED']`. The colon-form
refusal message is an emission. Declared, and recorded here because the guard biting during
development is evidence it works.

### §3.4 No book state across a resume — **SATISFIED BY EXISTING MACHINERY, NOT REBUILT**

A resume is a **new process**: a new adapter with an empty book, connecting fresh. There is no
carry-over path to sever. D45's addition (a) — the resume snapshot's checksum must validate before
any `MarketState` emits — **is** FR-018a(d), already enforced at `kraken_v2_book.py:1901-1938`: a
snapshot whose computed CRC32 does not match the venue's token calls `_enter_resync` and returns
`None`, and only a validated snapshot clears `_awaiting_resync`. A resumed segment starts life
proven, by the same code path that governs every mid-run resync.
**Behaviour on failure (asked explicitly):** it retries via reconnect; if the venue stays
unreachable the breaker STOPs the run under §4.2. It never emits from an unvalidated book.
No new code was written for this condition. The bite proof's P4 confirms it empirically: each run's
gap ledger carries its own distinct `run_start` wall anchor.

### §3.5 Corpus-spanning manifest

`CORPUS_MANIFEST.json` holds every run, every segment with its SHA-256 and originating `run_id`,
every seam as a first-class record, and a computed `progress` block. Segments carry
`hashed_at_capture` (see §2(b)).

### §3.6 Default-deny reader — **NO NEW READER LOGIC NEEDED (no-op, with the reason)**

**The reader does not exist yet.** `kraken_v2_book.py:3194` states it plainly: *"The default-deny
corpus reader (a later WO) consumes gaps + the run anchor."* There is therefore no reader logic to
change, and no finding to STOP on.

That is the trivial half. The substantive half is that the seam was deliberately shaped so the
reader **will not** need new logic when it is built: `SeamRecord` mirrors `GapRecord` — OPEN →
RESOLVED, write-through JSONL, and an unresolved record reporting duration `None` (read as
+infinity) so it intersects every later query and denies by construction. A reader that denies
across `duration is None` denies across both. Pinned by
`test_open_seam_has_no_duration_and_denies`.

### §3.7 Cumulative-hours accounting

`CorpusManifest.progress()` answers, at any time, from committed artifacts alone:

```
runs · cumulative_hours · target_hours · remaining_hours · seam_count · open_seams
seam_seconds · seam_causes · unfinalized_runs · complete
```

CLI: `python tools/live_corpus_capture.py --corpus-id <id> --progress` (opens no socket, runs no
preflight).

**Coverage = Σ over runs of (last frame − first frame) − recorded in-run gap seconds.** A gap is a
window with no data; crediting it would claim hours the corpus does not have. Seams are excluded by
construction — they sit *between* runs — but are reported separately so the corpus's real wall-clock
footprint is visible next to its labeled coverage.

---

## ⚠ FOR THE LEAD — "24 CUMULATIVE HOURS" MEANS 24 HOURS OF **DATA COVERAGE**, NOT 24 HOURS OF WALL CLOCK

This is the single most consequential definition in the WO, so it is stated plainly rather than left
implicit in the accounting code.

```
cumulative_covered_hours = Σ over runs of (last_frame − first_frame)  −  in-run gap seconds
elapsed_wall_hours       = earliest first frame → latest last frame   (seams and gaps included)
```

**Consequences the lead should rule against:**

1. **The capture must run LONGER than 24 wall-clock hours to reach the target.** Covered time is
   strictly less than elapsed time whenever the corpus has any gap or seam at all — which it will.
   The excess equals exactly the excluded gap + seam time.
2. **Sufficiency is judged against the covered number**, per §5.4 / condition 5 / D-r13. A run is
   never stretched or padded to hit it.
3. **A reader who mistakes covered for elapsed would declare the corpus complete EARLY.** That is
   the most damaging misreading available here, and it is the reason the metric is not merely
   documented but *labeled in the data itself*.

**How the labeling prevents it.** The old ambiguous keys (`cumulative_hours`, `remaining_hours`,
`target_hours`) are **removed**, not aliased — a stale reader gets a loud `KeyError` rather than
silently reading the wrong number. `progress()` now emits:

```json
{
  "metric": "cumulative_covered_hours = SUM over runs of (last_frame - first_frame) MINUS in-run
             gap seconds. Seams BETWEEN runs are excluded from coverage and reported separately.
             This is DATA COVERAGE, not elapsed wall-clock time.",
  "cumulative_covered_hours": 0.0,
  "target_covered_hours": 24.0,
  "remaining_covered_hours": 24.0,
  "complete": false,
  "not_the_metric": "elapsed_wall_hours is NOT the target. Reaching the target always takes MORE
                     wall-clock time than covered time, by exactly the excluded gap + seam time
                     below.",
  "elapsed_wall_hours": 0.0,
  "excluded_in_run_gap_hours": 0.0,
  "excluded_seam_hours": 0.0
}
```

The `metric` / `not_the_metric` strings travel **with** the data, so the distinction survives being
pasted into a report, a ticket, or a chat message — the places where a bare number loses its
definition. The console output at run end carries the same split, with the explicit note that
*"reaching it always takes MORE than 24 wall-clock hours."*

Pinned by `test_covered_hours_are_labelled_distinctly_from_elapsed_wall_hours`, which asserts the
identity `covered + excluded_gaps + excluded_seams == elapsed`, asserts `covered < elapsed` whenever
a gap or seam exists, and asserts the old ambiguous keys are **absent**.

**Reconciliation.** `CorpusLedger.reconcile()` folds in any run whose process died before
finalizing, so a SIGKILL does not make real hours invisible to the meter. Such runs are marked
`finalized=False` with `hashed_at_capture=False` segments — counted, but never dressed as
self-finalized.

### §3 BITE PROOF — `tools/wo044_resume_bite_proof.py` — **VERDICT: PASS**

A capture child is started, **killed mid-run** (`TerminateProcess` — unblockable, so no `finally`
and no `MANIFEST.json`: the exact shape of the two runs the shutdown policy ate), then **resumed
under the same corpus-id** in a second child. A same-process simulation would have assumed away the
thing under test.

| | Pristine | Mutated | Restored |
|---|---|---|---|
| P1 seam ledgered, cause `POLICY_SHUTDOWN` | ✅ | ✅ | ✅ |
| P2 duration is MEASURED | ✅ 4.977s | ❌ reported 0.0 vs independent 4.987s | ✅ 4.977s |
| P3 own preflight per run | ✅ | ✅ | ✅ |
| P4 distinct run anchors (fresh book) | ✅ | ✅ | ✅ |
| P5 manifest spans runs, all hashed | ✅ | ✅ | ✅ |
| P6 cumulative sums correctly | ✅ | ✅ | ✅ |
| **verdict** | **PASS** | **FAIL** | **PASS** |

**Mutation:** `SeamRecord.duration_seconds` → constant `0.0` — a **smoothed seam**, the precise
dishonesty §0.4 forbids. P2 fails alone; P1/P3/P4/P5 hold. `DISCRIMINATION: True`.
**sha256 exact-restore:** `5cb9b3d009e962cbbddce2bb9820a8102ae9d4402eb9342958e8c5f474917a11`
identical before and after.

P6 was initially **vacuous** — runs spanned milliseconds, so "hours sum correctly" compared 0 to 0.
Frames are now paced so each run has a measurable span, and the property asserts a non-zero
expectation. Recorded because a proof that passes on nothing is worse than no proof.

---

## §4 THE LONG-OUTAGE POLICY — X = 15 MINUTES

`RECONNECT_MAX_FAILURE_SECONDS: 600.0 → 900.0` (`kraken_v2_book.py:1047`).

### The measured justification — not doctrine

This is the **first value of this constant chosen against an observed failure** rather than derived
from documented silence. The old comment set T=600s with the caveat *"conservative and revisable
once the 24h run yields data."* **The run yielded the data.**

Corpus run `20260729190849` died on this exact constant. From `run_output.log.err`:

- Outage ran **20:49:30Z → 20:59:41Z ≈ 611s** of continuous retry.
- **23 logged reopen attempts**, alternating `TimeoutError: timed out during opening handshake` and
  `ConnectionResetError: [WinError 64] The specified network name is no longer available`.
- Breaker tripped at 600s, ending a healthy **1h51m** capture holding **462,155 frames**.
- Last validated book preserved: bid `63512.8` / ask `63512.9`, checksum `872323701`.

`[WinError 64]` is a **local link** failure. The venue was not gone; the host's network was briefly
down. **600s was measured to be too tight by roughly one attempt.** 15 minutes tolerates it with
margin.

Attempt rate is unchanged per-minute (emergent from T): at cap 30s with full jitter, ~60 attempts
across 900s ≈ 4/min. Observed in the real outage: 23 attempts / 611s ≈ 2.3/min.

### §4.1 / §4.2 — behaviour unchanged, tolerance widened

The whole outage remains **ONE gap record** with its TRUE duration, the retry ladder riding along as
`retry_ladder` (D-r10 machinery untouched). The breaker remains the **sole run-terminator** and
still STOPs with the full forensic tail. A longer tolerated outage is a longer **honest** gap, never
a hidden one.

### §4.3 — the independence boundary, and why it is the important half

Widening T makes long outages ordinary. If the suspend detector went quiet inside one, the corpus
would relabel *"the machine was asleep"* as *"we were patiently waiting"* — and every affected
window would be trusted instead of VOIDed under D24. **Patience toward the network must not extend
to the clock.** Proved in both directions, so the detector can be neither deaf nor trigger-happy.

### §4 BITE PROOF — `tools/wo044_outage_bite_proof.py` — **VERDICT: PASS**

`tests/integration/test_outage_policy.py` — 6 tests covering all three §4.4 cases.

| Artifact | Result |
|---|---|
| 1 — PRISTINE | 6 passed |
| 2 — MUTATION A: window reverted to 600s | 2 failed, 4 passed — **exactly** the two window tests |
| 3 — MUTATION B: suspend bound 43s → 1e9 | 1 failed, 5 passed — **only** the independence proof; the preservation dual still PASSES |
| 4 — RESTORED | 6 passed |

`MUTATION A discriminates: True` · `MUTATION B discriminates: True`
**sha256 exact-restore:** `3cb16565f881488509e4b4c1ec72c6fe15301c64f80e422258bc34ec24c7a3af`
identical before and after.

Two independent mutations, each caught by its own test — a proof that fails on everything is as
uninformative as one that fails on nothing.

**HONEST FIXTURE LIMIT (rule 0.1f):** simulated transport throughout, and T is scaled down so the
breaker branch runs in milliseconds. What is proved is the **policy shape** — one record, true
duration, tail retained, independence. Kraken's real reopen behaviour at 15 minutes is confirmed
only by a live run.

---

## ADDITIONAL FINDINGS (repaired, reported)

1. **`run_id` was generated twice** (`__init__` and again in `run()`), so the preflight announced a
   segment path the run never wrote to. Now generated once.
2. **`NameError` in the `finally` block.** `utc_now` was bound only inside the rotation branch, so a
   run ending before its first frame raised `NameError` during finalization and **masked the real
   capture error** with a bookkeeping one. Now bound unconditionally.
3. **Terminal vs incomplete gaps were conflated.** `gap_summary` counted a breaker-terminal gap as
   an "incomplete ledger". A terminal gap is COMPLETE by construction — a *known* open-ended gap —
   and reporting the breaker doing its job as a fault would make a genuinely deficient ledger
   indistinguishable from a clean STOP. Surfaced by real data: run `20260729190849` reported
   `incomplete_gaps: 1`. Now three outcomes: resolved / terminal / incomplete.
4. **`captures/` was untracked AND unignored.** A plain `git add -A` would have committed the entire
   corpus — hundreds of MB today, ~5.3 GB/day at full rate — into history where it could not later
   be removed. Added to `.gitignore` with the reason. The corpus is an archive; its provenance
   (`CORPUS_MANIFEST.json`, `seam_ledger.jsonl`, gap ledgers, `PREFLIGHT.json`) lives with the data.
5. **A regression I introduced, then fixed.** `CorpusLedger` creates its corpus directory on
   construction, and the runner now opens one during PREFLIGHT — so the corpus-runner tests, whose
   fixture set `CORPUS_DIR=test_captures/corpus_24h` (repo-relative), began littering the working
   tree with corpus dirs and `PREFLIGHT.json` files on every run. The fixture now points at
   `tmp_path`. Same family as WO-026's finding: an instrument must not write where it is not
   invited.

---

## SRC DISPOSITION

| File | Change |
|---|---|
| `src/trading/data/corpus.py` | **NEW** — seam records, corpus manifest, cumulative accounting, reconciliation |
| `src/trading/logkit/decision.py` | +4 declared reason codes (3 seam causes + 1 refusal) |
| `src/trading/data/adapters/kraken_v2_book.py` | `RECONNECT_MAX_FAILURE_SECONDS` 600.0 → 900.0 + rationale |
| `tools/live_corpus_capture.py` | corpus-id, per-run preflight record, executed 3.7 guard, seam open/close, corpus manifest, `--progress` |
| `tools/wo044_resume_child.py` | **NEW** — bite-proof child (paced scripted transport, no network) |
| `tools/wo044_resume_bite_proof.py` | **NEW** — §3 bite proof |
| `tools/wo044_outage_bite_proof.py` | **NEW** — §4 bite proof |
| `tests/test_corpus_resume.py` | **NEW** — 17 tests |
| `tests/integration/test_outage_policy.py` | **NEW** — 6 tests |
| `tests/test_live_corpus_capture.py` | fixture `CORPUS_DIR` → `tmp_path` (finding 5) |
| `.gitignore` | `/captures/` + `/nul` (finding 4) |

`git diff --stat -- src/`: `kraken_v2_book.py` +36/−9, `decision.py` +27/−0, plus the new
`corpus.py`. Post-change src sha256 (first 16):

```
ca7e9a85b491ab96  src/trading/data/corpus.py                  (new)
2905f7e119c27a57  src/trading/logkit/decision.py              (+4 declared codes)
3cb16565f8814885  src/trading/data/adapters/kraken_v2_book.py (600.0 -> 900.0)
103a8ba793c6c1d2  src/trading/data/adapters/factory.py        (UNCHANGED — matches WO-040)
5bf833c78fd3b91e  src/trading/data/adapters/registry.py       (UNCHANGED — matches WO-040)
```

---

## ACCEPTANCE

- [x] Run-3 eligibility verdict with evidence — **MACHINERY-VALIDATION-ONLY**, cumulative starts at 0
- [x] Resume support built; five conditions + D45's two additions; resume bite proof PASS
- [x] Outage policy at 15 min; three-case bite proof incl. suspend-during-outage independence — PASS
- [x] Seam cause codes declared in the vocabulary
- [x] Reader unchanged — no-op recorded with its reason (the reader does not exist yet)
- [x] Cumulative-hours accounting works (`--progress`)
- [x] Corpus-spanning manifest; per-run preflight records; every seam ledgered
- [x] **279 passed, 2 skipped — BOTH interpreters, BOTH orders** (see below)
- [x] **CI GREEN BOTH LEGS on the pre-capture commit `4d3898a` — run `31048238985`**
- [ ] §5 run and accumulate — **NOT BEGUN** (operator prerequisite unconfirmed)

### CI — the real run on THIS commit

**Commit:** `4d3898a` (pushed `0425ec6..4d3898a`) · **CI run `31048238985`** · triggered via push.

| Job | ID | Duration | Result |
|---|---|---|---|
| `test (3.14)` | 92448982091 | 10m26s | ✅ **279 passed, 2 skipped** (290.83s) |
| `test (3.11)` | 92448982251 | 10m8s | ✅ **279 passed, 2 skipped** (289.79s) |

Counts read from the job logs, not inferred from the ✓ — both legs ran the randomized-order step
and reported 279/2. (CLOSEOUT-1 lesson: a prior commit's green does not cover this one, and a green
checkmark is not a test count.)

Non-blocking annotation on both jobs: `actions/checkout@v3`, `actions/setup-python@v3` and
`codecov/codecov-action@v3` target Node.js 20, which GitHub now forces onto Node 24. A deprecation
warning, not a failure — recorded here rather than left for someone to rediscover as a surprise
when the forcing becomes a hard break.

### Test results

| Leg | Interpreter | Order | Result |
|---|---|---|---|
| dev | CPython 3.14.6 | `-p no:randomly` | **279 passed, 2 skipped** (296.78s) |
| acceptance | CPython 3.11.15 (throwaway uv venv) | `-p no:randomly` | **279 passed, 2 skipped** (295.66s) |
| order-dependence | CPython 3.14.6 | `--randomly-seed=20260806` | **279 passed, 2 skipped** (296.44s) |

**Count arithmetic:** 256 at base + 17 (`tests/test_corpus_resume.py`) + 6
(`tests/integration/test_outage_policy.py`) = **279**.

Auxiliary gates: `lint-imports` **6 kept / 0 broken** · `ruff` all checks passed · annotation scan
**0** · `preflight_path_check` PASS · `wo029_reverify_partition` PASS **31/31** ·
`git status --porcelain evidence/` **EMPTY** after full runs.

---

## §5 — NOT BEGUN, AND WHY

§5.1 requires §3/§4 committed green with CI **before** capturing. Beyond that, the WO's stated
**OPERATOR PREREQUISITE** — the security policy that shuts the machine down must be DISABLED and
confirmed — has not been confirmed, and cannot be established from inside the repo. That policy
already cost two runs (`20260729044021` at ~2h37m and `20260730152029` at ~3h55m, both killed with
no manifest). Starting a fourth run without that confirmation would be the same experiment a third
time.

Also required before launch: **`DATA_SOURCE=kraken_v2`** must be set for the run. `.env` ships
`DATA_SOURCE=simulated`, which is what killed run `20260730151934` instantly with
`LIVE_CAPTURE_UNSUPPORTED`.

**Resume command shape once cleared:**

```bash
# first run of a corpus
CORPUS_ID=corpus_<id> DATA_SOURCE=kraken_v2 TRADING_ENV=paper \
  python tools/live_corpus_capture.py --corpus-id corpus_<id>

# every resume — the seam cause is REQUIRED and operator-declared
python tools/live_corpus_capture.py --corpus-id corpus_<id> --seam-cause POLICY_SHUTDOWN

# progress at any time
python tools/live_corpus_capture.py --corpus-id corpus_<id> --progress
```
