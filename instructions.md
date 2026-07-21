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

WO-015 — ONE CHANGE REQUIRED BEFORE ACCEPTANCE, plus three items still owed.

The boundary handling is genuinely excellent and stands: the first cut broke two contracts
and you fixed the design rather than the contract (rule 0.4). That is the same pressure
that produced factory.py:15 at af27491, with the opposite outcome.

=== REQUIRED CHANGE — create_live_capture_feed MUST RESOLVE FROM DATA_SOURCE ===
Confirmed (b): registry.create("kraken_v2", mode="live", ...) hardcodes the venue.

THE REASON IS NOT SPRINT 3. It is today:

  Set DATA_SOURCE=kraken_fixture, launch a live capture, and it connects to KRAKEN
  MAINNET. The configuration says one thing and the system does another — on the single
  code path that holds a real venue socket.

WO-008b-A1 deliberately made venue mode distinguish kraken_fixture from kraken_mainnet.
Ignoring DATA_SOURCE on the live path undoes that at the resolution layer.

REQUIRED:
- create_live_capture_feed resolves the adapter from DATA_SOURCE via the registry.
- If the named adapter does not support live capture, FAIL LOUDLY and specifically —
  "adapter '<name>' does not support live capture" — with a declared reason code.
- That is the correct fix for the order-dependence bug too. A live-only kwarg reaching a
  builder that rejects it should produce a clear refusal, not be avoided by bypassing
  configuration. The bug was real; the remedy was too broad.
- Mechanism is yours: builders declaring live capability, or catching the rejection and
  re-raising with a specific message. State which and why.
- BITE PROOF, four artifacts, sha256: DATA_SOURCE names a non-live-capable adapter →
  live capture REFUSES with the specific message, before any connection. Assert the
  observable end state.

NOTE FOR THE RECORD — a new shape worth logging. Import-linter passes here and the
principle is violated anyway: no concrete adapter is imported, contracts stay 6/6, and the
venue lock lives in a STRING LITERAL that no import contract can see. The mechanical guard
is green while the boundary is soft. Add one line to the decision log:
  "A mechanical boundary guard constrains the SHAPE of a dependency, not its CONTENT. An
   import contract cannot see a hardcoded venue name. Contract-clean is not
   principle-clean, and Principle VII's single-module-swap property has to be checked by
   reading, not only by linting."

=== STILL OWED FROM THE ADDENDUM ===
Three of the six bite proofs required by WO-015 §2 are still missing:
  1. SHORT BOUNDED RUN COMPLETES — artifacts exist and are readable (0.1i), not that a
     method ran.
  2. CLEAN DEADLINE CLOSE DOES NOT RECONNECT — the preservation dual, S13 template, both
     halves in one test. THIS GOVERNS WHETHER THE RE-RUN STOPS AT MINUTE 60. We have
     already shipped a preservation guarantee (S10) certified while its production trigger
     did not exist; a deadline close quietly routing into the reconnect path is that shape
     again, and we would learn it at minute 61.
  3. BREAKER TRIP terminates with forensic tail and retained partial capture.
If the 6 tests in test_live_capture.py already cover these behaviors, say so and supply the
four-artifact proofs. If a behavior is not implemented, report it — do not add it silently.

DECLARE THE HOST_SUSPEND DETECTION FLOOR in the detection's docstring: a suspend shorter
than ~43s is NOT detected and presents as an enormous lag spike — indistinguishable from
catastrophic starvation, the exact misreading the detection exists to prevent. Declared
limit, not a defect; the threshold must sit above drift or it fires on drift.

Signature changes (LiveTradingLoop.run(feed=…), _build_kraken_v2) are RATIFIED
retroactively — additive, default-preserving, 16 live-loop tests green. No rework. Noting
only that 0.1a says "any signature change," not "any breaking change."

=== THEN VERIFY, COMMIT, PUSH, STOP ===
Both orders, linter, contract count, ruff, secret scan. Explain the delta. Per 0.2a nothing
commits until 0 failed / 0 xfailed / 0 xpassed with contracts 6/6.

Do NOT open the socket.