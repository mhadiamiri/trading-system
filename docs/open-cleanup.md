# Open Cleanup Items

Tracked, deliberately **not** actioned. Each is here because churning it now would cost
more than it saves, or because it touches a signature and rule 0.1a says stop and ask.

---

## Vestigial `sequence` parameters on `LocalBookData`

**Raised**: WO-008b-A1 (2026-07-19) · **Tracked by**: WO-008b-A1b · **Owner**: unassigned

`LocalBookData.apply_snapshot()` and `apply_incremental_update()` still take a `sequence:
int` parameter and store `self.last_sequence`. Every caller now passes `sequence=0`.

```
src/trading/data/adapters/kraken_v2_book.py
  :148  def apply_snapshot(self, bid_levels, ask_levels, sequence: int, checksum: int)
  :172  def apply_incremental_update(self, bid_levels, ask_levels, sequence: int, checksum: int)
  :98   last_sequence: int = 0
```

**Why it is vestigial.** The Kraken v2 public book channel transmits no sequence number
(amended FR-018a(a)). `QuoteUpdate` no longer carries the field, and the sequence-gap
branch is gone from `_process_quote_update`. These parameters are now pure internal
bookkeeping that nothing reads for a decision.

**Why it was NOT removed in WO-008b-A1.** Removing them changes two public method
signatures, which rule 0.1a makes a STOP-and-ask event. It is cosmetic, carries no
correctness risk while callers pass a constant, and bundling a signature change into a
work order already touching the checksum path, the parse path and 13 test sites would have
made the diff harder to review for no benefit.

**One thing to check when it is done.** `LocalBookData.state` still branches on
`last_sequence`:

```
:108  elif self.last_sequence == 0:
```

That is used to distinguish an uninitialised book from a synchronised one. Removing
`last_sequence` needs a replacement signal — most naturally "has the book any levels" or
an explicit state flag. **Do not delete the field without replacing that check**, or the
book-state machine loses its notion of "not yet initialised."

**Suggested scope**: a small standalone work order, or a rider on whichever work order next
has legitimate reason to touch `LocalBookData`.
