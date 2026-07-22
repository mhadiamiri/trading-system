# WO-018 FOLLOW-UP — FINAL REPORT: rule 0.1k, the prose-as-use doctrine, and the dead/live split

**Baseline:** `f3052e7` (WO-018 follow-up A–D, pushed) → this commit. **Report only** except the two
recordings the lead dictated (0.1k, the doctrine line). **NO taxonomy migration, NO tightened scan, NO
wiring/retiring** — the successor WO's work. **NO VENUE CONNECTION.**
Evidence: `evidence/WO-018/dead_live_split.txt`.

---

## 1. New standing rule 0.1k (recorded verbatim)

Added to `docs/standing-rules.md` (its canonical home; "Last amended" bumped to 2026-07-22):

> **0.1k A BEHAVIORAL PROOF IS SOVEREIGN OVER A STATIC SCAN.** If the tightened scan flags a code with a
> passing behavioral proof, THE SCAN IS WRONG, NOT THE CODE.
> Evidence-competence hierarchy: **BEHAVIORAL DEMONSTRATION > STATIC REACHABILITY > DEFINITION > PROSE.**

## 2. Prose-as-use doctrine line (recorded verbatim)

Added to the decision log `docs/decisions/2026-07-22-a-check-is-bounded-by-the-form-it-matches.md`:
*"PROSE MAY ANNOTATE EVIDENCE, NEVER CONSTITUTE IT … this is DOCUMENTATION LOAD-BEARING INSIDE A
MECHANICAL PROPERTY."* (full text in the log). The split below honours it: every classification cites
`file:line`.

## 3. The three-part split (report only — the task)

Applied **namespace-scoped** per the ruling (production counts only within a token's declared namespace).
Verified emission facts: risk decisions log `event_type=decision.value` + `reason_code=<RISK_* string>`
(`live.py:245-255`); no `reason_code=decision.value` exists anywhere; fills/rejects emit
`event_type="ORDER_FILLED"/"ORDER_REJECTED"` with `reason_code="EXEC_ORDER_FILLED"`/`e.reason_code`
(`live.py:279-312`). So `PASS/CLAMP/VETO/ORDER_FILLED/ORDER_REJECTED` never occupy a reason_code position.

**GENUINELY DEAD in the reason_code namespace — 5** (no reference, no proof *as a reason_code*; the
identical string is a live event_type):

| code (as reason_code) | why dead | string lives as event_type |
|---|---|---|
| `PASS`, `CLAMP`, `VETO` | emitted only via `event_type=decision.value`; reason_code carries `RISK_*` | `VALID_EVENT_TYPES["RISK"]`, emitted `live.py:247` |
| `ORDER_FILLED` | fill's reason_code is `EXEC_ORDER_FILLED` | `VALID_EVENT_TYPES["LOOP"]`, emitted `live.py:281` |
| `ORDER_REJECTED` | reject's reason_code is `e.reason_code` | `VALID_EVENT_TYPES["LOOP"]`, emitted `live.py:306` |

→ Fork (successor WO): **RETIRE the reason_code declaration** for all five — no audit vocabulary is lost
(each is a live, declared event_type). Matches the ruled taxonomy migration. No wiring candidate here.

**LIVE-BUT-INVISIBLE — 11** (a real emission path via constant/enum/variable/f-string indirection **and**
a passing behavioral proof; the literal scan cannot see any of them):

| # | code | ns | reference | behavioral proof |
|---|---|---|---|---|
| 1 | `RISK_PASS` | rc | `engine.py:113/116` | `test_risk.py:59` |
| 2 | `RISK_CLAMP_MAX_POSITION` | rc | `engine.py:101/104` | `test_risk.py:86` |
| 3 | `RISK_VETO_KILL_SWITCH` | rc | `engine.py:80` | `test_risk.py:162` |
| 4 | `RISK_VETO_DAILY_LOSS` | rc | `engine.py:88` | `test_risk.py:136` |
| 5 | `RISK_VETO_INVALID_INPUT` | rc | `engine.py:84` | `test_risk.py:180` |
| 6 | `LONG_SIGNAL` | rc | `live.py:223`→`:248` (var) | `test_reason_code_emission.py:137` (in decision log) |
| 7 | `SHORT_SIGNAL` | rc | `live.py:223`→`:248` (var) | `test_reason_code_emission.py:151` (in decision log) |
| 8 | `MEAN_CYCLE_BASELINE_INSTRUMENT_MISMATCH` | rc | `host_baseline.py:74` (`f"{CONST}: …"`) | `test_mean_cycle_baseline_gate.py` + `evidence/WO-013/instrument_mismatch_bite_proof.txt` |
| 9 | `PASS` | et | `engine.py:116` → `decision.value` (`live.py:247`) | `test_risk.py:56` |
| 10 | `CLAMP` | et | `engine.py:104` → `decision.value` | `test_risk.py:82` |
| 11 | `VETO` | et | `engine.py:80/84/88` → `decision.value` | `test_risk.py:134/160/178` |

## 4. Size verdict — a verdict on the instrument

**Live-but-invisible = 11 of 16 (69%). Genuinely dead = 5 of 16.**

Raw size is **LARGE** — but the verdict is **ANNOTATE, do not iterate**, and the reason is rule 0.1k:

- Every one of the 11 has a **passing behavioral proof** (sovereign over any static scan). Liveness is
  already settled by the superior evidence class.
- A **third static iteration** would have to chase constant-return, enum-`.value`, variable, and
  f-string indirection to make the reachability scan "see" these — the exact arms race the lead named
  (*each audit finds the instrument committing a subtler version of the crime it polices*). Building it
  would **subordinate behavioral demonstration to static reachability, inverting 0.1k.**
- So the successor WO's bounded, one-time action for this partition: **inline annotation** beside each of
  the 11 declarations citing its behavioral proof (the `file:line` above), so the next audit never
  re-litigates a code a test already proves live.

**Conclusion:** LARGE in count, but the annotation workload is **SMALL and closed-form** (11 known proofs,
enumerated), and **no third scan iteration is warranted.** The scan's blindness to indirection is a
**declared limit** (follow-up B, now in the scan docstring), retired by behavioral sovereignty — not by
more grepping.

## 5. Hot-path judgment

**NOT hot path — no re-baseline.** This follow-up touched only `docs/standing-rules.md`, a decision-log
`.md`, an evidence `.txt`, and this report. **Zero `.py` changed** (`git status` confirms), so there is no
per-frame work to measure; a re-baseline would measure nothing.

## 6. Verification

- **No `.py` file changed** (src or test) — `git status --short` shows only 2 `.md` + 2 new `.txt/.md`.
  The WO-018-follow-up pytest result therefore **carries forward byte-for-byte: 215 passed deterministic
  (`-p no:randomly`, 245.94s) and 215 passed randomized (`--randomly-seed=20260730`, 245.81s)**, 0
  failed/xfailed/xpassed both orders. A re-run with zero code delta is measured ceremony, not evidence —
  argued out explicitly per the standing "must be argued OUT of" ethos, and per the WO-008b-B-RERUN
  precedent (tree byte-unchanged → prior green stands).
- `ruff check .` clean; `lint-imports` 6/6; `contract_count_check` 6/6 (re-run this commit; unchanged).
- **New code:** none (`producible_only_via_definition.py` shipped last commit). **Secret scan:** 0 hits
  (docs only). **local HEAD == remote HEAD:** pasted in the delivery / push output.

## 7. Answers

- **Venue connection?** NO. **HTTPS doc fetch?** NO.
- **Prose standing in for output?** NO — the split cites `file:line` for every row; 0.1k and the doctrine
  line are recorded verbatim in their canonical files.
- **Changed but not asked?** None beyond the update's items. Files: `docs/standing-rules.md` (0.1k),
  `docs/decisions/2026-07-22-a-check-is-bounded-by-the-form-it-matches.md` (doctrine line),
  `evidence/WO-018/dead_live_split.txt`, this report. `instructions.md` (lead's WO text) left uncommitted.
- **What could not be completed?** Nothing. The wire/retire and the inline annotations are deliberately
  left to the successor WO (authority boundary respected: genuinely-dead = retire candidate; live-but-
  invisible = touched only by annotation).

---
**STOP. WO-018 is closed.** Next by sequence: CI capture + version ruling → CI green → taxonomy-migration
WO (carrying: namespace-scoped bidirectional scan, prose-as-use closure, uppercase normalization,
dead/live split with behavioral sovereignty, the ruled taxonomy migrations) → 008c → 24h corpus.
