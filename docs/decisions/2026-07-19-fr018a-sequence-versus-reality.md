# Decision Log: FR-018a Spec-Versus-Reality Conflict (sequence numbers do not exist)

**Date**: 2026-07-19
**Status**: RESOLVED — spec amended in WO-009 §1
**Related WO**: WO-009 §3 entry 1

## Statement

The Kraken v2 **public** book channel provides **no sequence numbers**. CRC32 checksum is
the sole integrity mechanism. FR-018a mandated sequence-number tracking and gap detection
— a mechanism the venue does not supply. Sequence-gap detection was "proven" against
fixtures modeling a nonexistent field.

## Confirmation

Verified against Kraken's own documentation before any code or spec was touched:

- <https://docs.kraken.com/api/docs/websocket-v2/book/>
- <https://docs.kraken.com/api/docs/guides/spot-ws-book-v2/>

Book messages carry `channel`, `type`, `symbol`, `bids`, `asks`, `checksum`, `timestamp`.
There is no sequence, update-id, or ordering field. Sequence numbers exist in Kraken v2
only on private/execution channels.

In our own code the field was populated from `int(raw_message[0])` — positional slot 0 of
a list-shaped message. Against real v2 (a dict envelope) that line is unreachable; against
v1 that slot is the **channelID**, constant for the life of a subscription, which would
have registered every message after the first as a gap.

## Checksum validation is BROADER than the mechanism it replaces

This is the point worth carrying forward, and it is why the amendment strengthens the
spec rather than merely correcting it:

| mechanism | detects |
|---|---|
| sequence gap | a **missing message** only |
| CRC32 mismatch | **any divergence** — missed messages, misapplied updates, and our own book-maintenance bugs |

A sequence counter cannot detect a message that arrives in order and is applied wrongly.
A checksum can. The amendment closes a fiction and widens real coverage simultaneously.

## What the amendment pins that was previously unstated

- **Ordering is now a stated guarantee, not an implementation detail.** Kraken's CRC32 is
  defined over the **post-update** book, so validation MUST occur after applying each
  update. The current implementation validates the **pre-update** book — a live defect
  recorded in `evidence/WO-008b-DIAG/checksum_pre_vs_post_update.txt`, and one that no
  self-generated fixture could ever catch.
- **Every-update validation.** Kraken permits periodic validation; permitted and honest
  are different standards. Written into the FR text so it cannot drift to "periodic" as a
  throughput optimization later.
- **A no-emission window.** From checksum failure until a fresh snapshot applies and
  validates, no MarketState may be emitted. An unverified book must not price anything
  (Principle V).
- **Subscription depth.** Legal values are 10/25/100/500/1000; this project pins **10**.
  `BOOK_DEPTH = 1` — illegal at the venue, and unable to hold the 10 levels the checksum
  requires — was possible only because no spec text made depth explicit.

## Known residual

`spec.md` is amended. Six sibling artifacts (`research.md`, `data-model.md`,
`contracts/data-adapter.yml`, `plan.md`, `quickstart.md`, `tasks.md`) still mandate
sequence tracking and were **out of WO-009's stated scope**. `research.md:23` still asserts
as fact that "v2 provides snapshot/incremental protocol with sequence numbers" — the
origin of the defect. Reported for a ruling; see `evidence/WO-009/speckit_analyze.txt`.

## Evidence

- `evidence/WO-009/speckit_analyze.txt`
- `evidence/WO-008b-DIAG/sequence_usage.txt`
- `specs/002-quote-level-data/spec.md` — Amendment History
