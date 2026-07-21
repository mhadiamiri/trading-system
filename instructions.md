FROM: Ops & Tooling
TO: Core Brain
RE: Re-run halted at its own gate — one new work order, and your authorization needed

WO-014c-3 is COMPLETE at 989600b (177 passed both orders). All six review items closed:
the persistence opt-in WAS a silent no-op and now refuses loudly (GAP_PERSIST_UNCONFIGURED)
BEFORE opening a connection; per-failure one-line summaries implemented (it was cheap);
the Shape-B sweep survived a wider net (mock.called, call_count, assert_has_calls,
assert_any_call, .mock_calls, .call_args) with the count still 1; stub-lint extended to
docstring-only bodies with 0 new hits; drift limit declared; the decision-log entry
"survives-the-failure-it-documents" created as a standing §0 review question.

THE RE-RUN HALTED AT ITS OWN PREFLIGHT — correctly, twice over.

1. HOST SUSPEND. §1.3 was non-negotiable and Claude Code refused to proceed, citing THIS
   PROJECT'S OWN EVIDENCE: the WO-014c-3 deterministic suite recorded 24063.39s (6:41:03)
   for ~4 minutes of CPU. The machine sleeps. A suspend mid-capture is indistinguishable
   from catastrophic starvation and would contaminate both the throughput series and the
   discrimination. It did not open a socket and did not fabricate a run file. Hadi has now
   set sleep to 2 hours, which covers a 60-minute run with margin.

2. NO LIVE-CAPTURE RUNNER EXISTS. This is the substantive finding. get_live_market_data
   has only ever been driven by tests with a patched transport — nothing in the codebase
   opens a real socket and drives the Data→Strategy→Risk→Execution loop for an hour. The
   re-run's §2 assumed an entrypoint that was never built.

   Ops error, and the third of its exact kind: WO-008b assumed a WebSocket that WO-008b
   was meant to build; WO-014 §1 assumed a settings.py footprint it didn't have; now the
   re-run assumed a runner. The pattern is Ops writing an order to OPERATE a thing the
   order was implicitly supposed to BUILD. Recording it as a named Ops failure mode rather
   than three coincidences.

WO-015 ISSUED (build only, no venue connection): the live-capture runner. It WIRES the
existing instrumentation rather than reimplementing it — the re-run forbids changing
throughput counting or instruments once it begins, so anything not wired now cannot be
fixed later without invalidating the run. Preflight enforcement moves INTO the runner
(refuse without persistence configured, refuse under non-paper TRADING_ENV) because
checklist-enforced rules are 0-for-N in this project. It also detects host suspend via
wall-vs-monotonic divergence exceeding the declared drift bound, and reports it loudly —
so a contaminated run is identifiable afterward rather than misread as a starvation
finding and sent chasing pipeline architecture that isn't the problem. Bite proofs on
simulated transport; the honest limit stated in the docstring.

WHAT I NEED FROM YOU — one authorization, two optional rulings.

AUTHORIZATION REQUESTED: THE FIRST REAL VENUE SOCKET, HELD FOR AN HOUR.
Claude Code flagged that this warrants explicit go-ahead rather than inheriting it from
the earlier re-run release, and Ops agrees — the prior authorization was granted when we
believed the runner existed, and the situation has changed. Everything prior touched
Kraken for 2 minutes at most. This is 60 minutes of continuous connection with the gap
ledger, failure capture, and ping_timeout=None all facing real venue behavior for the
first time.

Ops's position: the preconditions are met. TRADING_ENV=paper with the order-capable path
bite-proved unreachable, no credentials anywhere (public feed needs none), the venue is
read-only public market data, and the guards protecting this run have all been watched to
bite. The exposure is a read-only socket; the risk is a wasted hour, not a bad trade.

Requesting your explicit authorization to open it once WO-015 clears review.

OPTIONAL RULING 1 — Ops proposes the sequence stays: WO-015 (runner) → re-run → WO-013 →
CI capture + version ruling → CI green → 008c → 24h corpus. Confirm or reorder.

OPTIONAL RULING 2 — the 24-hour corpus will exceed any sleep setting. Ops expects the
runner's suspend DETECTION to become load-bearing there rather than merely diagnostic, and
that a 24-hour capture likely needs a host that does not sleep at all. Flagging now so the
corpus WO can carry it as a precondition rather than discovering it at hour three. No
action needed yet.

Nothing else is blocked. WO-015 can proceed on Ops authority; only the socket needs you.


-------------------------------------

ADDENDUM TO WO-015 — three additions from the project lead's ruling. Everything else in
WO-015 stands.

=== A. HOST_SUSPEND IS A RULED FIFTH GAP-LEDGER CAUSE — do not halt on exhaustiveness ===
WO-014c-2 ruled the cause taxonomy exhaustive at four (KEEPALIVE_RECONNECT,
CHECKSUM_RESYNC, BREAKER_RETRY_LADDER, VENUE_DISCONNECT) and instructed: "if a
gap-producing path exists that fits none of these, STOP AND REPORT — do not invent a
fifth cause."

The project lead has now RULED a fifth: HOST_SUSPEND. This is a ruled addition, not an
invention, so it does NOT trigger that STOP. Implement it.

- Emitted when wall-vs-monotonic divergence exceeds the declared drift bound
  (~5s typical, ≤43s worst case per WO-014c-3 §0.3). Divergence beyond that bound is
  suspend, not drift — the bound is what makes the two distinguishable.
- **In WO-015 and the re-run its role is DIAGNOSTIC:** record the gap, report it loudly,
  do not terminate. A contaminated run must be identifiable after the fact.
- **At corpus time its role becomes LOAD-BEARING and is the corpus WO's to implement:** a
  HOST_SUSPEND divergence INVALIDATES the affected window rather than annotating it, with
  the honest-window doctrine applying to what remains. Build the cause and its detection
  now; the invalidation semantics belong to the corpus WO.
- Declare any new reason code in the same commit. If HOST_SUSPEND fits the existing
  GapRecord schema unchanged, say so; if it needs a field, propose it and STOP.

Why it matters, on the record: without this detection a mid-capture suspend would
MASQUERADE AS CATASTROPHIC STARVATION — a wrong-thing-measured verdict at the
discrimination layer itself, sending us after pipeline architecture that isn't the
problem. This is the VOID doctrine applied prophylactically.

=== B. DECISION-LOG ENTRY — a named OPS failure mode ===
Create it. This one is about the work-order authoring layer, not the code:

  "ORDERS WRITTEN TO OPERATE A THING THE ORDER WAS IMPLICITLY SUPPOSED TO BUILD.
   Three instances: WO-008b specified how to operate a WebSocket that WO-008b was meant to
   build; WO-014 §1 scoped an amendment to settings.py while the change spanned three
   files; WO-008b-B-RERUN §2 assumed a live-capture runner that had never existed —
   get_live_market_data had only ever been driven by tests with a patched transport.
   Naming it converts coincidence into checklist: EVERY FUTURE WORK ORDER THAT OPERATES
   ANYTHING STATES WHERE THE OPERATED THING WAS BUILT AND VERIFIED, OR DECLARES ITSELF THE
   BUILDER. This is the §0 carry-over question ('does this survive what it documents?')
   extended to the authoring layer — the review loop turned on the reviewer."

=== C. AUTHORIZATION STATUS — for the record, no action ===
The project lead has AUTHORIZED the first real venue socket: one 60-minute read-only
capture under the ruled parameters (five pass criteria, five-branch discrimination, W08
thresholds), effective when WO-015 clears review. It is PER-RUN, not open-ended — a second
attempt after a VOID or failure is a new socket under the same terms, with its own
preflight and its own report.

WO-015 opens NO socket. That remains true. Noted here so the authorization's scope is in
the same record as the runner it authorizes.

Proceed with WO-015 as written, plus A and B. STOP for review at the end.

--------

update :

BEFORE COMMITTING — one question on the order-dependence fix, plus the three outstanding
addendum items.

=== Q. DOES create_live_capture_feed STILL RESOLVE FROM DATA_SOURCE? ===
You report the mode= kwarg bug was "fixed by resolving the kraken_v2 book adapter
explicitly." Confirm which of these is true:

  (a) The function still resolves the adapter from DATA_SOURCE via the registry, and the
      fix was to the BUILDER SIGNATURE / capability handling — e.g. builders that do not
      support live mode now reject it clearly, or the live path validates that DATA_SOURCE
      names a live-capable adapter and FAILS LOUDLY otherwise.

  (b) create_live_capture_feed now names kraken_v2 directly, bypassing DATA_SOURCE.

If (b): that is a Principle VII regression and I want it changed before commit. The venue
abstraction's stated property is that a venue swap is a SINGLE-MODULE CHANGE — add an
adapter, it self-registers, config names it, nothing else moves. A hardcoded adapter in
the factory's live path means Sprint 3's Coinbase swap requires editing factory.py too.
It is also the same shape as the spread_cost parameter the project lead rejected:
venue-specific knowledge migrating into a component that is supposed to be venue-neutral.

"Only one adapter supports live mode today" is a true statement and a fine reason to FAIL
LOUDLY when DATA_SOURCE names one that doesn't. It is not a reason to stop asking
DATA_SOURCE. The failure mode we want at Sprint 3 is a clear "adapter X does not support
live capture," not a silent connection to the wrong venue.

If (a): say so plainly and proceed — the concern dissolves.

Either way, log the order-dependence bug itself as a finding: a live-only kwarg passed to
a builder that rejects it, hidden by deterministic ordering, caught by the randomized scan.
Fourth time that scan has paid for itself.

=== STILL OUTSTANDING FROM THE ADDENDUM — confirm these are in scope ===
Your status lists 3 bite proofs. WO-015 §2 required SIX. Still owed:
  1. Short bounded run COMPLETES — artifacts exist and are readable (0.1i).
  2. CLEAN DEADLINE CLOSE DOES NOT RECONNECT — the preservation dual, S13 template, both
     halves in one test. This governs whether the re-run stops at minute 60.
  3. BREAKER TRIP terminates with forensic tail and retained partial capture.
Plus: declare the HOST_SUSPEND detection floor (suspends shorter than ~43s are undetected
and present as enormous lag — indistinguishable from starvation, the exact misreading the
detection exists to prevent). And the two signature changes are RATIFIED retroactively —
no rework, but 0.1a says "any signature change," not "any breaking change."

If those are already in the in-flight work, say so. If not, they are this session's or the
next one's — your call on budget, and checkpoint rather than half-implement.

Per 0.2a, nothing commits until both orders confirm 0 failed / 0 xfailed / 0 xpassed with
contracts 6/6.