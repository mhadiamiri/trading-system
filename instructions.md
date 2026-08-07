# WO-045 — BOUNDED RETENTION for captured_raw_text + the termination-log-level fix.
#
# D46: the failure mode is a MISATTRIBUTION — unbounded retention → memory pressure → swap →
# event-loop starvation → HEARTBEAT_ABSENCE: a HOST problem entering the ledger wearing a VENUE
# problem's cause code. Precisely the confusion the suspend detector exists to prevent, arriving
# through a different door.

BASE: HEAD `e4dde21` (WO-044 complete, corpus_20260805 ratified). Confirm in §1.
284 both interpreters at last CI (run 31050446103). MANDATORY before any multi-day or resume-heavy
capture (D46).

SCOPE: §2 bounded retention with declared cap + count-past-cap; §3 the termination-log-level fix
(finding 2). Commit green, STOP.
SHIP IMPACT: **YES** — `kraken_v2_book.py` retention path + log levels. Full discipline.
NOT IN SCOPE: finding 3 (read-only live-corpus query) — D46 assigned it to the default-deny reader
WO. Declare the interim restriction (§4) but build nothing for it here.

---

## §0 RULES OF ENGAGEMENT
0.1 No discretion. Code wins: STOP and report.
0.3 Fail-then-pass bite proof, four artifacts, sha256 exact-restore, both directions.
0.4 Preservation duals mandatory, local and direct.
0.5 Report every attempt.
0.6 AUTO MODE OFF — production edit to the capture adapter.
0.7 **BUILT-VS-OPERATED (D24).**

    | Thing | Status | Built & verified where |
    |---|---|---|
    | `FAILURE_CAPTURE_CAPPED` + count-past-cap (the PRECEDENT to follow) | **OPERATED** | pre-existing failure-capture path — read it before building |
    | `captured_raw_text` unbounded retention | **OPERATED — DEFECTIVE** | `kraken_v2_book.py:2956`, measured 35–48 MB/h |
    | Corpus `corpus_20260805` | **OPERATED — RATIFIED, DO NOT TOUCH** | `e4dde21` |
    | The retention cap + its derivation | **THIS WO IS THE BUILDER** | §2 |

---

## §1 CONFIRM STATE
HEAD, test count both interpreters (state the real number — the WO does not assert one; WO-044's
figures were 279→284, derive from the tree), `git diff -- src/` clean, CI green, lint 6/6, ruff,
annotation 0, preflight, partition 31/31.

**Do not modify anything under `captures/corpus_24h/corpus_20260805/`.** It is the ratified
reference artifact. Confirm it is untouched at the end (§5).

---

## §2 BOUNDED RETENTION — follow the FAILURE-CAPTURE PRECEDENT (D46)

2.1 **Read the precedent first.** `FAILURE_CAPTURE_CAPPED` already implements bounded retention with
    count-past-cap. Paste its mechanism (cap constant, where the cap is enforced, how past-cap
    events are counted and surfaced). The new cap MIRRORS this shape — do not invent a second
    pattern for the same problem.
2.2 **Cap the retention** at `kraken_v2_book.py:2956`. `captured_raw_text` retains every raw wire
    message for the life of the run; run 2 ended near 1.6 GB private at 35–48 MB/h.
    - A DECLARED cap (constant, named, with its derivation in a comment).
    - **Count-past-cap semantics:** messages beyond the cap are not silently dropped — the count is
      retained and surfaced, same as the failure-capture path. A silent drop would make a
      memory-bounded run indistinguishable from a quiet one.
    - A declared reason code if one is emitted (mirror `FAILURE_CAPTURE_CAPPED`'s form; if you add
      one it must be genuinely producible, not a constant — WO-037/WO-044 both caught dead ones).
2.3 **DERIVE the cap against the measurement, and state the derivation** (D46 is explicit: derive
    from 35–48 MB/h). State: the chosen cap in both messages and MB, the hours of capture it
    permits at the measured rate, and why that headroom is right for a multi-day run. A cap chosen
    without arithmetic against 35–48 MB/h does not satisfy the ruling.
2.4 **The corpus is unaffected but the condition is SCALE-DEPENDENT** — 1.6 GB peaked comfortably on
    this host; the next capture may not. State what the cap makes safe (e.g. "N days at the measured
    rate within M GB") so the bound is a claim someone can check, not a vibe.

### §2 BITE PROOF (0.3/0.4 — four artifacts, sha256 exact-restore)
- **BITE:** drive retention past the cap → retention stops growing at the cap AND the past-cap count
  increments and is observable. Prove the memory bound actually holds (measure retained size, don't
  assert it).
- **DUAL (local and direct):** under the cap → everything retained, count zero, no behavior change.
  A cap that truncates early is as wrong as one that never fires.
- **MUTATION (necessity):** remove/neuter the cap → the bite assertion fails, the dual still passes.
  Proves the cap enforces the bound, not something adjacent.
- Restore; sha256 == pristine; final artifact PASS.

---

## §3 THE TERMINATION-LOG-LEVEL FIX (finding 2 — D46 doctrine)

**Ratified doctrine, record it verbatim in a decision doc:**
> For unattended runs, any message that explains a TERMINATION logs at WARNING or above.
> **The line that says why it ended must never be the line that gets dropped.**

3.1 The clean-close reason is `logger.info` and was filtered out of the detached run's logs (which
    capture WARNING and above), so run 1's cause had to be derived by ELIMINATION rather than read.
    Raise it to WARNING (or above).
3.2 **Enumerate every termination path** and confirm each logs its reason at WARNING+: clean venue
    close, 24h deadline, breaker STOP, fatal guard STOP, and any other exit. This is the "enumerate,
    don't fix the one you found" discipline — one path was found because it bit; the others have not
    been checked. Report the full enumeration and which needed raising.
3.3 **Bite proof or equivalent evidence:** demonstrate a termination message now survives a
    WARNING-and-above filter. If a full bite proof is disproportionate for a log-level change, state
    the evidence you used and why it is sufficient — do not skip evidence, and do not pad it.
3.4 Record in the corpus's provenance that run 1's cause remains **inference** (cause-by-elimination,
    honestly labeled per D46) and that this fix makes the next such fact directly readable.

`docs/decisions/2026-08-07-the-line-that-says-why-it-ended.md` carries the doctrine.

---

## §4 DECLARE THE FINDING-3 RESTRICTION (do not build)
D46 assigned the read-only live-corpus query to the default-deny reader WO. Until it exists:
**no live `--progress` queries against a RUNNING capture** — `--progress` calls `reconcile()` and
writes `CORPUS_MANIFEST.json`, racing the capture. Record the restriction in `progress.md` and, if
cheap, make `--progress` REFUSE (or loudly warn) when the target corpus has a live run — but do NOT
build the read-only path here. If refusing requires detecting a live run and that is non-trivial,
declare the restriction in docs only and say so.

---

## §5 ACCEPTANCE
- Cap declared with its derivation stated against 35–48 MB/h; count-past-cap surfaced, not silent
- Bite proof: bite + dual + necessity mutation, four artifacts, sha256 exact-restore, memory bound
  MEASURED not asserted
- All termination paths enumerated; every reason logs WARNING+; evidence stated
- Doctrine decision doc committed
- Finding-3 restriction declared (and enforced if cheap)
- `captures/corpus_24h/corpus_20260805/` byte-untouched — confirm
- `kraken_v2_book.py` before/after sha256 (`3cb16565…` was WO-044's; state the real base); other src
  files unchanged unless a reason code was added (`decision.py`)
- Test count stated with arithmetic, both interpreters, both orders
- lint 6/6 · contract 6/6 · ruff · annotation 0 · preflight · partition 31/31
- Commit, push, local == remote, CI GREEN both legs — REAL run number, counts pulled from the job
  logs (the WO-044 practice: a green ✓ says the job exited zero, not what it ran)

## §6 REPORT — `WO-045-REPORT.md`
The failure-capture precedent as read; the cap, its derivation arithmetic, and what it makes safe;
the bite proof verbatim with sha256 and the MEASURED memory bound; the full termination-path
enumeration and which needed raising; the doctrine doc; the finding-3 declaration; corpus-untouched
confirmation; src hashes; CI run with log-derived counts; every attempt; any STOP.

**THEN STOP.** Next: 008c validation phase — the default-deny reader with gap enforcement (finding 3
folded in) → the first backtest against `corpus_20260805`.