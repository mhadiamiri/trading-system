"""WO-057 §4 — THE COMMITTED CORPUS SCANNER. Abort condition 2's detector.

    python tools/corpus_fabrication_scan.py [corpus_path]

THE CONDITION
-------------
    "any frame is written with `observable: true` and a FABRICATED `last_price`"

A fabricated `last_price` is the D48 substitution moved to CAPTURE time, where it is harder to
catch than at read time because the reader has no way to tell an invented price from an observed
one. This scanner is the thing that can tell.

WHY THIS EXISTS AND WHY IT IS COMMITTED
---------------------------------------
WO-055 found this condition had NO detector, and — worse — that the obvious way to check it
returned a FALSE GREEN. Scanning `corpus_20260805` for "frames with `observable: true` and an
unbacked `last_price`" yields **zero**, because that corpus is book-only: no frame has an
`observable` field or a `last_price` at all. The zero would have been reported as
"§3.5 PASS — no fabricated prices".

That is the ratified specimen, live:

    AN EMPTY RESULT FROM A QUERY THAT CANNOT FAIL IS NOT EVIDENCE.

It is committed rather than a throwaway script because a scanner whose code is not in the tree
certifies nothing (the D51 standing rule that retired `a025db1e…`).

THE THREE OUTCOMES — AND THE FIRST TWO ARE NEVER CONFLATED (§4.2)
------------------------------------------------------------------
    (a) NOT_APPLICABLE  the corpus carries no `trades` sub-object, so the question CANNOT BE ASKED.
                        This is NOT "zero fabricated prices". Refusing to say "clean" here is the
                        entire point of this tool.
    (b) CLEAN           the fields exist, frames were examined, and zero violations were found.
    (c) VIOLATIONS      n frames named, with their identities.

Every report states the number of frames EXAMINED and the number EXAMINABLE. A scanner that says
"0 violations" without saying "of N examinable frames" is indistinguishable from one that examined
nothing — which is exactly the failure being closed.

WHAT COUNTS AS FABRICATED
-------------------------
Per `evidence/WO-054/trade_merge_schema.md`, on a frame with `observable: true`:

    count == 0  =>  last_price MUST be null.   A price on a zero-trade interval is not backed by
                    any observed trade in that interval; it can only have been invented or carried
                    in from elsewhere. `running_last_price` is the separately-named field that
                    legitimately carries forward, and it is NOT examined here.
    count >= 1  =>  last_price MUST be non-null. A traded interval with no price is a different
                    defect — reported as MISSING rather than fabricated, so the two never merge.

Writes to .artifacts/ (WO-032 §4.1).
"""

import json
import sys
from pathlib import Path

DEFAULT_CORPUS = Path("captures/corpus_24h/corpus_20260805")

NOT_APPLICABLE = "NOT_APPLICABLE"
CLEAN = "CLEAN"
VIOLATIONS = "VIOLATIONS"


def _iter_frames(root: Path):
    """Yield (path, line_number, frame) for every JSONL frame under `root`. Read-only."""
    import gzip

    for path in sorted(root.rglob("*.jsonl")) + sorted(root.rglob("*.jsonl.gz")):
        opener = gzip.open if path.suffix == ".gz" else open
        try:
            with opener(path, "rt", encoding="utf-8") as handle:
                for lineno, line in enumerate(handle, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield path, lineno, json.loads(line)
                    except json.JSONDecodeError:
                        continue          # a torn trailing line is not data; never guessed at
        except OSError:
            continue


def scan(root: Path) -> dict:
    """Scan a corpus. Returns the three-outcome report."""
    total = 0
    examinable = 0
    examined = 0
    violations = []
    missing = []

    for path, lineno, frame in _iter_frames(root):
        total += 1
        trades = frame.get("trades")
        # NOT EXAMINABLE: no trades sub-object, or the frame makes no claim about visibility.
        if not isinstance(trades, dict) or "observable" not in trades:
            continue
        examinable += 1
        if trades.get("observable") is not True:
            # `observable: false` is the ABSENCE of a claim. There is nothing to fabricate and
            # nothing to check — the condition is scoped to observable frames by its own wording.
            continue
        examined += 1

        count = trades.get("count")
        last_price = trades.get("last_price")
        ident = {"file": str(path.name), "line": lineno,
                 "timestamp": frame.get("timestamp"), "count": count, "last_price": last_price}

        if count == 0 and last_price is not None:
            violations.append(ident)          # THE FABRICATION
        elif isinstance(count, int) and count >= 1 and last_price is None:
            missing.append(ident)             # a different defect; never merged with the above

    if examinable == 0:
        outcome = NOT_APPLICABLE
        detail = (
            f"{total} frames read, NONE examinable: no frame carries a `trades.observable` field, "
            f"so the question cannot be asked of this corpus. THIS IS NOT 'zero fabricated "
            f"prices' — reporting it as clean would be the WO-055 false green."
        )
    elif violations:
        outcome = VIOLATIONS
        detail = (f"{len(violations)} frame(s) with observable:true, count:0 and a non-null "
                  f"last_price — a price not backed by any observed trade in its interval")
    else:
        outcome = CLEAN
        detail = (f"{examined} observable frame(s) examined of {examinable} examinable; "
                  f"zero fabricated prices")

    return {
        "corpus": root.as_posix(),
        "outcome": outcome,
        "frames_total": total,
        "frames_examinable": examinable,
        "frames_examined": examined,
        "violations": violations,
        "missing_price_on_traded_interval": missing,
        "detail": detail,
        "falsifier": (
            "A CLEAN verdict would be falsified by any observable frame with count == 0 and a "
            "non-null last_price. A NOT_APPLICABLE verdict would be falsified by the presence of "
            "any frame carrying `trades.observable`. Note the two are NOT interchangeable: "
            "NOT_APPLICABLE means the query could not speak, CLEAN means it spoke and found "
            "nothing."
        ),
    }


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CORPUS
    if not root.is_dir():
        print(f"FAIL: not a directory: {root}")
        return 2

    report = scan(root)
    print(f"corpus            : {report['corpus']}")
    print(f"frames total      : {report['frames_total']}")
    print(f"frames EXAMINABLE : {report['frames_examinable']}")
    print(f"frames EXAMINED   : {report['frames_examined']}")
    print(f"violations        : {len(report['violations'])}")
    print(f"missing price     : {len(report['missing_price_on_traded_interval'])}")
    for v in report["violations"][:20]:
        print(f"    FABRICATED  {v['file']}:{v['line']}  ts={v['timestamp']}  "
              f"count={v['count']}  last_price={v['last_price']}")
    print()
    print(f"OUTCOME: {report['outcome']}")
    print(f"  {report['detail']}")

    out = Path(".artifacts/WO-057")
    out.mkdir(parents=True, exist_ok=True)
    (out / "fabrication_scan.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n[WO-032 §4.1] written to {out / 'fabrication_scan.json'} (git-ignored)")

    # Exit codes are distinct so a caller can tell the three outcomes apart WITHOUT parsing text.
    #   0 = CLEAN   1 = VIOLATIONS   3 = NOT_APPLICABLE
    # NOT_APPLICABLE is deliberately NOT 0: a validation run that treated it as success would be
    # committing the WO-055 false green in a shell script instead of a report.
    return {CLEAN: 0, VIOLATIONS: 1, NOT_APPLICABLE: 3}[report["outcome"]]


if __name__ == "__main__":
    raise SystemExit(main())
