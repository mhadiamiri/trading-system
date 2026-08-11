# WO-066 — HYPERLIQUID CAPTURE SPIKE + INTEGRITY-MITIGATION DESIGN. One WO.
#
# D56: Hyperliquid is the execution venue, **conditional on the integrity-mitigation design.**
# The venue leads on cost while having NO integrity mechanism at all — no checksum, no sequence.
# **This project does not trade data it cannot verify.**
# One WO because the mitigations are only testable against the live feed.

BASE: current HEAD (§1 reports actual — do not pin).
GRANT REQUIRED: **this WO opens a socket** to a new venue. Read-only public WebSocket, no order path,
no credentials, no wallet, no signing key. Terms in §2; **the socket does not open until §2's
preflight is green and the operator has confirmed.**
SHIP IMPACT: **YES** (new adapter). Full discipline.

**If the mitigations cannot produce a feed we would certify, the decision REVERTS TO dYdX** with the
dust-touch declared and a fill model that never trusts the touch (D56). **A negative outcome here is
a legitimate result, not a failure** — say so plainly and stop rather than weakening a mitigation to
make the venue pass.

---

## §0 RULES OF ENGAGEMENT
0.1 No discretion. Code wins: STOP and report.
0.1e Cite or declare-with-derivation. Unobtainable → DECLARED UNKNOWN, never estimated.
0.3 Bite proofs: four artifacts, sha256 exact-restore, discriminating mutations.
0.4 Preservation duals mandatory, local and direct.
0.5 Report every attempt.
0.6 AUTO MODE OFF.
0.9 **Assert the economic effect, not the event record.** A mitigation that logs a divergence but
    does not stop the system acting on suspect data is a log line, not a guard.
0.11 Enumerate, do not assume the count.
0.12 Every observation offered as corroboration states its falsifier.
0.14 **Reachability**: every BUILT row names its production call site. An unwired mitigation is the
    WO-055 defect and it is the likeliest failure mode of this WO.
0.15 Margin-bearing declarations round up and say so.
0.16 Every declared bound comparing two quantities states, at declaration, what mechanism generates
     each and **whether they are simultaneous**. **§4.1 is entirely this shape — two venues, two
     clocks, two books — and it is where this rule most applies in the whole project.**
0.19 A premise is a declared figure. Every figure states the order size / regime it was computed at.

---

## §1 CONFIRM STATE
Actual HEAD, `git diff -- src/` empty, gates green, both corpora verify. `phaseb_20260809` status —
**and note that §4.1's mitigation depends on a RUNNING Kraken feed**, which changes leg 3 from an
optional fallback activity into an input. State whether it is running.

---

## §2 THE SOCKET GRANT — preflight before any connection
Restate the terms as the run's contract: **read-only public WebSocket, BTC perp book + trades, no
order path reachable, no credentials, no wallet, no signing key, `TRADING_ENV=paper`.**
Run the **eight-term preflight fresh, not inherited**, adapted to the venue — and state per term how
it maps, since several were written for Kraken. **Term 7 executed, not printed** (the WO-044 §3.7
scar). **Confirm no order path exists in the adapter at all** — not disabled, absent.
**Report the preflight block and STOP for operator confirmation before connecting.**

---

## §3 THE CAPTURE SPIKE
3.1 A minimal Hyperliquid adapter under the venue abstraction. **State what transfers unchanged from
    the Kraken adapter and what is new** (0.11 — enumerate the message kinds the socket actually
    sends; WO-056 found six on Kraken where two were assumed).
3.2 **Duration: enough to observe the regimes the depth reads could not.** Declare it and derive it —
    five instants proved a single read can misrepresent a venue by 38×, so state what continuous
    observation is needed to supersede that, and round up (0.15).
3.3 Corpus discipline transfers: segments, manifest, **capture-time hashes**, gap ledger, the
    default-deny reader's requirements. **State per element whether it transfers or needs adaptation.**
3.4 **The 5-vs-20 level question**: subscribe at the deeper setting if available and record which.
    **Declare the level count as the feed's evidentiary bound** (§4.4).

---

## §4 THE FOUR MITIGATIONS — designed, built, and each one bite-proved

### 4.1 CROSS-VENUE PRICE GUARD — the checksum's replacement
Hyperliquid's mid continuously reconciled against **our own Kraken feed** within a declared band;
divergence beyond it means our Hyperliquid view is suspect and **the system refuses to act on it**
(the FR-018a(d) instinct for a checksumless world).
- **0.16 IS THE WHOLE DIFFICULTY HERE, STATE IT AT DECLARATION**: Kraken BTC/USD spot mid and
  Hyperliquid BTC-perp mid are **different instruments on different venues with different clocks**.
  They are **NOT the same quantity** and they are **NOT simultaneous**. A perp trades at a basis to
  spot; the basis is real and varies. **A band derived as if they should match is the F6 error.**
  Derive the band from the **measured** spot-perp basis distribution over the capture, plus a
  timestamp-alignment tolerance — **not from a guess, and not from a single instant.**
- **Bite proof:** BITE — inject a synthetic Hyperliquid mid outside the band → the system REFUSES
  (assert the economic effect: no MarketState emitted / no decision acted on, not a log line, 0.9).
  DUAL — a normal basis excursion inside the band does NOT refuse (a guard that fires on ordinary
  basis is worse than none). MUTATION — remove the comparison → the bite fails, the dual passes.
- **Falsifier (0.12): what observation would show the band is wrong?** State it.

### 4.2 TAPE-VS-BOOK RECONCILIATION
Trade prints must be consistent with the book state we hold — a book that disagrees with its own
prints is detectably wrong.
- State precisely **what consistency means** (a print inside the held spread? at or through a level
  we hold?) and **what this CANNOT detect** — the WO-063 line: *integrity failures are loud;
  semantic mismatches are silent.*
- Bite proof with a discriminating mutation.

### 4.3 STALENESS AND LIVENESS BOUNDS — re-derived for ≥0.5s cadence
The existing doctrine assumes Kraken's ~106 ms. **Re-derive, do not port.** State the bound, its
derivation from the observed cadence distribution (not the documented figure), and the refusal
behaviour when exceeded.

### 4.4 THE EVIDENTIARY BOUND — declared, not mitigated
5 or 20 levels is what the feed gives. **Declare what the corpus can and cannot support**: at 20
levels, depth beyond level 20 is unobserved, so any figure depending on deeper book is
unavailable **by construction**. State it where a future WO will hit it — this is the fidelity rule
applied to our own capture.

### 4.5 THE CERTIFICATION QUESTION — answer it explicitly
**Do these four together produce a feed we would certify?** Not "are they implemented" — **would we
trade on it?** State what the stack DOES guarantee and what it DOES NOT, and name the residual.
Compare honestly against CRC32: **consistency is not correctness.** If the answer is no, say so and
recommend the dYdX reversion — that is a legitimate outcome (D56) and the report should not strain
to avoid it.

---

## §5 THE DEPTH FIGURES, RE-VERIFIED (D56 carries the stress caveat forward)
The five depth reads were five quiet instants. Against continuous capture, restate: touch spread
distribution, level-1 notional distribution, **and the regimes observed** — with the eighth dimension
declared. **State whether WO-065's 0.157 bps touch and $16,177 minimum L1 hold up over days**, or
whether continuous observation contradicts the snapshots. Either way it supersedes them.

---

## §6 ACCEPTANCE
Preflight green with operator confirmation before connect; no order path present; adapter capturing
with corpus discipline; the four mitigations built, **wired (0.14 — name the production call site for
each)**, and each bite-proved with a discriminating mutation; the cross-venue band derived from
measured basis with its 0.16 mechanism statement and falsifier; the certification question answered
explicitly with its residual; depth figures re-verified against continuous observation with regimes
declared; `corpus_20260805`/`validation_20260809` untouched; all gates; CI green both legs (real run
number, counts from job logs).

## §7 REPORT — `WO-066-REPORT.md`
The preflight block; what transferred vs what is new; the four mitigations with their bite proofs
verbatim and their wiring; the measured basis distribution and the derived band; **the certification
verdict with its residual**; the re-verified depth figures and regimes; every attempt; any STOP; CI.

**THEN STOP.** Next: paper validation on native capture → pre-registered HF strategy → the $100
instrument under D55's three conditions.