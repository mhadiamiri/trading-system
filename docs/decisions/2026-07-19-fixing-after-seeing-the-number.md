# Decision Log: "Fixing after seeing the number and re-running to green is exactly how a wrong assumption survives contact."

**Date**: 2026-07-19 · **Related WO**: WO-008b-A3 addendum D, entry 1

Recorded as the reason **WO-008b-A2 declined to fix the rendering defect in the run
that discovered it.**

A2's smoke failed: the snapshot checksum mismatched on the first live frame. The cause
was diagnosable within minutes and the fix was one keyword argument. The temptation to
apply it and re-run was proportionally large — and §4.3 had pre-ruled against exactly
that, before anyone knew what the failure would be.

**Why the discipline matters here specifically.** The pre-ruled hypothesis was that a
repeated checksum failure meant the *ordering* defect. It did not. Had A2 patched the
rendering and re-run to green, the run would have "passed" and the ordering question —
the entire reason the run existed — would have been silently answered "yes" by a green
light rather than by evidence. Instead A2 stopped, captured 1192 frames, and proved the
ordering fix correct **offline, from the failing run's own data**: 1070/1070 post-update,
0/1070 pre-update, with a negative control.

A failed run that is diagnosed honestly produced *more* verified knowledge than a passing
run would have. A3 then fixed the rendering as its own work order, starting from that
diagnosis, and the re-run passed all five criteria with 0 checksum failures.

The general rule: **a fix applied after seeing the number is untested against the belief
that produced the number.** Separating discovery from remedy is what keeps the remedy
falsifiable.

**Evidence**: `evidence/WO-008b-A2/smoke_diagnosis.txt`, `evidence/WO-008b-A3/`
