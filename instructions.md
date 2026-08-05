# WO-044 — RESUMABLE 24-HOUR CORPUS. One corpus-id, N runs, every seam labeled.
#
# D45: "Every seam is a declared ledger record — this is MORE honest than one unbroken process,
# not less." An in-run venue disconnect and an inter-run policy shutdown are the same epistemic
# object: a bounded window with no data, a declared cause, a true duration.

BASE: current HEAD — confirm in §1. Supersedes WO-043's one-continuous-process definition.
GRANT (amended, D45): one corpus-id, all resume runs toward 24 CUMULATIVE hours. Expires on corpus
completion or in **14 days**, whichever first. Each resume carries its OWN full preflight.

SCOPE: §2 verify run-3's retroactive eligibility (D45 ruling 3); §3 build resume support; §4 the
long-outage policy (15 min); §5 run and accumulate. Commit green before capturing.
SHIP IMPACT: likely YES (resume + outage policy touch the capture path). Full discipline.
REPORTING: PER-ITEM.

**OPERATOR PREREQUISITE (before any run): the security policy that shuts the machine down must be
DISABLED and confirmed. That policy caused two lost runs. State it confirmed in the preflight.**

---

## §0 RULES OF ENGAGEMENT
0.1 No discretion. Code wins: STOP and report.
0.2 Stay inside the grant: public feed, read-only, no order path, TRADING_ENV=paper.
0.4 **The ledger owns honesty.** Every seam and every outage is a record with a declared cause and
    TRUE duration. Never smooth a seam, never shorten an outage, never stitch a book across a gap.
0.5 Report every attempt.
0.6 Auto mode OFF (grant condition 2), operator-confirmed.
0.7 BUILT-VS-OPERATED (D24): the capture runner, gap ledger, checksum, breaker, detachment,
    rotation are OPERATED (proven across four runs). Resume support + the outage policy are THIS
    WO's build.

---

## §1 CONFIRM STATE
HEAD, 237 both interpreters, `git diff -- src/` clean, CI green. Confirm the amended grant terms and
the 14-day expiry window (state the expiry date). Confirm the shutdown policy is disabled.

---

## §2 RUN-3 RETROACTIVE ELIGIBILITY (D45 ruling 3 — verify as FACTS, not belief)

Run `20260730152029` (~3h55m, 4 complete segments + 1 partial, live reconnect recorded) counts
toward the cumulative 24 **only if all four hold as demonstrable evidence**:
  (a) full preflight evidence EXISTS for that run — paper-env asserted, suspend armed, load recorded;
  (b) its segments are HASHED in a manifest (note: no MANIFEST.json was written — determine whether
      hashes can be computed now over the preserved segments and whether that satisfies the
      condition, or whether absent-at-capture-time hashing disqualifies it. State your reading and
      why; if uncertain, it does NOT count — provenance must be demonstrable);
  (c) its gaps are LEDGERED (the 17:45:53 VENUE_CONNECTION_CLOSED resume is — confirm the ledger is
      complete for the run);
  (d) it ran the same proven machinery at the same HEAD-adjacent state as this WO.
Verdict: COUNTS (and how many hours) or MACHINERY-VALIDATION-ONLY (cumulative starts fresh). The
partial 19Z segment: state whether a partial hour counts or only complete segments do.

---

## §3 BUILD RESUME SUPPORT (the five ratified conditions + D45's two additions)

3.1 **Corpus-id spanning runs.** A stable `corpus_id` under which multiple `run_id`s accumulate.
    Directory layout groups all runs of a corpus. State the scheme.
3.2 **Each resume = new run-id with its OWN full preflight** (condition 1). No inherited
    preconditions: paper-env, no-credential, suspend armed, load recorded, rotation loaded, ledger
    armed, auto-mode confirmed, kill-switch — all re-demonstrated per resume, logged as that run's
    opening record.
3.3 **The seam is an explicit ledger record** (condition 2) with a declared cause code and TRUE
    duration: `PROCESS_RESTART` / `POLICY_SHUTDOWN` / `OPERATOR_STOP`. Declare these in the reason
    vocabulary (they are runtime decision reasons — the corpus archives them). Duration = last frame
    of prior run → first frame of resumed run, measured, never estimated.
3.4 **NO book state across a resume** (condition 3). Each resume takes a FRESH Kraken snapshot and
    rebuilds. **D45 addition (a): the resume snapshot's checksum MUST validate before any MarketState
    emits** — same FR-018a(d) semantics as any resync. A resumed segment starts life proven, not
    assumed. If the snapshot fails validation, the resume does not begin emitting — it retries or
    STOPs; state the behavior.
3.5 **Manifest spans the corpus-id** (condition 4): all segments from all runs, each with SHA-256,
    plus inter-run seams as first-class ledger records.
3.6 **D45 addition (b): the default-deny reader treats seams identically to in-run gaps** — same
    refusal semantics, same acknowledgment machinery. Confirm NO new reader logic is needed (the
    seam is a gap with a bigger cause code). If the reader needs a change, that is a finding — STOP.
3.7 **Cumulative-hours accounting:** a mechanism that reports, at any time, total labeled continuous
    hours across the corpus-id, seam count, and remaining to 24. This is the progress meter.

**Bite proof (0.3-equivalent, four artifacts, sha256):** simulate a resume — run, kill the process,
resume under the same corpus-id — and prove: the seam is ledgered with cause and true duration, the
resumed run has its own preflight record, a fresh validated snapshot was taken, no book state
carried, the manifest spans both runs, and cumulative hours sums correctly. Restore, sha256.

---

## §4 THE LONG-OUTAGE POLICY (D45 ruling 2 — X = 15 minutes)

4.1 A sustained venue outage enters bounded retry/backoff for up to **15 minutes**, recorded as
    **ONE gap record** with its TRUE duration and cause. The retry ladder inside it keeps the FULL
    forensic trail — attempts, backoff intervals (D-r10 tail machinery unchanged).
4.2 At 15 minutes the **breaker STOPs** with the standard forensic tail. The breaker remains the
    sole run-terminator; X only widens what it tolerates before judging.
4.3 **D45 boundary: the suspend detector and the outage window are INDEPENDENT.** A host suspend
    DURING an outage still voids affected windows under D24. Network patience does not extend to
    clock divergence. Prove they are independent — a suspend inside an outage must still VOID.
4.4 Bite proof: an outage under 15 min → one gap record, retries in the tail, run continues. An
    outage past 15 min → breaker STOP with forensic tail. A suspend during an outage → windows VOID.
    Four artifacts, sha256.

---

## §5 RUN AND ACCUMULATE
5.1 Commit §3/§4 green with CI on the commit BEFORE capturing. Launch detached (the proven method).
5.2 Capture toward 24 cumulative hours. On any interruption: restart under the SAME corpus-id, new
    run-id, full preflight, fresh validated snapshot, seam ledgered. Repeat until cumulative ≥ 24h
    or the 14-day grant expires.
5.3 Report cumulative progress after each run: hours accumulated, seams and their causes, remaining.
5.4 **Do NOT stretch or pad a run to hit a number.** Sufficiency against the real seam count is the
    lead's ruling (condition 5 / D-r13) when it lands.

## §6 ACCEPTANCE
- Run-3 eligibility verdict with evidence (counts + hours, or validation-only)
- Resume support built; all five conditions + D45's two additions demonstrated; resume bite proof
- Outage policy at 15 min; three-case bite proof incl. suspend-during-outage independence
- Seam cause codes declared in the vocabulary; reader unchanged (or the finding reported)
- Cumulative-hours accounting works
- CI green both legs on the pre-capture commit (real run number)
- Corpus-spanning manifest; per-run preflight records; every seam ledgered

## §7 REPORT — `WO-044-REPORT.md`
Run-3 verdict; the resume mechanism and its bite proof; the outage policy and its three-case proof;
the seam vocabulary; cumulative accounting; each run's preflight + duration + seam; the running
cumulative total; every attempt; any STOP; CI run.

**THEN report at each interruption and at 24 cumulative hours.** Sufficiency is the lead's call
against the actual seam count.