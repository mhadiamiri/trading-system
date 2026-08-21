# ESCALATION TO THE LEAD — the §4.5 certification verdict and what should follow it

**Status: ESCALATION. Nothing has been acted on.** D56 ruled that a negative certification reverts
the execution venue to dYdX. WO-066 §4.5 returned a negative. **The reversion has not been
started, and no venue work has been done since**, because what the verdict actually falsifies is
narrower than what D56's trigger reads on, and the difference is a venue decision that is not
ours to make.

**The question for the lead:** does D56's reversion fire on this verdict as written, or does the
verdict get re-asked on a fresh window with the three named defects repaired first?

---

## 1. WHAT WAS ACTUALLY MEASURED — the verdict is sound and is not being softened

§4.5 answered **NO**: the four mitigations as built do not produce a feed we would certify. That
answer stands, it was reached honestly, and the report did not strain against it. The dominant
mitigation deletes data in a market-correlated way — `refused_cross_venue_band` was **2,723 of
2,740 refusals, 99.4%** — and it truncated six consecutive hours at a fitted ceiling. By the
operator's own standard that is worse than no guard.

**None of what follows disputes the NO.** It disputes what the NO is a verdict *about*.

---

## 2. THE FAILURE IS IN THE MITIGATION DESIGN, NOT THE VENUE

This is the load-bearing distinction and it is why this is an escalation rather than a reversion.

D56 made Hyperliquid the execution venue **conditional on the integrity-mitigation design**. The
thing that failed the condition is **the design we wrote**, and specifically one component of it:

**§4.1's band was derived once and never re-derived.** It is centred on the measured median
log-basis — 0.16 was handled correctly at declaration, the mechanism statement is there, the
falsifier was stated. But the centre moved across four calibrations from **+4.94 to +9.40 bps**,
and the band's half-width is barely wider than the quantity's own daily range. A guard fitted to
one hour and then held fixed across a day will refuse ordinary data on any instrument whose
basis drifts, which is every perpetual. **That is a property of our fitting procedure, not of
Hyperliquid's book.**

The falsifier fired, and it fired cleanly: four blackouts up to 253 s with Kraken publishing
4,549 frames inside the widest and `kraken_dt` at 0.00 s. The counterpart feed was healthy and
publishing. The band refused anyway.

---

## 3. THE EVIDENCE THAT THE REST OF THE STACK IS SOUND

Two independent measurements say the problem is localised to §4.1.

**§4.3 (staleness) reproduced to 0.2% across a full day.** Re-derived rather than ported — Kraken's
~106 ms doctrine would have fired constantly, and the documented ">= 0.5 s" is a floor, which
cannot bound staleness. Bound = `6 × observed p99`, floored at 5 s, **per feed**:

| calibration | slow | fast |
|---|---|---|
| 02:50Z | 34.59 s (p99 5.766) | 5.32 s (p99 0.887) |
| 11:51Z | 34.53 s (p99 5.756) | 5.03 s (p99 0.838) |
| 03:52Z | 34.55 s (p99 5.759) | 5.00 s (p99 0.832) |

The slow-feed bound sits within **0.2%** across a full diurnal cycle. **Cadence is a stable venue
property** — this is the most reproducible measurement in the whole WO. Final run:
`refused_staleness: 0` across seven disconnects and two feed re-pointings.

(§4.3 did latch during the run, taking the feed offline for 5 h 39 m while reporting healthy. That
was a two-clock bug in `_emit`, found by watching rather than testing, and it is fixed with four
tests including a mutation that reproduces the latch. The latch was in our emit path; the bound
itself never moved.)

**The venue's economics were confirmed over 36.5284 covered hours** — measured continuously, not
asserted from instants:

- **Touch spread p50 0.1569–0.1585 bps** on every leg and both feeds, against WO-065's 0.157/0.158
  from five instants. **WO-065 HOLDS.**
- **$100 fill cost p50 0.0784–0.0792 bps** — exactly half the touch spread, i.e. a $100 order
  fills entirely at level 1 and walks no levels. Level-walking on 1.3–2.9% of frames, at most
  ~1.9 bps.
- The 20-level slow feed could fill $100 on **every frame of every leg**; the 5-level fast feed
  could not on 29 frames. §3.4's depth choice has real content.

Continuous observation also **contradicted** WO-065's `$16,177` minimum L1 notional — the measured
minimum is **$1**, with 17–24% of frames below the figure called a minimum. That is a correction
to our own prior reading, not a mark against the venue, and it supersedes the snapshots as §5
required. Note the regime it exposed: **the spread does not widen when the touch is dust** — the
$1 touch and the 0.157 bps touch are the same frame. The 20-level book still carries p50
**$8.7–9.5M** cumulative bid notional when L1 is $1.

---

## 4. THE ONE THING NO FIX REACHES

**Hyperliquid publishes no checksum, no sequence, and no version.** CRC32 answers *"is my book
byte-identical to the venue's?"* against the venue's own authority. Nothing in the four
mitigations answers that question, and **no arrangement of them ever will**. Everything the stack
establishes is internal consistency between our own observations.

**Consistency is not correctness.** This is not a defect to be scheduled — it is a property of
choosing a checksumless venue, and it does not improve with a better band, a longer window, or a
fifth mitigation. It is the residual that survives every repair proposed below.

**The residual, as stated in the report:**

> The corpus is a record of frames that *survived a guard whose threshold was fitted to one hour
> and whose reference feed is a separate process with no declared lifetime*. It establishes that
> our view was internally consistent and cadence-bounded. It establishes nothing about whether any
> snapshot matched the book Hyperliquid matched against, and its completeness is conditioned on a
> band that measurably refused ordinary data.

---

## 5. THE FIVE DEFECTS, SPLIT BY WHETHER THEY ARE REACHABLE

| # | defect | reachable? |
|---|---|---|
| 1 | Nothing establishes correctness; no checksum, sequence, or version exists | **NO — permanent** |
| 2 | §4.1 deletes data in a market-correlated way (99.4% of all refusals) | YES — rolling re-derivation |
| 3 | §4.1 has an undeclared hard dependency on a second live process | YES — declare it, give it a liveness bound |
| 4 | §4.2, derived honestly, is nearly inert (0.05% at 22.5–36.0 USD) | YES — but see below |
| 5 | The stack can take the feed offline and say nothing; counters reach disk only at run end | YES — per-segment counters |

**On #4, honestly:** the fix is real but the ceiling is low. §4.2's tolerance had to widen to
22.5–36.0 USD (~36–57 bps at $63k) precisely because the slow feed's ~5.4 s cadence lets the tape
print ~11 times between snapshots. A one-tick tolerance refused 33.3% of slow-feed frames and the
refusals correlated with price *movement* — the surviving corpus would have been systematically
calmer than the venue. So §4.2 is inert **by derivation**, and tightening it reintroduces the same
market-correlated deletion that sank §4.1. It catches grossly dislocated prints and little else.
That is what it is worth, and it should not be counted on to carry weight it cannot.

---

## 6. THE TWO PATHS, AND WHAT WOULD SETTLE IT

**Path A — revert to dYdX now, per D56.** The verdict is negative; the rule fires. Carries the
dust-touch declaration and a fill model that never trusts the touch. Note what this costs on
measured evidence: dYdX's quoted touch was **$12.73** in WO-065 round 5 with real liquidity 36
ticks away, so a $100 buy paid **4.937 bps** on the narrowest quoted spread of the window. dYdX is
not free of the dust-touch problem — it is where the problem was first measured.

**Path B — repair #2, #3, #5, re-run a fresh window, re-ask §4.5.** The report's own condition:
*"if those are done and a fresh window shows the band refusing no ordinary data, the question is
worth re-asking."*

**The falsifier for Path B, stated in advance so it cannot be argued after the fact (0.12):** a
fresh window in which the re-derived band refuses **any** frame that the venue and its counterpart
both treat as ordinary — a refusal while `kraken_dt` is inside tolerance and the counterpart feed
is publishing — falsifies the repair and Path A fires without further argument. The same
observation that killed the first band kills the second. No new band gets a second interpretation.

**What Path B does NOT buy at any price:** defect #1. Whatever the outcome, trading Hyperliquid
means trading a venue whose book we can never verify against its own authority. If that is
unacceptable as a standing position, the answer is Path A and there is no measurement worth
taking first.

---

## 7. WHAT IS OWED REGARDLESS OF THE RULING

- **CI on the WO-061..066 arc.** Run `32496621211` is the first CI to see any of it; the previous
  run was `31299001628` (WO-060, 2026-08-09), nineteen commits back.
- **Two seam causes that do not fit** — no cause exists for a guard-induced blackout, and none for
  a run that ended by completing its declared duration. Two labels are currently wrong. **Held at
  the lead's instruction** until the venue is ruled, since a reversion changes which causes matter.
- **A broken instruction, logged as such.** The tree was frozen for the capture window; the freeze
  was broken mid-window when both feeds latched dark and the run was producing nothing. Logged as
  judgement against an explicit instruction, not as authorisation.

---

## 8. THE ASK

**Rule on the venue.** Path A or Path B. Everything downstream — paper validation on native
capture, the pre-registered HF strategy, the $100 instrument under D55's three conditions — sits
behind this and none of it has been started.

The rest of the WO-066 queue is held pending that ruling, except item (a) (`--seam-cause` with no
referent must refuse), which is repaired because it is venue-independent and it is the defect that
let a wrong-`CORPUS_DIR` launch read as healthy.
