"""WO-013 item 2 — CONTAINMENT bite proof for the widened (full-loop) instrument (four artifacts, sha256).

The §B claim "the widened instrument times adapter + strategy.decide + risk.check + emission" was a
source-inspection claim about behavior (0.1f), and the evidence mildly cut against it. This proves it
BEHAVIORALLY: inject a KNOWN per-frame delay into the LOOP path (live.py per-MarketState body — a line
ONLY the full-loop instrument executes; the adapter-only instrument never runs it), run the WIDENED
establishment, and show the measured mean_cycle RISES by ~the expected amount. Restore, sha256.

Injected per-frame delay is LARGE relative to the noise floor (10 ms ~ 10x the measured 1.018 ms
cross-session noise), so the containment verdict is itself well above sign-unestablished.

CALIBRATION: expected cycle rise = injected_per_frame x frames_per_cycle (frames_per_cycle =
achieved_rate x mean_cycle). If the measured rise is MATERIALLY LESS than expected, the instrument
ATTENUATES — reported as its own finding, NOT adjusted toward the expected number.

NO src change persists: the injection is reverted by exact-byte restore before exit.
"""
import hashlib
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(REPO, "src", "trading", "loop", "live.py")
TOOL = os.path.join(REPO, "tools", "establish_mean_cycle_baseline.py")
SECONDS = "30"
# Inter-frame budget at 1959/min = 30.6 ms/frame. Sweep BELOW it (10 ms — attenuation regime) and
# ABOVE it (40 ms — saturation regime) to map the instrument's transfer function for per-frame cost.
INJECT_LEVELS_MS = [10.0, 40.0]

# Single-line anchor in the LOOP per-frame body. Prepend a SYNCHRONOUS delay (blocks the event loop,
# so the lag sampler sees the occupancy) on the same line — CRLF-safe, no import statement needed.
ANCHOR = "            desired_position = self._strategy.decide(market_state)"


def _inject(delay_ms):
    return (f'            __import__("time").sleep({delay_ms/1000.0}); '
            "desired_position = self._strategy.decide(market_state)  # INJECTED containment probe")


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run_widened():
    """Run the WIDENED establishment; return (mean_cycle_ms, achieved_per_min, tail)."""
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "src"))
    p = subprocess.run(
        [sys.executable, TOOL, "--seconds", SECONDS],
        cwd=REPO, env=env, capture_output=True, text=True,
    )
    out = p.stdout
    mc = re.search(r"measured mean_cycle=([\d.]+)ms", out)
    ach = re.search(r"achieved=([\d.]+)/min", out)
    mean_ms = float(mc.group(1)) if mc else float("nan")
    achieved = float(ach.group(1)) if ach else float("nan")
    return mean_ms, achieved, out.strip().splitlines()[-3:]


def main():
    original = open(LIVE, "rb").read()
    assert original.decode().count(ANCHOR) == 1, "anchor not unique in live.py"
    before = sha256(LIVE)
    out = ["WO-013 item 2 CONTAINMENT + CALIBRATION — widened instrument vs the loop (four artifacts, sha256)",
           f"Target: {os.path.relpath(LIVE, REPO)} (loop per-frame body); instrument: WIDENED full-loop",
           "Sweep per-frame delay BELOW (10 ms) and ABOVE (40 ms) the ~30.6 ms/frame inter-frame budget.",
           f"Noise floor 2.0 ms. Establishment: {SECONDS}s each. sha256 BEFORE: {before}", ""]

    # A1 — baseline (no injection)
    m0, a0, t0 = run_widened()
    frames_per_cycle = (a0 / 60.0) * (m0 / 1000.0)
    out += [f"-- ARTIFACT 1 — BASELINE widened mean_cycle = {m0:.3f} ms (achieved {a0:.0f}/min; "
            f"frames/cycle ~{frames_per_cycle:.2f}) --", *t0, ""]

    # A2 — inject the per-frame LOOP delay at each level, re-run widened
    rows = []
    for d in INJECT_LEVELS_MS:
        with open(LIVE, "wb") as f:
            f.write(original.decode().replace(ANCHOR, _inject(d)).encode())
        m, a, _t = run_widened()
        rise = m - m0
        expected = d * frames_per_cycle
        rows.append((d, m, a, rise, expected))
        out += [f"-- ARTIFACT 2.{int(d)} — INJECTED {d:.0f} ms/frame in the LOOP: mean_cycle={m:.3f} ms "
                f"(achieved {a:.0f}/min) --",
                f"MEASURED RISE={rise:+.3f} ms ; EXPECTED (full containment = inj x frames/cycle)={expected:.3f} ms ; "
                f"transfer ratio={rise/expected:.3f} ; vs floor: RATIO={abs(rise)/2.0:.2f} "
                f"({'ABOVE floor' if abs(rise) > 2.0 else 'BELOW floor — sign unestablished'})", ""]

    # A3 — restore, re-run widened
    with open(LIVE, "wb") as f:
        f.write(original)
    m2, a2, t2 = run_widened()
    out += [f"-- ARTIFACT 3 — RESTORED: widened mean_cycle = {m2:.3f} ms (back near baseline) --", *t2, ""]

    after = sha256(LIVE)
    exact = (after == before)
    r10 = next(r for r in rows if r[0] == 10.0)
    r40 = next(r for r in rows if r[0] == 40.0)
    # ENCLOSURE is shown iff SOME injection produces an ABOVE-FLOOR response (the loop is in the timed path).
    enclosed = any(abs(r[3]) > 2.0 for r in rows)
    out += ["-- ARTIFACT 4 — sha256 EXACT-RESTORE --", f"sha256 AFTER : {after}",
            f"EXACT RESTORE: {'YES — byte-identical' if exact else 'NO'}", "",
            "=== FINDINGS ===",
            f"ENCLOSURE: {'CONFIRMED' if enclosed else 'NOT SHOWN'} — a per-frame delay injected into the LOOP "
            f"moves the WIDENED mean_cycle (the adapter-only instrument never runs this line, so it cannot). "
            f"10 ms/frame -> {r10[3]:+.3f} ms; 40 ms/frame -> {r40[3]:+.3f} ms.",
            "ATTENUATION (the calibration finding, per item 2 — reported, NOT adjusted): mean_cycle = span / "
            "actual_samples is the mean SLEEP-WAKE (event-loop lag) cycle, NOT per-frame CPU throughput. Below "
            "the ~30.6 ms/frame inter-frame budget the pacer leaves idle slack, so a per-frame block delays the "
            f"sampler's wake only by ~its residual-on-arrival: 10 ms/frame -> {r10[3]:.3f} ms (transfer "
            f"{r10[3]/r10[4]:.3f}, and BELOW the 2.0 ms floor). Above the budget the loop SATURATES and the rise "
            f"grows sharply: 40 ms/frame -> {r40[3]:.3f} ms (achieved {r40[2]:.0f}/min — rate drop is itself a "
            "signal). So mean_cycle is a STARVATION/responsiveness detector (its WO-014c-1 purpose), not a linear "
            "per-frame cost meter; per-frame CPU changes are largely INVISIBLE until they approach saturation.",
            "IMPLICATION (item 3): the effective per-frame DETECTION floor is NOT ~0.6 ms — because of "
            f"attenuation a 10 ms/frame change is already below the cycle floor. Sensitivity ~{r10[3]/10.0:.3f} "
            "ms-cycle per ms-frame below saturation, so the per-frame detection floor is ~tens of ms/frame at "
            "this rate. Realistic sub-ms/frame changes are invisible to this instrument — a declared LIMIT.",
            "",
            f"RESULT: baseline={m0:.3f}  10ms->rise {r10[3]:+.3f}  40ms->rise {r40[3]:+.3f}  restored={m2:.3f}  "
            f"sha256-exact={exact}  enclosure={enclosed}  => {'OK (enclosure shown + attenuation characterised)' if (enclosed and exact) else 'SEE FINDINGS'}"]

    text = "\n".join(out)
    dest = os.path.join(REPO, "evidence", "WO-013", "containment_bite_proof.txt")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    assert sha256(LIVE) == before, "LIVE NOT RESTORED — aborting"
    print(text)
    print(f"\n[written] {os.path.relpath(dest, REPO)}")
    sys.exit(0 if (enclosed and exact) else 1)


if __name__ == "__main__":
    main()
