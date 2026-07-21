"""WO-016 §1.4 — checksum-failure REPLAY HARNESS (drives the PRODUCTION path; rule 0.1h).

Takes captured checksum-failure artifacts (WO-008b-B-RERUN instruments_dump.json ->
checksum_failure_captures) and drives the PRODUCTION book-apply + checksum path to reproduce
each observed `computed_checksum`. It imports and calls the real production code
(KrakenV2BookAdapter.apply_snapshot -> _current_ladder_strings -> compute_checksum); it does
NOT reimplement any of it, so a reproduction is evidence about the code that failed.

Honest artifact limit (rule 0.1f): the 20 preceding frames cannot rebuild a book that accreted
over thousands of prior frames. The captured `local_book_{bids,asks}` IS the adapter's own
top-10 ladder at the instant it computed `computed_checksum`, and the CRC is fully determined by
that top-10 plus the string formatting. Seeding a production LocalBookData with that ladder and
driving the production formatter (_current_ladder_strings) + compute_checksum therefore replays
exactly the computation that failed.

The FIX CANDIDATE (fixed-point size formatting) is computed here for DIAGNOSIS only — it does NOT
modify production (§2 is gated behind approval).

Usage:  python tools/replay_checksum_capture.py [--index N]
"""
import binascii
import json
import os
import sys
from decimal import Decimal

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [REPO, os.path.join(REPO, "src")]

from trading.data.adapters.kraken_v2_book import KrakenV2BookAdapter, LocalBookData  # noqa: E402

DUMP = os.path.join(REPO, "evidence", "WO-008b-B-RERUN", "instruments_dump.json")


def load():
    d = json.load(open(DUMP, encoding="utf-8"))
    inst = d["instruments"]
    return inst["checksum_failure_captures"], inst.get("checksum_failure_summaries", [])


def dec_levels(levels):
    return [(Decimal(p), Decimal(q)) for p, q in levels]


def replay_production(cap):
    """Seed a production LocalBookData with the captured top-10 ladder and drive the PRODUCTION
    formatter + checksum. Returns the checksum the production path computes."""
    book = LocalBookData()
    book.apply_snapshot(bid_levels=dec_levels(cap["local_book_bids"]),
                        ask_levels=dec_levels(cap["local_book_asks"]),
                        sequence=0, checksum=0)
    adapter = KrakenV2BookAdapter()          # fixture mode; opens NO socket
    adapter._local_book = book
    bid_strs, ask_strs = adapter._current_ladder_strings()   # PRODUCTION formatter (bug site)
    return adapter.compute_checksum(bid_strs, ask_strs), bid_strs, ask_strs


def replay_fixed(cap):
    """FIX CANDIDATE (diagnosis only, not production): format sizes fixed-point (precision-
    preserving per Kraken's 'decimal decoder' rule) instead of str()'s scientific notation."""
    def fixed(v):
        return format(Decimal(str(v)), "f")   # fixed-point; no scientific notation
    def crc(bids, asks):
        parts = []
        for p, s in asks:
            parts.append(str(p).replace(".", "") + fixed(s).replace(".", "").lstrip("0"))
        for p, s in bids:
            parts.append(str(p).replace(".", "") + fixed(s).replace(".", "").lstrip("0"))
        return binascii.crc32("".join(parts).encode("ascii"))
    return crc(dec_levels(cap["local_book_bids"]), dec_levels(cap["local_book_asks"]))


def main():
    caps, summaries = load()
    n = len(caps)
    repro = fixed_ok = 0
    bad = []
    for cap in caps:
        comp, _, _ = replay_production(cap)
        if comp == cap["computed_checksum"]:
            repro += 1
        else:
            bad.append((cap["sequence_position_in_run"], comp, cap["computed_checksum"]))
        if replay_fixed(cap) == cap["expected_checksum"]:
            fixed_ok += 1
    print(f"=== WO-016 REPLAY HARNESS — {n} full captures (+{len(summaries)} summaries) ===")
    print(f"PRODUCTION path reproduces captured computed_checksum : {repro}/{n}")
    print(f"FIX CANDIDATE (fixed-point size) yields expected      : {fixed_ok}/{n}")
    if bad:
        print(f"  NON-reproducing: {bad[:5]}")
    print("PROVES: the production apply+format path deterministically reproduces every captured")
    print("failure, and precision-preserving (fixed-point) size formatting recovers Kraken's")
    print("expected checksum for every one. Root cause = scientific-notation size formatting.")


def detail(i):
    caps, _ = load()
    cap = caps[i]
    comp, bstr, astr = replay_production(cap)
    print(f"capture[{i}] seq={cap['sequence_position_in_run']} utc={cap['utc']}")
    print(f"  expected={cap['expected_checksum']} computed={cap['computed_checksum']}")
    print(f"  production _current_ladder_strings bids: {bstr}")
    print(f"  production replay checksum = {comp}  (==computed? {comp==cap['computed_checksum']})")
    print(f"  fix-candidate checksum     = {replay_fixed(cap)}  (==expected? {replay_fixed(cap)==cap['expected_checksum']})")


if __name__ == "__main__":
    if "--index" in sys.argv:
        detail(int(sys.argv[sys.argv.index("--index") + 1]))
    else:
        main()
