# A bite proof asserts the ECONOMIC EFFECT, not the EVENT RECORD

**Date:** 2026-08-07
**WO:** WO-050 §5.1
**Ruling:** D49
**Status:** RATIFIED

## The doctrine

> In an economic path the observable effect is the **ledger consequence** — the trade, the cost, the
> position change — never the log line or the event object announcing it.
>
> **A log line is a claim; the ledger is the effect.**

## What produced it

WO-048's segmented backtest runner force-flattened every segment boundary like this:

```python
position = dataclasses.replace(position, current_quantity=Decimal("0"))
```

It zeroed a variable. It executed no trade. The U2 ruling — force-flat at every boundary — was
**labelled but never economically executed**, so the reported P&L omitted the cost and proceeds of
closing all 21 segments of a 3.5-million-trade run.

The §6.1 bite proof did not catch it. It asserted:

```python
flats = [e for e in result["boundary_events"] if e["event"] == "SEGMENT_CLOSE_FORCE_FLAT"]
assert flats
assert "DECLARED COST" in flats[0]["detail"]
assert Decimal(flats[0]["quantity_flattened"]) != 0
```

Every one of those passes with no trade in existence. The proof checked that the runner *said* it
flattened, in the right words, with the right quantity. It never checked that anything happened.

## Why the existing rule was not enough

D-r16 already ruled that proofs must terminate in **observable effects**. This proof was written
*after* that rule and still checked a label — because **an event record is technically observable**.
It is a real object, in a real output, with real fields, and it can be asserted on with a straight
face. The rule was satisfied to the letter and defeated in substance.

The gap is that "observable" does not distinguish between *the system doing a thing* and *the system
reporting that it did a thing*. In an economic path those come apart precisely when it matters most,
because the reporting is the easy half to get right.

## What the rule now requires

For any path with economic consequence, the assertion must land on one of:

- **the trade** — a fill exists, with a side, a size, and a price;
- **the cost** — it is non-zero, and attributed to the right channel;
- **the position** — it moved to the value claimed.

An assertion on an event, a log line, a decision enum, a reason code, or a boolean flag is **not
sufficient on its own**. It may accompany the economic assertion — naming the cause is useful — but
it can never substitute for it.

## The test that would have caught it

```python
assert seg["boundary_closes"] == 1                 # a real closing trade exists
assert Decimal(ev["close_cost"]) > 0               # it cost money
assert Decimal(seg["final_quantity"]) == 0         # the position actually moved to zero
assert Decimal(seg["unrealised_pnl_at_close"]) == 0  # and nothing is left marked to market
```

Note the last line especially: **unrealised P&L at segment end is an independent check on R1**. It
is computed from the position, not from the flatten event, so a close that did not execute shows up
as a non-zero residual no matter what the event record says. Two mechanisms, one derived from the
other's absence — which is what makes it hard to fool by accident.

## Scope

This does not weaken event records. They remain the right thing to assert for **governance**
properties — a reason code being declared, a refusal naming what it refused, a termination stating
its cause. The rule is specifically about paths where money moves: there, the ledger is the effect,
and the announcement is only ever a claim about it.
