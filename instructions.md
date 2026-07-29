# WO-040 — THE REAL CAPTURE-LOOP BASELINE. Drive A3 through the real loop, measure real work.

BASE: HEAD `89a2842` (WO-039 flag committed, CI green `30399653951`). Instrument FROZEN at this commit.
234/237 both interpreters (237 with the perf/bite-proof tests). `git diff -- src/` must stay empty.

This produces the FIRST real capture-loop baseline — the reference the 24h corpus run is judged
against. Four prior attempts measured a sleep or a direct-construct harness; this one drives real
Kraken frames through the real production generator. It is the anti-VOID measurement done for real.

SCOPE: drive A3 through `get_live_market_data(enable_instrument=True)`, measure real
parse+CRC32+book-update+MarketState per frame, declare the baseline with seven dimensions +
host-suspend verified. Commit green, STOP.
SHIP IMPACT: **NO** — a measurement harness (tools/, `.artifacts/`) + evidence declaration. The
instrument is frozen; `git diff -- src/` MUST be empty vs `89a2842` (paste). If measuring needs an src
change, STOP — the instrument and the loop already exist; driving them needs a harness.
REPORTING: PER-ITEM (D43) — this is the corpus reference, a red-line-(c) declared figure.

WHAT THE INVESTIGATION ESTABLISHED (WO-040-PREP, committed):
- A3 (`tests/fixtures/kraken_v2_captured_frames_a3.py`): 41 frames (1 snapshot + 40 updates), RAW WIRE
  TEXT, real Kraken checksums, validates 40/40 through the full path. Ground-truth from the 2026-07-19
  Sprint-2 capture. Replayable with NO socket.
- The full path (parse→WireDecimal→book update→CRC32→MarketState) is gated by checksum validation at
  :1938; A3 frames validate, so they reach MarketState — full path, not truncated.

---

## §0 RULES OF ENGAGEMENT
0.1 **No discretion.** Code wins: STOP and report.
0.2 **No src change.** The instrument (`89a2842`) and the loop are frozen. The harness drives them; it
    does not edit them. If a real measurement seems to need an src edit, STOP and report.
0.3 **THE STANDING ENTRY-POINT CHECK (D-r30):** the measurement MUST drive
    `get_live_market_data(enable_instrument=True)` — the production async generator — and STATE that
    entry point. A direct-construct harness (building PerFrameRecord and calling its methods) measures
    the instrument's arithmetic, not the loop; it is VOID. State the entry point explicitly.
0.4 **NO sleep on the measured path** (D-r30 / CLOSEOUT-3). No `time.sleep`, `asyncio.sleep`, or
    injected interval on the frame-processing path. The measured interval is real processing only.
    State that no sleep is on it. (`_test_per_frame_delay_seconds` MUST be 0/unset — confirm.)
0.5 Report every attempt.
0.6 AUTO MODE OFF — verify the bar. Measurement WO, but §0.2 forbids any src edit and auto mode is how
    a stray one slips in.
0.7 **BUILT-VS-OPERATED (D24).**

    | Thing | Status | Built & verified where |
    |---|---|---|
    | Per-frame instrument + `enable_instrument` flag | **OPERATED — FROZEN** | `89a2842`; observes the real loop (WO-039 bite proof) |
    | A3 fixture (wire-text, real checksums, validates 40/40) | **OPERATED** | Sprint-2 capture; confirmed WO-040-PREP |
    | Host-suspend detector | **OPERATED** | WO-023 §6 |
    | The real-frame measurement harness + the baseline number | **THIS WO IS THE BUILDER** | §2/§3 |

    Any OPERATED row not verified → STOP.

---

## §1 CONFIRM STATE
HEAD `89a2842`, `git diff -- src/` empty (paste), 237 both interpreters, CI green `30399653951`.
Confirm A3 loads and its 41 frames are present. Confirm `_test_per_frame_delay_seconds` default is 0
(no injected delay available on the measured path).

---

## §2 DRIVE A3 THROUGH THE REAL LOOP AND MEASURE (this WO builds the harness)

2.1 Build `tools/measure_real_loop_baseline.py` (writes `.artifacts/`, WO-032 boundary). It feeds A3's
    wire-text frames through `get_live_market_data(enable_instrument=True)` — the production async
    generator — replaying the snapshot then the 40 updates in order. The committed PerFrameRecord
    collects per-frame timing (frame-received → ready-to-yield) over the REAL parse+CRC32+book-update+
    MarketState work.
2.2 **Entry point stated (0.3):** the harness drives `get_live_market_data`, not a direct construct.
    State it. Confirm each frame reaches MarketState (validates) — a frame that fails checksum yields
    None and is NOT a per-frame processing sample; report how many of 41 produced a timing and confirm
    it matches the validating count (expected: all that should validate do).
2.3 **No sleep on the path (0.4):** state explicitly that the measured interval contains only real
    processing — no injected delay, `_test_per_frame_delay_seconds == 0`.
2.4 **Sample size honesty:** 41 frames is a SMALL sample for a distribution. Options to strengthen it,
    state which you used: replay the 41-frame sequence multiple times (N passes → 41·N samples, noting
    warm-cache effects), and/or report the distribution with explicit N and a caveat that 41 unique
    frames is the ground-truth ceiling without a new capture. Do NOT fabricate frames to pad N — real
    frames only. If the sample is too small for stable p99, SAY SO and report what the ground-truth
    permits rather than inflating confidence.

---

## §3 DECLARE THE BASELINE — SEVEN DIMENSIONS, HOST-SUSPEND GATED, PLAUSIBILITY-CHECKED

3.1 The measured per-frame processing distribution: median / p95 / p99 / max / N (real work, real
    checksums, real book updates). This is the reference.
3.2 **Seven scope dimensions (D35-4), declared WITH the number, inseparable:** HOST (machine/OS), LOAD,
    SOURCE ("A3 ground-truth wire-text replay, real Kraken checksums, 2026-07-19 capture, no socket, no
    injected pacing"), DURATION/N (frames·passes), RESOLUTION (timer granularity), INSTRUMENT
    (PerFrameRecord @ `89a2842`), INTERPRETER (3.14 canonical — state whether 3.11 differs materially).
3.3 **Host-suspend gate (D24):** the detector runs for the measurement window; any wall-vs-monotonic
    divergence beyond the drift bound VOIDs the baseline (re-measure on a quiet host). State the
    detector result as the number's validity gate — zero suspend events, or VOID + re-measure.
3.4 **Plausibility check (CLOSEOUT-3):** is the number physically reasonable for parse + CRC32 over a
    full-depth L2 ladder + book update + MarketState construction? State the expected order of
    magnitude and confirm the measurement sits in it. If implausibly SMALL (e.g. sub-microsecond →
    the CRC32/parse isn't actually running), or implausibly large, STOP and investigate — a real
    measurement must be plausible for the work described. (WO-039's raw_frames gave 0.078ms median for
    4 frames; A3's fuller book depth may differ — state whether the A3 number is consistent with real
    CRC32 over the actual ladder depth.)
3.5 **Reference USE stated:** what a corpus-time check flags against this number, e.g. "per-frame real
    processing cost exceeds <p99> for N consecutive frames." A number nothing is checked against is not
    a reference. The check must use the REAL p99, and account for the small-N caveat (a tighter margin
    if N is small and the tail is uncertain).
3.6 Declare in `evidence/WO-038/baseline.json` (or `evidence/WO-040/baseline.json`, state which),
    superseding the withdrawn CLOSEOUT-2 numbers. Preserve the correction chain
    (15.5ms fixture-pacing → 0.542ms simulated → THIS real number), annotate-not-rewrite — the chain is
    the evidence the reference was hunted to ground.

---

## §4 SCOPE FENCE
- Produces the baseline ONLY. No src change (instrument frozen). No live socket (A3 is on-disk).
- No corpus capture (final WO). No pass-two touch. No new reason code.
- Does NOT pad the sample with fabricated frames — real ground-truth frames only.

## §5 ACCEPTANCE
- Harness drives `get_live_market_data(enable_instrument=True)` — entry point stated; A3 frames reach
  MarketState; timing count matches validating count; NO sleep on the path (`_test..._delay == 0`)
- Baseline distribution declared (median/p95/p99/max/N) with all seven dimensions + host-suspend result
- Plausibility check stated and passed (or STOP); small-N honesty stated
- Reference USE stated against the real p99
- baseline.json declares the real number; correction chain preserved (fixture-pacing → simulated → real)
- `git diff -- src/` EMPTY vs `89a2842` (paste); five src sha256 identical
  (`kraken_v2_book.py` `2e0f8a13…`, `factory.py` `103a8ba7…`, `registry.py` `5bf833c7…`,
  `live_capture.py` `dab18f67…`, `decision.py` `3d153a11…`, `risk/engine.py` `bd0747f…`)
- 237 both interpreters (+ any harness test — state arithmetic); lint 6/6 · contract 6/6 · ruff clean ·
  annotation 0 · preflight pass
- `wo029_reverify_partition.py` PASS 31/31
- Commit, push, local == remote, CI GREEN both legs (REAL run number, on the commit with the evidence)

## §6 REPORT — `WO-040-REPORT.md`
The entry point stated; frames-reaching-MarketState count; no-sleep confirmation; the baseline
distribution with N and the small-N caveat; all seven dimensions; the host-suspend gate result; the
plausibility check with expected-vs-measured order of magnitude; the reference USE; the baseline.json
declaration with the preserved correction chain; the empty src diff + five sha256; every attempt; any
STOP; the CI run (real).

**THEN STOP.** With a REAL capture-loop baseline in hand, the queue is: corpus preconditions
(host-suspend verification, socket grant, checksum + gap-ledger integrity — per-item, red lines live
here) → 24h corpus.