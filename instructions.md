# WO-040 CLOSEOUT — fix the impossible p99, define the reference honestly, verify real CI.

BASE: HEAD at WO-040's evidence commit (state it). The MEASUREMENT is accepted: A3 driven through
`get_live_market_data(enable_instrument=True)`, 41/41 to MarketState, no sleep, footprint by
construction, median 0.031ms / p95 0.057ms / max 0.154ms plausible. **The p99 is broken and the
reference is defined against it.** Three fixes; no re-measurement of the loop.

SCOPE: §1 fix the percentile computation (P99 0.209 > MAX 0.154 is impossible); §2 redefine the
reference honestly for N=41; §3 real CI on the evidence commit + the actual 3.11 leg. Commit green,
STOP.
SHIP IMPACT: **NO** — harness/percentile fix (tools/, `.artifacts/`, evidence). `git diff -- src/`
empty vs `89a2842` (the instrument stays frozen — paste the diff). If a fix touches src, STOP.
REPORTING: PER-ITEM — this is the corpus reference.

---

## §0 RULES OF ENGAGEMENT
0.1 No discretion. Code wins: STOP and report.
0.2 No src change. The loop and instrument are frozen at `89a2842`. Only the measurement HARNESS's
    statistics code and the evidence declaration change. The raw per-frame samples are NOT re-measured
    unless §1 finds the samples themselves (not the percentile math) are wrong.
0.3 Report every attempt.
0.6 AUTO MODE OFF — verify the bar; §0.2 forbids any src edit.

---

## §1 FIX THE IMPOSSIBLE PERCENTILE (P99 > MAX)

The reported distribution is arithmetically impossible: **P99 (0.2090ms) > MAX (0.1538ms).** The 99th
percentile cannot exceed the maximum. On N=41, p99 ≈ the top sample; the computation is interpolating
past the array end or indexing wrong.

1.1 Show the percentile code in `tools/measure_real_loop_baseline.py`. Identify the bug (off-by-one,
    interpolation method producing a value above max, wrong index for small N, or reading a wrong
    field). State it.
1.2 Fix the statistics ONLY — not the samples. Re-compute median/p95/p99/max from the SAME 41 collected
    samples (they are in `.artifacts/WO-040/wo040_measurement_results.json` — use them; do not re-drive
    the loop unless the raw samples are themselves absent/corrupt, in which case re-drive A3 and say so).
1.3 **Sanity gate:** after the fix, assert MEDIAN ≤ P95 ≤ P99 ≤ MAX. If that ordering does not hold,
    the fix is wrong — STOP. Paste the corrected ordered distribution.
1.4 State whether the corrected p99 now equals or approaches max (expected on N=41 — the top 1% of 41
    samples is the top sample). If corrected p99 == max, say so plainly: at N=41, p99 and max are the
    same measurement, which is itself the small-N honesty point.

---

## §2 DEFINE THE REFERENCE HONESTLY FOR N=41 (the §2.5 caveat, applied not just stated)

WO-040 §2.5 correctly said "N too small for stable p99, use p95 for regression" — then §3.5 defined the
reference against p99 anyway. Resolve the contradiction in favor of the honest reading:

2.1 Define the corpus regression check against the statistic the sample actually supports. On N=41,
    p99 IS the max (one or two samples) — a threshold there flags only a new all-time-worst frame,
    which is noisy. State the reference USE against **p95** (0.057ms, well-supported by 41 samples) as
    the primary trip, with max/p99 reported as the observed ceiling but NOT the sole trip. Exact
    wording to declare: what fires, on which statistic, over how many consecutive frames, with the N=41
    limitation named in the reference itself.
2.2 State plainly what this baseline can and cannot support: median and p95 are usable references from
    41 real frames; the extreme tail (p99+) is provisional and should tighten when the corpus itself
    provides millions of real frames (the corpus run will produce a vastly larger real sample — note
    that the baseline is a PRE-corpus sanity reference, and the corpus's own data becomes the mature
    distribution). This frames the 41-frame baseline correctly: a plausibility gate, not the final
    performance model.
2.3 Re-declare `evidence/WO-040/baseline.json` with the corrected distribution and the honest reference
    definition. Preserve the correction chain (15.5ms → 0.542ms → 0.031ms real) AND annotate the p99
    correction (impossible→fixed) — annotate-not-rewrite; the p99 error and its fix are part of the
    evidence trail.

---

## §3 REAL CI ON THE EVIDENCE COMMIT + THE ACTUAL 3.11 LEG

3.1 WO-040 cited CI run `30399653951` — that is WO-039's run, not a run on WO-040's evidence commit.
    Commit the closeout (percentile fix + baseline.json), push, and run CI on THAT commit. Paste the
    REAL run number with both legs. (CLOSEOUT-1 lesson: a prior commit's green does not cover this one.)
3.2 The 3.11 leg was asserted "verified in prior work," not shown for this WO. Run it (the throwaway uv
    venv acceptance leg) and paste the actual 3.11 result for this commit. "237 both interpreters" must
    be demonstrated here, not inherited.
3.3 If either leg fails → STOP; a red leg on the corpus-reference commit is a finding.

---

## §4 ACCEPTANCE
- Percentile bug shown and fixed; MEDIAN ≤ P95 ≤ P99 ≤ MAX holds (paste); corrected distribution from
  the same 41 samples
- Reference redefined against p95 (primary), tail reported as provisional/observed-ceiling with N=41
  named in the reference; baseline.json re-declared, correction chain + p99-fix annotated
- `git diff -- src/` EMPTY vs `89a2842` (paste); five src sha256 identical (`2e0f8a13…`, `103a8ba7…`,
  `5bf833c7…`, `dab18f67…`, `3d153a11…`, `bd0747f…`)
- CI GREEN both legs on THIS closeout's commit (real run number, not WO-039's); 3.11 leg SHOWN for this
  commit, not inherited
- 237 both interpreters demonstrated; lint 6/6 · contract 6/6 · ruff clean · annotation 0 · preflight
- `wo029_reverify_partition.py` PASS 31/31

## §5 REPORT — `WO-040-CLOSEOUT-REPORT.md`
The percentile bug + fix + the ordered distribution; the honest reference definition (p95 primary, tail
provisional, N=41 named); the re-declared baseline.json; the REAL CI run on this commit both legs; the
shown 3.11 result; the empty src diff + five sha256; every attempt; any STOP.

**THEN STOP.** With a correct, honestly-bounded baseline: corpus preconditions (per-item, red lines
live here) → 24h corpus.