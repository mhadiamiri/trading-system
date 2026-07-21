# Certification is bounded by what the certifying artifact contains (WO-016 D26 §5)

**Date:** 2026-07-21 · **Context:** WO-016 checksum-render defect vs A3's 1254/1254 sweep · **Author:** project lead

> "A fixture cannot witness a code path its data does not reach. A3's 1254/1254 was TRUE and
> certified less than it appeared to: the ground-truth vector fed decimal strings, so the
> Decimal-to-str path went unexercised and a formatting defect affecting only small
> quantities survived a clean sweep against real venue data. The 0.1h analogy is exact —
> there, a test supplied a precondition production could not produce; here, a fixture
> supplied a representation production does not always produce. Both are the same epistemic
> event: CERTIFICATION BOUNDED BY WHAT THE CERTIFYING ARTIFACT HAPPENED TO CONTAIN. The
> accretion doctrine closed both — the old fixtures could not reach this path; the new 200
> can, forever. Each live capture widens the witnessed domain; that is the doctrine's stated
> purpose, not merely its habit."

**Consequence:** the new 200-capture fixture
(`tests/fixtures/kraken_v2_checksum_captures_wo016.json`) is labelled with its evidentiary bounds —
*"witnesses SMALL-QUANTITY RENDERING and REPEATED-PRICE APPLICATION"* — so the next defect class that
slips past A2 (book/checksum logic), A3 (rendering), and this fixture is diagnosed against known
coverage, not assumed completeness.
