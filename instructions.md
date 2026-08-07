# WO-046 — 008c VALIDATION PHASE: the DEFAULT-DENY CORPUS READER.
#
# D20: "The guarantee moves from 'every consumer remembers to check metadata' (vigilance, 0-for-4)
# to 'the only way to get gap-spanning data is to have written code that asked for it' (mechanical)."

BASE: HEAD `89e5857` (WO-045 complete, CI green run 31185950085, 301 tests). Confirm in §1.
Reference artifact: `corpus_20260805` at `e4dde21` — 36.8867 covered h, 38 segments, 19 gaps, 1 seam.

SCOPE: build the reader, its bite proofs, and the read-only live query (finding 3). Commit green, STOP.
SHIP IMPACT: **YES** — new production module in the Data layer. Full discipline.
NOT IN SCOPE: the backtest itself; strategy; cost model. This builds the READ boundary only.

**`captures/corpus_24h/corpus_20260805/` is the ratified reference artifact. READ it; never write to
it. Snapshot its digest before and after and prove it untouched (WO-045's practice).**

---

## §0 RULES OF ENGAGEMENT
0.1 No discretion. Code wins: STOP and report.
0.3 Fail-then-pass bite proofs, four artifacts, sha256 exact-restore, both directions.
0.4 Preservation duals mandatory, local and direct. **S13: refusal and preservation in ONE test.**
0.5 Report every attempt.
0.6 AUTO MODE OFF — new production module.
0.7 **BUILT-VS-OPERATED (D24).**

    | Thing | Status | Built & verified where |
    |---|---|---|
    | Gap-record schema (the CONTRACT the reader conforms to) | **OPERATED** | specified WO-014c — READ IT FIRST, §2 |
    | `corpus_20260805` ledger, seam ledger, manifests | **OPERATED — READ ONLY** | `e4dde21`, ratified D46 |
    | `GapLedger` zero-duration declared limit | **OPERATED** | `kraken_v2_book.py` docstring, WO-022 §3.2 |
    | `--progress`'s live-run refusal heuristic | **OPERATED** | WO-045 §4 — the reader SUPERSEDES it, §5 |
    | The default-deny reader | **THIS WO IS THE BUILDER** | §3 |

---

## §1 CONFIRM STATE + READ THE CONTRACT
HEAD, test count both interpreters (301 at base — derive, don't assume), `git diff -- src/` clean,
all gates, partition 31/31. Snapshot `corpus_20260805`'s 88-file digest (`a025db1e…`) before any work.

**Then read, and paste, the gap-record schema as WO-014c specified it** — field names, types,
semantics of `open`/`close`/`duration_s`/`cause`/`gap_id`. D20: *"the reader inherits whatever the
capture happened to write"* is fixtures-shaped-to-the-implementation one layer up. **The reader
conforms to the declared schema; if the corpus's actual ledger DIVERGES from the declared schema,
that is a finding — STOP and report it** rather than conforming to the divergence.

Also read the SEAM record's shape (`seam_ledger.jsonl`, WO-044 §3.3) and confirm d45's ruling holds:
**a seam is a gap with a bigger cause code** and needs no separate reader logic. If it needs
different handling, that is a finding.

---

## §2 THE READER'S CONTRACT (hard spec — implement exactly this)

2.1 **Default-deny at the read boundary.** A consumer requests a time window. If the window spans
    ANY recorded gap or seam, the reader REFUSES by default — either raises naming the gap's
    IDENTITY (`gap_id`, cause, bounds, duration) or returns EXPLICITLY SEGMENTED data.
    **Continuous-looking data across a gap must not be expressible by the API.** A caller who writes
    the obvious thing gets a refusal, not a silent splice.
2.2 **Acknowledgment: explicit, per-request, gap-class-aware.** A consumer may accept some gap
    classes (e.g. sub-second `KEEPALIVE_RECONNECT`) for its purpose — but states so IN CODE, PER
    REQUEST, PER CLASS. Not a global flag, not a config default, not omission. Design it so the
    acknowledgment names WHAT is being accepted (cause class and/or duration bound), so a reader of
    the calling code can see what was tolerated.
2.3 **A ZERO-DURATION GAP IS A REAL GAP AND TRIGGERS DEFAULT-DENY** (precondition 5, hard spec).
    Overlap tests use **INCLUSIVE** bounds. Zero-duration entries are NEVER filtered as noise.
    *A reader that launders an honest ledger is default-deny's failure mode arriving one layer
    downstream.*
2.4 **Seams too** (d45): the 2.1061 h `PROCESS_RESTART` seam in `corpus_20260805` is a gap with a
    bigger cause code. A window spanning it refuses by default like any other.
2.5 The reader is READ-ONLY: it must never write to the corpus directory. Enforce mechanically if
    cheap (the WO-032 evidence-write-boundary precedent) — at minimum, prove it in §4.

---

## §3 BUILD
Place it in the Data layer; `lint-imports` must stay 6/6 (a reader is a data-layer concern; if the
boundary contracts push back, that is architecture telling you something — report it, don't relax a
contract). Declare any new reason codes properly (producible, prefix-free — the guard has bitten
twice in two WOs and was right both times).

---

## §4 BITE PROOFS (0.3/0.4 — four artifacts each, sha256 exact-restore)

4.1 **The D20 proof, both shapes in ONE test (S13):**
    - **REFUSAL:** a corpus fixture with a KNOWN gap; request a spanning window WITHOUT
      acknowledgment → REFUSES, naming the gap's identity.
    - **PRESERVATION DUAL:** the same request WITH the correct acknowledgment → SERVES.
    - **NECESSITY MUTATION:** neuter the gap check → the refusal half fails, the dual still passes.
4.2 **Zero-duration fixture (precondition 5, hard spec):** a gap whose open == close. Request a
    window spanning it without acknowledgment → REFUSES. Prove inclusive bounds: a window whose
    boundary EQUALS the gap's timestamp still refuses.
4.3 **Seam-spanning:** a window spanning a `PROCESS_RESTART` seam refuses by default; with
    acknowledgment, serves — proving d45's "no separate reader logic" claim by demonstration.
4.4 **Class-awareness:** acknowledging class A does NOT admit a gap of class B. An acknowledgment
    that admits everything is not gap-class-aware — mutate it to a blanket accept and show a test
    fails.
4.5 **Read-only:** run the full reader test suite, then confirm the corpus directory digest is
    unchanged. `git status --porcelain` on the corpus path empty.

**Fixtures are synthetic and in-repo** (deterministic, always runnable, no 700 MB dependency).

---

## §5 VALIDATE AGAINST THE REAL CORPUS (this is the "validation phase")
Separately from the unit fixtures, run the reader against `corpus_20260805` READ-ONLY and report:
- total windows requested, refusals, and that every refusal names a REAL ledger gap;
- that all **19 gaps and the 1 seam** are visible to the reader and each triggers default-deny;
- a window entirely inside one continuous stretch serves without acknowledgment (the dual, at scale);
- the corpus digest UNCHANGED after the validation pass (`a025db1e…`).
This is evidence in the report, NOT a committed test (no test may depend on the 700 MB artifact).

---

## §6 FINDING 3 — THE READ-ONLY LIVE QUERY (D46 folded it here)
`--progress` is a writer: it calls `reconcile()`, which saves `CORPUS_MANIFEST.json`. Build the
read-only path the reader makes possible: query a corpus's coverage/seams/gaps **without writing
anything**, safe against a live run. Then: WO-045's live-run refusal heuristic becomes unnecessary
for the read-only path — state whether it is retired, kept for the writing path, or narrowed, and
why. Prove no-write (digest unchanged with a run in progress, or the closest safe equivalent).

---

## §7 ACCEPTANCE
- Schema read and conformed to (or divergence reported as a finding)
- Default-deny implemented per §2.1–2.5; acknowledgment explicit/per-request/class-aware
- Bite proofs 4.1–4.5, four artifacts each, sha256 exact-restore, necessity mutations discriminating
- Real-corpus validation: 19 gaps + 1 seam all trigger default-deny; digest unchanged
- Read-only live query built; `--progress` disposition stated
- `corpus_20260805` byte-untouched — digest before and after
- Test count with arithmetic, both interpreters, both orders
- lint 6/6 · contract 6/6 · ruff · annotation 0 · preflight · partition 31/31
- Commit, push, local == remote, CI GREEN both legs — REAL run number, **counts pulled from the job
  logs** (a green ✓ says the job exited zero, not what it ran)

## §8 REPORT — `WO-046-REPORT.md`
The schema as read; the reader's contract as built; all bite proofs verbatim with sha256 and their
discriminating mutations; the real-corpus validation with the 19+1 accounting; the read-only query
and the `--progress` disposition; corpus-untouched digests; src hashes; CI with log-derived counts;
every attempt; any STOP.

**THEN STOP.** Next: **the first backtest measured against `corpus_20260805`** — the unified cost
model's first encounter with real recorded market data.