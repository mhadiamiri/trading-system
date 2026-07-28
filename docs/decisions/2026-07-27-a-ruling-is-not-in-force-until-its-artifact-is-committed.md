# Decision Log: a ruling is not in force until its artifact is committed (D42)

**Date:** 2026-07-27 (landed 2026-07-28 by WO-035 §2.3)
**WO:** raised across WO-031/WO-032/WO-034; ratified as **D42**; landed by WO-035
**Authority:** D42 (this ruling); D24 (built-vs-operated); D41 (apparatus honesty)
**Related:** [[a-doctrine-needs-a-guard-that-reaches-every-producer]],
[[bound-versus-race-is-a-measurement-not-a-margin]],
[[an-enumeration-is-only-as-good-as-its-identifiers]],
[[a-residual-clock-read-is-classified-not-waived]],
[[instrument-competence]], [[a-verdict-inherits-its-instrument-s-coverage]]

---

## The entries (both ratified verbatim)

**The standing step:**

> **A ruling is not in force until its artifact is committed.** Every WO's §1 confirms that the
> artifacts it reads reflect all rulings made since those artifacts were written. Where a lag is
> found, the amendment lands before the work proceeds.

**The regeneration rule:**

> **A regeneration must read the original, not a restatement of it; before trusting a diff, confirm
> both sides derive from the source, not from each other's corrections.**

---

## Specimen 1 — the ruling that was described but not committed

WO-031 was ordered to classify batch B. Its §2 required confirming that D39's amendment to
`evidence/WO-029/batch_partition.md` had landed. It had not: the file had exactly one commit, the
phrase the amendment was supposed to strike was still present, and the amendment's own language
existed **only inside `instructions.md`**. WO-031 stopped with nothing classified.

The ruling was real. It had been made, and everyone downstream believed it was in effect. But Claude
Code — and any reader — operates on the tree, and on the tree it did not exist. An uncommitted ruling
is an unverified OPERATED row (D24) wearing the costume of settled fact.

## Specimen 2 — the same failure, three WOs later, in the same file

WO-031 §3-bis reclassified entry 35 from BOUND to RACE and **correctly escalated instead of amending**
— a denominator change is the lead's call. D40/D41 ratified it. And then nobody landed it.
`batch_partition.md` still read `batch C = 8` when WO-034 arrived to convert batch C, and still read
8 when WO-035 began. Two work orders planned against an artifact that a ruling had already superseded.

The lag is not carelessness; it is structural. The WO that discovers a needed amendment is usually
forbidden from making it (escalation), and the WO that receives the ruling is usually pointed at the
next task rather than at the artifact. Nothing in the process owned the landing. Hence the standing
step: **§1 checks currency, every time**, and the check is cheap precisely because it is mechanical.

## Specimen 3 — the diff that measured the wrong side

WO-034 regenerated the audit's identifiers as pytest node IDs and diffed them against the audit's
prose. The first run reported four mismatches — comfortably matching what D41 already knew — and
flagged one oddity: **entry 5 matched exactly when the ruling said it should not.**

That oddity was the whole finding. The transcription had been taken from
`evidence/WO-029/batch_partition.md`, a *restatement* that had silently repaired several of the
audit's names when it re-derived the table. So the diff measured the restatement's accuracy, not the
audit's. Re-transcribing verbatim from `wall_clock_race_audit.txt` trebled the population: **nine
mismatches, not four**, six of them races, four of them in the batch about to be converted.

**The apparatus was wrong in the same way the thing it measured was wrong** — D41's apparatus-honesty
rule turned inward on the instrument. A regeneration that reads a corrected copy cannot find the
corrections; it can only confirm them. And a version of that script that never questioned its own
source would have reported "one extra mismatch" and looked entirely plausible.

---

## Standing consequence

1. **§1 of every WO performs the artifact-ruling currency check.** Name the artifacts the WO reads;
   confirm each reflects every ruling since it was written. A lag is landed before the work proceeds,
   not carried.
2. **The WO that receives a ratification lands it.** Escalation defers the *decision*, not the
   *bookkeeping*. A ruling with no landing commit is a to-do, however firmly it was made.
3. **A regeneration reads the original.** Before trusting any diff, confirm both sides derive from
   the source rather than from each other's corrections. Where a restatement exists, treat it as a
   third party to be checked, never as the baseline.
4. **A suspicious agreement is evidence.** In specimen 3 the tell was not a failure but a *match* —
   an expected mismatch that failed to appear. Reconciling that quietly would have buried the finding.

**Landed by WO-035 §2:** `batch_partition.md` now reads batch C = 9 with entry 35 folded in and its
reclassification noted, and its race identifiers are restated as node IDs with the prose retained as
superseded historical record. That file is this ruling's own specimen — it carried the lag that
produced the doctrine.
