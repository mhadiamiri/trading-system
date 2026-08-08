"""WO-054 §2.5/§3.4 BITE PROOF — trade-merge no-fabrication, and the regime summary.

    python tools/wo054_trade_merge_bite_proof.py

FIXTURES ONLY. No socket opens in this WO under any circumstance; every input below is synthetic.

TWO MUTATIONS, EACH FAILING A DIFFERENT MODULE:

  MUTATION FABRICATE (§2.5) — during an outage, report `count: 0` and carry the last seen price
      into `last_price`, i.e. exactly the corpus that says "no trades occurred" when it means "the
      trade channel dropped". The misattribution bite must FAIL. The DUAL — a healthy channel
      reporting real numbers — must still PASS, because a merger that nulled everything would fail
      the bite too and a proof checking only "something failed" could not tell the two apart.

  MUTATION HARDCODE (§3.4) — return a fixed regime summary regardless of input. The quiet-vs-
      volatile discrimination must FAIL while the trade-channel tests are untouched, proving the
      summary is actually reading the prices rather than being decorated with plausible numbers.

ARTIFACT 5 demonstrates the ECONOMIC OBJECT directly (§0.9): the two states are printed side by
side so the difference between "a claim of zero" and "the absence of a claim" is visible without
reading a test name.

§0.10 — the discrimination sets hold only single-purpose tests; exclusions recorded below.

Writes to .artifacts/ (WO-032 §4.1).
"""

import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADE = os.path.join(REPO, "src", "trading", "data", "trade_channel.py")
REGIME = os.path.join(REPO, "src", "trading", "data", "regime.py")
TESTS = "tests/test_trade_channel.py tests/test_regime.py"
ARTIFACT_DIR = os.path.join(REPO, ".artifacts", "wo054_trade_merge_bite_proof")

# ── MUTATION FABRICATE: an outage reports zeros and a carried price ───────────────────────────
FABRICATE_ANCHOR = [
    '                "observable": False,',
    '                "count": None,',
    '                "volume": None,',
    '                "last_price": None,',
]
FABRICATE_MUTANT = [
    '                "observable": False,',
    '                "count": 0,                      # MUTATED: claims nothing traded',
    '                "volume": "0",                   # MUTATED',
    '                "last_price": (str(self._running_last_price)',
    '                               if self._running_last_price is not None else None),',
]

# ── MUTATION HARDCODE: the regime summary stops reading the prices ────────────────────────────
HARDCODE_ANCHOR = [
    "        moves.sort()",
    '        horizons[f"{horizon}m"] = _horizon_block(moves)',
]
HARDCODE_MUTANT = [
    "        moves.sort()",
    "        from decimal import Decimal as _D   # MUTATED: fixed summary, input ignored",
    '        horizons[f"{horizon}m"] = _horizon_block([_D("0.05")] * 20)',
]

# SINGLE-PURPOSE sets (§0.10).
FABRICATE_BITE = {"test_bite_an_outage_reports_nulls_not_zeros"}
FABRICATE_DUAL = {
    "test_dual_a_healthy_channel_reports_real_numbers",
    "test_counts_are_per_interval_deltas_not_running_totals",
    "test_an_interval_with_no_trades_reports_zero_and_a_null_last_price",
    "test_recovery_resumes_real_counting",
}
REGIME_BITE = {
    "test_bite_a_volatile_window_summarises_differently_from_a_quiet_one",
    "test_bite_the_cost_threshold_counts_discriminate",
}
REGIME_DUAL = {"test_dual_the_same_input_summarises_identically"}
# BROAD — excluded from the discrimination sets and reported for visibility (§0.10). These read
# several properties at once, so they fail under either mutation and attribute nothing.
BROAD = {
    "test_last_price_is_never_fabricated_for_a_tradeless_interval",
    "test_a_quiet_regime_classifies_as_quiet_and_a_volatile_one_does_not",
    "test_the_carried_price_survives_an_outage_with_its_age",
}


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _nl(t):
    return "\r\n" if "\r\n" in t else "\n"


def run_tests():
    p = subprocess.run(
        [sys.executable, "-m", "pytest", *TESTS.split(), "-p", "no:randomly", "-v",
         "--tb=line", "-q"],
        cwd=REPO, env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"),
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
    )
    return p.returncode, (p.stdout + p.stderr)


def digest(rc, out):
    failed_lines = [line for line in out.splitlines() if "FAILED" in line]
    failed = {f.split("::")[-1] for f in re.findall(r"(test_[\w\[\]\.\-]+)",
                                                    "\n".join(failed_lines))}
    passed = set(re.findall(r"(test_\w+)\s+PASSED", out))
    return {
        "returncode": rc,
        "summary": next((line.strip() for line in reversed(out.splitlines())
                         if re.search(r"\d+ (passed|failed)", line)), "(no summary)"),
        "fabricate_bite_failed": sorted(failed & FABRICATE_BITE),
        "fabricate_dual_failed": sorted(failed & FABRICATE_DUAL),
        "regime_bite_failed": sorted(failed & REGIME_BITE),
        "regime_dual_failed": sorted(failed & REGIME_DUAL),
        "fabricate_dual_passed": len(passed & FABRICATE_DUAL),
        "broad_failed": sorted(failed & BROAD),
    }


def block(title, d, expectation):
    lines = [f"-- {title} --"]
    for k, v in d.items():
        lines.append(f"  {k:<24} {v}")
    return lines + [f"  EXPECT: {expectation}", ""]


def _mutate(path, anchor_lines, mutant_lines):
    original = open(path, "rb").read()
    text = original.decode("utf-8")
    nl = _nl(text)
    anchor, mutant = nl.join(anchor_lines), nl.join(mutant_lines)
    assert text.count(anchor) == 1, (
        f"anchor in {os.path.basename(path)} is not unique (found {text.count(anchor)}) — "
        f"refusing to mutate blindly")
    open(path, "wb").write(text.replace(anchor, mutant, 1).encode("utf-8"))
    return original


def main():
    trade_before, regime_before = sha256(TRADE), sha256(REGIME)
    out = ["WO-054 §2.5/§3.4 BITE PROOF — TRADE-MERGE NO-FABRICATION, AND THE REGIME SUMMARY.",
           "FIXTURES ONLY — no socket opens in this WO. Four artifacts, sha256 exact-restore.",
           f"  trade_channel.py sha256 BEFORE : {trade_before}",
           f"  regime.py        sha256 BEFORE : {regime_before}", ""]

    d1 = digest(*run_tests())
    out += block("ARTIFACT 1 — PRISTINE", d1, "returncode 0; nothing failed")

    original = _mutate(TRADE, FABRICATE_ANCHOR, FABRICATE_MUTANT)
    try:
        out += ['  MUTATION FABRICATE: an outage reports count 0 and carries a last_price', ""]
        d2 = digest(*run_tests())
    finally:
        open(TRADE, "wb").write(original)
    out += block("ARTIFACT 2 — MUTATION FABRICATE (the misattributing corpus)", d2,
                 "the misattribution BITE fails; the DUAL still passes and the REGIME tests are "
                 "untouched")

    original = _mutate(REGIME, HARDCODE_ANCHOR, HARDCODE_MUTANT)
    try:
        out += ["  MUTATION HARDCODE: the regime summary ignores its input", ""]
        d3 = digest(*run_tests())
    finally:
        open(REGIME, "wb").write(original)
    out += block("ARTIFACT 3 — MUTATION HARDCODE (a summary that reads nothing)", d3,
                 "the REGIME bite fails; the trade-channel sets are untouched")

    d4 = digest(*run_tests())
    out += block("ARTIFACT 4 — RESTORED", d4, "returncode 0; nothing failed")

    trade_after, regime_after = sha256(TRADE), sha256(REGIME)
    exact = (trade_after == trade_before) and (regime_after == regime_before)
    out += ["-- sha256 EXACT-RESTORE --",
            f"  trade_channel.py AFTER : {trade_after}",
            f"  regime.py        AFTER : {regime_after}",
            f"  IDENTICAL              : {exact}", ""]

    demo = _direct_demonstration()
    out += ["-- ARTIFACT 5 — DIRECT DEMONSTRATION (§0.9: the record, not the test name) --"]
    out += [f"  {line}" for line in demo["lines"]]
    out += ["  EXPECT: an outage writes NULLS (no claim); a quiet interval writes 0 (a claim)", ""]

    fab_ok = bool(d2["fabricate_bite_failed"]) and not d2["fabricate_dual_failed"] \
        and not d2["regime_bite_failed"]
    reg_ok = bool(d3["regime_bite_failed"]) and not d3["regime_dual_failed"] \
        and not d3["fabricate_bite_failed"]
    out += [f"  FABRICATE discriminates (bite fails, dual holds {d2['fabricate_dual_passed']}/"
            f"{len(FABRICATE_DUAL)}, regime untouched) : {fab_ok}",
            f"  HARDCODE  discriminates (regime bite fails, trade sets untouched)          : "
            f"{reg_ok}",
            f"  DIRECT demonstration distinguishes null from zero                          : "
            f"{demo['ok']}",
            "",
            "  §0.4 THE DUAL IS LOCAL AND DIRECT: `fabricate_dual_failed` is tracked in EVERY",
            "  artifact and is empty in all four. A merger that nulled everything would fail the",
            "  bite too — the dual is what distinguishes 'refuses to claim' from 'claims nothing'.",
            "",
            "  §0.10 BROAD TESTS EXCLUDED from the discrimination sets and reported separately:",
            "  they assert several properties at once and attribute nothing.",
            ""]

    ok = (d1["returncode"] == 0 and not d1["fabricate_bite_failed"] and not d1["regime_bite_failed"]
          and d2["returncode"] != 0 and fab_ok
          and d3["returncode"] != 0 and reg_ok
          and d4["returncode"] == 0 and not d4["fabricate_bite_failed"]
          and demo["ok"] and exact)
    out += [f"VERDICT: {'PASS' if ok else 'FAIL'}"]

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    body = "\n".join(out) + "\n"
    run_path = os.path.join(ARTIFACT_DIR,
                            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".txt")
    for p in (run_path, os.path.join(ARTIFACT_DIR, "latest.txt")):
        open(p, "w", encoding="utf-8").write(body)
    print(body, end="")
    print(f"\n[WO-032 §4.1] written to {os.path.relpath(run_path, REPO)} (git-ignored)")
    assert exact, "SRC NOT RESTORED — aborting"
    return 0 if ok else 1


def _direct_demonstration():
    """Print the two records side by side on the RESTORED tree. Fixtures only."""
    sys.path.insert(0, os.path.join(REPO, "src"))
    from trading.data.trade_channel import TradeMerger, parse_trade_message

    t1, t2, t3 = ("2026-08-05T22:00:01+00:00", "2026-08-05T22:00:02+00:00",
                  "2026-08-05T22:00:03+00:00")
    msg = {"channel": "trade", "type": "update", "data": [
        {"symbol": "BTC/USD", "side": "buy", "qty": "0.02", "price": "64000.0",
         "ord_type": "market", "trade_id": 1, "timestamp": t1}]}

    quiet = TradeMerger()
    quiet.observe(parse_trade_message(msg)[0])
    quiet.snapshot_for_frame(t1)
    quiet_rec = quiet.snapshot_for_frame(t2)          # listening, nothing traded

    down = TradeMerger()
    down.observe(parse_trade_message(msg)[0])
    down.snapshot_for_frame(t1)
    down.mark_unobservable("TRADE_CHANNEL_DROPPED", t2, detail="venue dropped the trade channel")
    down_rec = down.snapshot_for_frame(t3)            # channel down

    lines = [
        "LISTENING, NOTHING TRADED  ->  " + _fmt(quiet_rec),
        "CHANNEL DOWN, CANNOT SEE   ->  " + _fmt(down_rec),
        f"outage ledger              ->  {down.ledger()}",
        "",
        "  count 0    = a CLAIM: we were listening and nothing traded",
        "  count null = the ABSENCE of a claim: we could not see",
    ]
    ok = (quiet_rec["count"] == 0 and quiet_rec["last_price"] is None
          and down_rec["count"] is None and down_rec["last_price"] is None
          and len(down.ledger()) == 1)
    return {"lines": lines, "ok": ok}


def _fmt(rec):
    return (f"observable={str(rec['observable']):<5} count={str(rec['count']):<5} "
            f"volume={str(rec['volume']):<5} last_price={str(rec['last_price']):<9} "
            f"running={rec['running_last_price']} (age {rec['running_last_price_age_ms']}ms)")


if __name__ == "__main__":
    raise SystemExit(main())
