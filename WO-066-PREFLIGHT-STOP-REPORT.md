# WO-066 §2 — THE SOCKET PREFLIGHT. **STOPPED for operator confirmation, as instructed.**

**§2's instruction is explicit: *"Report the preflight block and STOP for operator confirmation
before connecting."*** No socket has been opened. No adapter has been built. Nothing has been
committed to `src/`.

**And §1's note turns out to be the finding of this turn.** The WO says §4.1's mitigation depends on
a running Kraken feed and asks me to state whether it is running.

# IT IS NOT RUNNING — AND §4.1 CANNOT BE BUILT UNTIL IT IS.

---

## §1 STATE CONFIRMED

| | |
|---|---|
| HEAD | **`45af94a`** (actual, not pinned) |
| `git diff -- src/` | **empty** |
| pytest 3.14.6 / 3.11.15 | **572 passed, 2 skipped** both (315.71 s / 314.23 s) |
| import-linter | **6 kept, 0 broken** |
| `corpus_20260805` / `validation_20260809` | `e3ab1aec…` **38/38** · `884f9f00…` **3/3** |

### `phaseb_20260809` — **STOPPED**, and that is now load-bearing

```
covered        23.9984 h of 556          runs 2   seam 1   gaps 2 (both bounded, resolved)
integrity      26/26 segments verified against their capture-time SHA-256
last frame     2026-08-10T16:02:44.515Z
state          NOT RUNNING — leg 3 never opened
```

**Why this stops being an optional fallback and becomes a prerequisite.** §4.1 specifies the
cross-venue price guard as *the checksum's replacement* — the single mitigation that D56's
conditional rests on — and requires that its band be derived **"from the measured spot-perp basis
distribution over the capture."** That is not satisfiable from one side:

1. **A basis is a difference between two simultaneous observations.** With no Kraken feed running
   there is no second observation, so there is no basis to measure, no distribution to derive a band
   from, and nothing to reconcile against at runtime.
2. **The two captures must overlap in time.** A basis measured against `corpus_20260805`
   (2026-08-05→07) and a Hyperliquid capture taken now would be four days apart — not simultaneous,
   which §0.16 makes the governing objection and which §4.1 itself names as *"the F6 error."*
3. **The bite proof needs the live pair too.** §4.1's DUAL requires that *"a normal basis excursion
   inside the band does NOT refuse"* — a normal excursion can only be observed against a live
   counterpart feed.

**So leg 3 must be open BEFORE and DURING the Hyperliquid spike, not after it.** I am not opening it:
it is the operator's call and the WO does not grant it.

---

## §2 THE SOCKET GRANT — restated as this run's contract

> **Read-only public WebSocket to Hyperliquid. BTC perpetual book + trades. No order path reachable.
> No credentials. No wallet. No signing key. `TRADING_ENV=paper`.**

**The socket does not open until this preflight is green AND the operator confirms.** Neither has
happened.

### 0.11 — THE PREFLIGHT IS NOT EIGHT TERMS. IT IS TWELVE.

§2 calls it "the eight-term preflight". **Enumerated from the code rather than assumed, the
implemented preflight has twelve conditions**, and the recorded `PREFLIGHT.json` from the last real
capture confirms twelve keys:

```
paper_env · no_credential · host_suspend_armed · load_recorded · rotation_loaded ·
gap_ledger_armed · auto_mode_off · guards_armed · seam · term2_memory_gate ·
shutdown_policy_disabled · grant_expiry
```

**Four terms would have gone unmapped had I taken the count on trust.** They are mapped below.

### The twelve terms, mapped to Hyperliquid — transfers, adapts, or blocked

| # | term | maps how |
|---|---|---|
| 1 | **paper_env** | **ADAPTS — and the mapping is not clean.** The check asserts `TRADING_ENV == "paper"`. Hyperliquid has no "paper" mode; it has a **testnet** (`api.hyperliquid-testnet.xyz`). For a *read-only public book capture* `TRADING_ENV=paper` remains meaningful as **our own** guard state, and it is what gates the order path. **Kept as-is and satisfied**, with the note that "paper" here describes our system, not a venue mode. |
| 2 | **no_credential** | **TRANSFERS, and matters MORE here.** Scans `.env` for `API_KEY / SECRET / PASSWORD / TOKEN`. **WO-064 recorded that this would not see a signing key** — for Hyperliquid that gap is live, not theoretical. **Needs widening before any signing path exists**; for a read-only capture it is satisfied because no key of any kind is required. |
| 3 | **host_suspend_armed** | **TRANSFERS UNCHANGED.** Host-level, venue-agnostic. Reads the bound from the adapter class — so the Hyperliquid adapter must expose the same constant, or the term must read it from a shared home. |
| 4 | **load_recorded** | **TRANSFERS UNCHANGED.** CPU / memory-used / background-quiet. Venue-agnostic. |
| 5 | **rotation_loaded** | **TRANSFERS UNCHANGED.** Hourly segments, 3600 s, compression, 90-day retention. |
| 6 | **gap_ledger_armed** | **ADAPTS — and 0.11 applies to its cause set.** Kraken's five ruled causes include **`CHECKSUM_RESYNC`, which has no referent on Hyperliquid** (WO-063 finding). **Four of five transfer.** The fifth must be **removed or redefined, never left wired and always-zero** — that is the `checksum_failures_total` error one level up. |
| 7 | **auto_mode_off** | **TRANSFERS UNCHANGED.** Operator declaration, host-level. |
| 8 | **guards_armed** | **ADAPTS — and §2's "Term 7 executed, not printed" applies here.** The kill-switch half is venue-agnostic and executes as-is. The `TRADING_ENV` half constructs a `LiveCaptureRunner(trading_env="mainnet")` and asserts it **refuses**; that runner is Kraken-shaped, so the Hyperliquid equivalent must be **executed against the Hyperliquid path**, not inherited. **This is the term the WO-044 §3.7 scar is about and it must not be printed from a prior run.** |
| 9 | **seam** | **TRANSFERS UNCHANGED.** Corpus-id, prior run, declared cause. A new corpus-id means first-run, no seam owed. |
| 10 | **term2_memory_gate** | **TRANSFERS UNCHANGED.** Pagefile-movement gate — host-level, venue-agnostic (WO-059). |
| 11 | **shutdown_policy_disabled** | **TRANSFERS UNCHANGED.** Operator declaration. |
| 12 | **grant_expiry** | **ADAPTS.** A **new grant with its own expiry** is required — the corpus grant covers Kraken, not Hyperliquid. **Not yet issued.** |

### "Confirm no order path exists in the adapter at all — not disabled, ABSENT"

**I cannot confirm this yet, because the adapter does not exist.** I did not build it: §2 gates the
socket on confirmation, and building a new registered adapter is SHIP-IMPACT-YES work whose only
purpose is to be connected.

**What I can state now is the construction constraint and how it will be verified, so the property
is designed in rather than tested for afterwards:**

- The adapter will expose **book and trade subscription and parsing only**. No order placement,
  cancellation, signing, or account method will exist on the class.
- **Verification will be structural, not behavioural**: a test asserting that the adapter's public
  surface contains **no** method matching an order-path vocabulary, and that the module imports
  nothing capable of signing. **An absent method cannot be accidentally enabled; a disabled one
  can.** That is the difference §2 is asking for.
- The existing **"No test doubles in production code"** and **adapter-registry-is-the-sole-resolution-path**
  contracts already hold and will be re-run.

**Registry contract, read rather than assumed:** a `live_capture=True` builder must accept
`connect_fn`, `monotonic_clock`, and `wall_clock` — validated **at import time** by
`registry.register`. The Hyperliquid builder must accept all three or it will be rejected the moment
it is imported. That is a real constraint on the adapter's shape and it transfers unchanged.

---

## THE TWO THINGS THAT MUST HAPPEN BEFORE §3 CAN START

**1. Open phase-B leg 3** — and keep it running through the Hyperliquid spike. Without a concurrent
Kraken feed, §4.1's band cannot be derived from a measured basis, its bite proof cannot be
constructed, and the mitigation that D56's conditional depends on cannot be built. Everything else in
WO-066 could proceed without it; **§4.1 cannot**, and §4.1 is the one that decides the venue.

**2. Confirm the socket grant**, with an expiry, per §2.

**A third item is a decision, not a blocker:** the gap ledger's fifth cause. `CHECKSUM_RESYNC` has no
referent on Hyperliquid. **Removed, or redefined?** Left wired and always-zero it becomes a metric
that cannot move — the exact defect this project has now named three times. I will not choose that
silently.

---

## §0.5 — EVERY ATTEMPT

| # | attempt | outcome |
|---|---|---|
| 1 | Gates, corpora, HEAD | HEAD `45af94a`, `git diff -- src/` empty; suite results below |
| 2 | phase-B status | **NOT RUNNING**, 23.9984/556 covered h, 26/26 verified |
| 3 | Read the adapter registry contract | `live_capture=True` requires `connect_fn`, `monotonic_clock`, `wall_clock`, enforced at import |
| 4 | Enumerate registered adapters | `kraken_public`, `kraken_v2` (live-capable), `simulated` — **three** |
| 5 | Enumerate the preflight terms | **TWELVE, not eight** — four would have gone unmapped |
| 6 | Read terms 3.1 and 3.7 in full | paper-env / credential scan; kill-switch + TRADING_ENV guard **executed**, not printed |
| 7 | Build the Hyperliquid adapter | **NOT ATTEMPTED — §2 gates the socket on confirmation** |
| 8 | Open a socket | **NOT ATTEMPTED** |

**No socket opened. No adapter built. No `src/` change. Nothing committed.**

---

## STOPPING HERE

Per §2, this is where the WO pauses. **A negative or blocked outcome is a legitimate result** (D56),
and I would rather report a missing prerequisite than build a mitigation that cannot be validated and
call it done — that is the WO-055 defect §0.14 names as this WO's likeliest failure mode.

**On your word I will:** open leg 3, then build the adapter with the order path absent by
construction, run the twelve-term preflight fresh against the Hyperliquid path with term 8 executed,
and report it for confirmation before the socket opens.
