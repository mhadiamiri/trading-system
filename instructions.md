# WORK ORDER — WO-003: Sprint 2 Spec Kickoff — Quote-Level Data + Observed-Spread Cost Model

**Status:** ACTIVE. Supersedes all previous instructions.
**Authority:** `.specify/memory/constitution.md` governs. If any instruction here conflicts with the constitution, the constitution wins — STOP and escalate.

**Scope of THIS work order:** produce and refine the Sprint 2 **specification only** — through `/speckit-specify` and `/speckit-clarify`. **Do NOT plan, do NOT write tasks, do NOT implement, do NOT touch any source file under `src/`.** This is a spec-authoring session. Implementation is a later, separate work order after the plan is gate-reviewed.

---

## 0. RULES OF ENGAGEMENT — read before doing anything

These are not suggestions. They apply to every task in this document.

### 0.1 No discretion on unspecified points
If a decision is not explicitly specified here, you **do not choose for yourself**. You **STOP** and ask. In particular, you may not silently change scope, defaults, channel choices, API versions, or the meaning of any field. A scope change must be *argued and surfaced*, never absorbed into text.

### 0.2 Blockers are escalated, never worked around
If a task cannot be completed as written, STOP and report: which task ID is blocked, exactly what blocks it, and what you'd need to proceed. Reporting a blocker is a success, not a failure. Do not substitute an easier path.

### 0.3 Stay inside the spec phase
This work order stops at `/speckit-clarify`. You do **NOT** run `/speckit-plan`, `/speckit-tasks`, or `/speckit-implement` in this session, and you do **NOT** edit code. If you believe planning is needed to answer a clarify question, STOP and say so — do not proceed on your own.

### 0.4 Secrets
NEVER read, print, echo, or reproduce the contents of `.env` or any credential. NEVER write a real credential value into any file or output. Editing `instructions.md` (this file) to remove a previously-committed example key is expected and required — see WO-003-A.

### 0.5 Evidence, not assertion
A task is done when you have produced the evidence this document demands — command output or file contents, not the words "done" or "verified."

### 0.6 Report format
Report per task ID: `DONE` / `BLOCKED` / `NOT DONE`, each with the required evidence. No task silently dropped.

---

## 1. CONTEXT — why this work order exists

Sprint 1 (walking skeleton) and the Bybit->Kraken venue swap are complete and pushed to a private remote. The live loop runs on Kraken's public feed, but a finding emerged: Kraken's **trade** channel delivers only ~14 events/min for BTC/USD.

The Strategy & Roadmap chat ruled on this. The finding is not a bug — it exposed that our **cost model has been using an assumed spread, not a real one**, which violates Constitution Principle V (No Backtest Without Costs — spread crossing must be modeled realistically). You cannot get spread from a trades feed. The fix is to move to **quote-level data**.

**The ratified Sprint 2 direction:**
- **Primary data source: Kraken `book` channel** (top-of-book — best bid/ask price and size). Quotes update far more frequently than trades, giving the strategy a dense, continuous signal.
- **Secondary stream: `trades`** — kept for volume/last-price enrichment only, not the heartbeat.
- **API: migrate the data adapter to Kraken WebSocket v2.** (Decision: do the channel switch and the v2 migration as ONE change. Rationale: the adapter's message layer is being rewritten for the channel switch anyway; v2's book channel has a checksum/snapshot protocol that would otherwise have to be built twice. v1 is legacy. This reverses an earlier "v1 for now" suggestion, which was withdrawn with reason.)
- **`MarketState` becomes quote-centric:** timestamp, best bid/ask price and size, derived mid-price and spread, plus rolling trade stats (count, volume, last price) over a window.
- **Cost model switches from assumed spread to OBSERVED spread.** This is the constitutional payoff of the entire change and must be explicit in the spec.
- **Checksum discipline:** v2's book channel sends a snapshot then incremental updates, CRC-checksummed. The local book must be validated on every update so it cannot silently drift out of sync — a drifted book means dishonest spread data.

**Boundary to hold:** this is a **data-layer + `MarketState` schema** change. It is **NOT** license to change the strategy's logic or interface. The strategy still takes a `MarketState` and returns a desired position. Resist any "while we're in here" strategy sophistication — that is the same trap as threshold-lowering, different door.

---

## 2. TASKS

### WO-003-A — Scrub the leaked example key from this repo

The security check reported the old Bybit key pattern still exists in `instructions.md` as an example string, and that file is tracked and pushed.

**Do:**
1. Overwrite `instructions.md` with THIS work order's content (that alone removes the old key text — confirm the string `THjVW4qXNw` no longer appears anywhere in the working tree).
2. Grep the whole repo (case-insensitive) for that key fragment and confirm zero hits: `grep -ri "THjVW4qXNw" . --exclude-dir=.git`.
3. Commit as `chore: scrub leaked example key fragment from docs`.

**Definition of Done:** grep returns zero hits; commit made.

**Required evidence:** paste the grep output (should be empty) and the commit hash.

**Note:** the key is testnet-only and being revoked, and the remote is private, so this is hygiene, not an emergency. Do it anyway — the habit is the point.

---

### WO-003-B — Generate the Sprint 2 spec

**Do:** run `/speckit-specify` with EXACTLY this description (do not edit it, do not add or remove scope):

```
/speckit-specify Change the system's market data from a trades feed to quote-level data so the cost model uses real observed spread instead of an assumption. Subscribe to Kraken's book channel (top-of-book: best bid/ask price and size) as the primary data source, keep trades as a secondary enrichment stream (volume, last price), and migrate the data adapter to Kraken WebSocket v2 as part of this change. MarketState becomes quote-centric: timestamp, best bid/ask price and size, derived mid-price and spread, plus rolling trade stats over a window. The backtest cost model must compute spread cost from the actual observed bid/ask spread, not a constant assumption. The v2 book channel's checksum/snapshot protocol must be validated on every update so the local book cannot silently drift out of sync. Out of scope: any change to the strategy's logic or interface — the strategy still takes a MarketState and returns a desired position.
```

**Definition of Done:** a new `specs/00N-*/spec.md` is generated.

**Required evidence:** report the feature branch/folder created, and the spec's section summary (user stories + count, functional requirements + count, success criteria + count).

**Then verify the spec captured the three load-bearing items** — report explicitly, per item, PRESENT or MISSING:
1. The cost model uses **observed** spread from bid/ask, and no assumed-spread path remains.
2. The v2 book **checksum/snapshot must be validated on every update** (book cannot silently drift).
3. The strategy logic/interface is **out of scope** and unchanged.

If any of the three is MISSING or weaker than stated here, report it — do not fix it silently, and do not proceed to clarify until I confirm.

---

### WO-003-C — Clarify

**Do:** run `/speckit-clarify`.

**Definition of Done:** clarify completes and produces its questions.

**Required evidence:** paste the clarification questions **verbatim**. Do NOT answer them. STOP after pasting them.

**Prohibited:** answering the clarify questions yourself, guessing at parameters (e.g. book depth, rolling-window length, checksum-failure behavior), or proceeding to plan. Those answers are decisions for the human — several shape the cost model and the data schema.

---

## 3. FINAL REPORT REQUIRED

Report status per task ID — `DONE` / `BLOCKED` / `NOT DONE` — with evidence. Then STOP.

Do not run `/speckit-plan`. Do not edit code. The clarify questions come back to the human for answers before anything proceeds.

**Anything you were tempted to decide for yourself, list it here instead and ask.**
