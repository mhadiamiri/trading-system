# WO-042 — CORPUS ROTATION / RETENTION POLICY

**Date:** 2026-07-28
**Base Commit:** 48c9830 (WO-041 NO-GO)
**Purpose:** Close TERM 5 gap — specify rotation and retention for 24h corpus capture (~5.3 GB/day raw)

---

## §1.1 ROTATION CADENCE

**Choice:** Time-based — **HOURLY** rotation

**Justification:**
- Ops's expectation per WO-042 instructions
- Aligns with gap ledger's 1-hour windows for integrated analysis
- Makes partial-run recovery straightforward (whole-hour segments)
- Simpler to reason about than size-based for a fixed 24h run

**Segment Size Estimate:**
- 5.3 GB/day ÷ 24 = ~220 MB/hour (raw JSON)
- With 5-10× compression: ~22-44 MB/hour compressed

**Naming Scheme:**
```
corpus_{HOST}_{YYYYMMDD}T{HH}Z.jsonl          (raw, uncompressed)
corpus_{HOST}_{YYYYMMDD}T{HH}Z.jsonl.gz       (compressed, if enabled)
```

**Example:**
```
corpus_HADI_20260728T00Z.jsonl
corpus_HADI_20260728T01Z.jsonl
...
corpus_HADI_20260728T23Z.jsonl
```

- **Sortable:** Lexicographic sort = chronological order (ISO 8601 UTC)
- **UTC-stamped:** Avoids timezone ambiguity, aligns with baseline's UTC measurement
- **Host-prefixed:** Multiple hosts can archive without collision
- **Extension:** `.jsonl` for newline-delimited JSON (one frame per line)

**File Layout:**
```
captures/
└── corpus_24h/
    └── {RUN_ID}/
        ├── corpus_{HOST}_{YYYYMMDD}T{HH}Z.jsonl
        ├── corpus_{HOST}_{YYYYMMDD}T{HH}Z.jsonl.gz  (if compression enabled)
        └── gap_ledger.json                          (per-run, not per-hour)
```

---

## §1.2 CRASH-SAFETY

**Segment Flush/Close Behavior:**
- Each hour segment is **flushed and closed** at the top of the next hour
- A crash during the run loses **at most the open hour segment** (~220 MB raw)
- Closed segments are immutable — re-open does not append

**Gap Ledger Interaction:**
- Gap ledger persists **separately** as `gap_ledger.json` (per-run, not per-hour)
- Ledger uses write-through persistence (proven in TERM 4, WO-041)
- **Crash recovery:** On restart, gap ledger is read from disk; capture continues into a new hour segment
- **Per-segment readability:** Each hour segment contains complete frame records for that hour — no cross-segment references required for analysis

**Crash Scenario:**
```
T+02:30 — crash
Lost: frames from T+02:00 to T+02:30 (in open hour segment)
Safe: frames from T+00:00 to T+02:00 (in closed segments)
Recovery: restart → new segment corpus_HADI_...T03Z.jsonl (or continue T+02 if within same hour)
```

**Write-Through Persistence (from TERM 4):**
- Gap ledger flushes each gap record immediately to disk
- Frame writes flush per-line or per-batch (configurable, default per-line for safety)
- The capture WO inherits this proven machinery — no new code required

---

## §1.3 COMPRESSION + RETENTION

**Compression Strategy:**
- **Format:** gzip (`*.jsonl.gz`)
- **Timing:** Compress on segment close (after the hour completes)
- **Expected Ratio:** 5-10× for JSON frame data
  - Raw: ~220 MB/hour
  - Compressed: ~22-44 MB/hour
  - Daily compressed: ~0.6-1 GB (vs 5.3 GB raw)

**Retention Period:**
- **Minimum:** 90 days
- **Recommended:** 1 year
- **Rationale:** The corpus is an archive for regression analysis and forensic investigation. Headroom is 874 GB, so multi-year retention is disk-feasible. The 90-day minimum ensures coverage of any downstream investigation cycle.

**Archive Cleanup:**
- No automatic cleanup — retention is a declared policy, not accidental
- Manual cleanup only after explicit decision (e.g., archive cold-storage migration)

---

## §1.4 INTEGRITY (PER-SEGMENT CHECKSUMMING)

**Requirement:** Each segment independently checksummed/validatable so archive corruption is detectable.

**Mechanism:**
- **File-level:** SHA-256 checksum computed on segment close, stored in manifest
- **Segment-level:** Per-frame CRC32 checksums (proven in TERM 3, WO-041) already validate individual records
- **Manifest file:** `MANIFEST.json` alongside each run

**Manifest Structure:**
```json
{
  "run_id": "{RUN_ID}",
  "host": "HADI",
  "start_utc": "2026-07-28T00:00:00Z",
  "end_utc": "2026-07-29T00:00:00Z",
  "segments": [
    {
      "filename": "corpus_HADI_20260728T00Z.jsonl",
      "sha256": "abc123...",
      "frame_count": 111000,
      "size_bytes": 220000000,
      "compressed": false
    },
    {
      "filename": "corpus_HADI_20260728T00Z.jsonl.gz",
      "sha256": "def456...",
      "size_bytes": 25000000,
      "compressed": true
    }
  ],
  "gap_ledger": "gap_ledger.json",
  "gap_ledger_sha256": "789xyz..."
}
```

**Corruption Detection:**
- **On archive read:** Recompute SHA-256 for each segment, compare to manifest
- **Silent corruption detection:** Per-frame CRC32 validates data integrity; a mismatched frame is a corrupted segment
- **Recovery strategy:** If manifest mismatch — segment is corrupt; if CRC32 mismatch — frame is corrupt; whole segment is marked as corrupt in manifest metadata

---

## §1.5 CONFIG VALUES — WHERE CAPTURE WO READS

**Rotation Policy Constants:**

The capture WO will read rotation/retention configuration from **environment variables** (not hard-coded constants):

| Variable | Value | Purpose |
|----------|-------|---------|
| `CORPUS_ROTATION_CADENCE` | `hourly` | Rotation cadence (future: could be `size`-based) |
| `CORPUS_SEGMENT_DURATION_SECONDS` | `3600` | Seconds per segment (1 hour) |
| `CORPUS_COMPRESSION_ENABLED` | `true` | Enable gzip on segment close |
| `CORPUS_RETENTION_DAYS` | `90` | Minimum retention period (operational policy) |
| `CORPUS_DIR` | `captures/corpus_24h` | Root directory for corpus captures |

**Why Environment Variables:**
- Ops-configurable without code changes
- Different environments (dev/prod) can use different settings
- Captures are run as commands — env vars are natural CLI parameters

**No src/ Changes Required:**
- The capture WO will consume these env vars at capture-time
- This policy document specifies the DEFAULTS for the 24h corpus run
- If defaults change, update this document — capture WO reads from env, not from code

**Capture WO Interface (contract):**
```
# Example corpus capture invocation
CORPUS_ROTATION_CADENCE=hourly \
CORPUS_SEGMENT_DURATION_SECONDS=3600 \
CORPUS_COMPRESSION_ENABLED=true \
CORPUS_RETENTION_DAYS=90 \
CORPUS_DIR=captures/corpus_24h \
python -m trading.capture.live_corpus_capture
```

---

## SUMMARY

| Aspect | Specification |
|--------|---------------|
| Rotation cadence | Hourly (time-based), ~220 MB/segment raw |
| Naming scheme | `corpus_{HOST}_{YYYYMMDD}T{HH}Z.jsonl` (UTC, sortable) |
| Crash safety | Segment closed hourly; max loss = open hour segment (~220 MB) |
| Gap ledger | Separate per-run file; write-through persistence proven |
| Compression | gzip on close; 5-10× ratio; ~22-44 MB/hour compressed |
| Retention | 90-day minimum, 1-year recommended |
| Integrity | SHA-256 per segment + CRC32 per-frame; MANIFEST.json |
| Config source | Environment variables (no src changes required) |

**Disk Budget (24h run):**
- Raw: 5.3 GB
- Compressed: 0.6-1 GB
- With 90-day retention: 54-90 GB
- Host headroom: 874 GB free → sufficient for multi-year archives
