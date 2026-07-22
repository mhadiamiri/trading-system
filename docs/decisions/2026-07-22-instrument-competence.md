# Decision Log / Doctrine: Instrument competence (RATIFIED)

**Date:** 2026-07-22
**WO:** WO-013 follow-up item E (ratified by the project lead)
**Related:** [[baselines-attract-scope-errors]], [[structural-satisfaction-retires-the-defect-class]]

---

> An instrument is COMPETENT FOR THE QUESTION IT WAS DESIGNED TO ANSWER, and borrowing it for an
> adjacent question requires RE-ESTABLISHING COMPETENCE BY MEASUREMENT, NOT BY PROXIMITY. This is
> rule 0.1e's 'evidence competent to support the claim' extended from evidence to instruments. The
> re-baseline rule borrowed a starvation detector for cost accounting because it was the timer we
> had; two work orders of scope corrections later, the borrowed instrument's transfer function was
> finally measured and the loan was called. `mean_cycle = span/actual_samples` measures the
> sleep-wake cycle, and below the ~30.6 ms/frame budget per-frame work eats idle slack the sampler
> never sees — it responds near saturation because saturation is what it was built to detect.
> Corollary, third instance: a proof requirement that MEASURES out-earns one that ASSERTS. The
> containment proof was ordered to verify enclosure and instead measured FITNESS — it answered a
> question we had not thought to ask by answering the one we had. Precedents: the A2 smoke test
> settling checksum ordering; the establishment runs exposing the noise floor. Assertions return
> the answer requested; measurements return the answer PRESENT.

---

**Applied here.** The mean-cycle re-baseline instrument was competent for STARVATION DETECTION (its
WO-014c-1 purpose) but was borrowed to gate PER-FRAME COST. Competence for the adjacent question was
established only when WO-013 item 2 measured the transfer function (~0.2 ms-cycle per ms-frame,
effective per-frame floor ~10 ms/frame). The rule is now relabelled a saturation-detection section
(progress.md), the deferral condition is wired mechanically into the tool's report form (a sub-floor
delta reads UNDETECTABLE, never "no change"), and a fit per-frame timer is deferred post-corpus —
where, per the ruling, it will carry its own declared floor, its own containment proof, and
**instrument identity in the fingerprint from birth**, entering a world where that dimension already
exists so no inheritance defect recurs.
