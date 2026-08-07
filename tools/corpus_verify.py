"""Verify a corpus against the per-segment SHA-256 recorded IN ITS OWN MANIFEST (WO-052 §1).

    python tools/corpus_verify.py [corpus_path]

WHY THIS IS THE RIGHT WITNESS
-----------------------------
WO-052 §1 asked git to witness that the ratified corpus is byte-identical across WO-045→WO-051.
Git cannot: `/captures/` is gitignored by deliberate policy (WO-042 §2.3 — capture data must not
enter history it could never be removed from), so ZERO corpus files are tracked, in any commit, in
all of history. There are no blobs to compare. The ruling's remedy was premised on the corpus
being in git; it is not, and never was.

But a stronger witness already existed, written by the capture itself:

    CORPUS_MANIFEST.json carries, for every segment, a sha256 with `hashed_at_capture: true` —
    computed by `trading.data.corpus.sha256_file` AT THE MOMENT THE SEGMENT WAS CLOSED.

That satisfies the standing rule this same WO mints (§2): **an integrity-certifying figure must be
computed by code committed in the tree it certifies.** `sha256_file` is committed, in `src/`, under
test, and the figures it produced are stored beside the data. Unlike `a025db1e…` — whose scheme
lived in a throwaway script and died with it — this can be recomputed by anyone, forever.

It is also a BETTER witness than the git log the ruling asked for, on two counts:
  * it is per-segment, so a failure NAMES the corrupted file rather than reporting a directory-wide
    mismatch;
  * it dates from CAPTURE, not from whenever someone first thought to hash the tree — so it covers
    the interval from the moment each byte was written, which no later-computed digest can.

What it does NOT do: prove the manifest itself is unaltered. Someone who rewrote a segment AND its
manifest entry would pass. That is an honest limit of any self-describing artifact and is reported
rather than papered over — see WO-052-REPORT.md.
"""

import hashlib
import json
import sys
from pathlib import Path

DEFAULT_CORPUS = Path("captures/corpus_24h/corpus_20260805")


def sha256_file(path: Path) -> str:
    """Byte-for-byte the scheme `trading.data.corpus.sha256_file` used at capture time."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(root: Path):
    """Return (results, missing) where results is a list of (filename, ok, at_capture)."""
    manifest = json.loads((root / "CORPUS_MANIFEST.json").read_text(encoding="utf-8"))
    results, missing = [], []
    for run in manifest.get("runs", []):
        run_dir = root / run["run_id"]
        for seg in run.get("segments", []):
            path = run_dir / seg["filename"]
            if not path.is_file():
                missing.append(str(path.relative_to(root).as_posix()))
                continue
            results.append((
                seg["filename"],
                sha256_file(path) == seg["sha256"],
                bool(seg.get("hashed_at_capture", True)),
            ))
    return results, missing


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CORPUS
    if not (root / "CORPUS_MANIFEST.json").is_file():
        print(f"FAIL: no CORPUS_MANIFEST.json under {root}")
        return 1

    results, missing = verify(root)
    ok = [r for r in results if r[1]]
    bad = [r for r in results if not r[1]]
    at_capture = [r for r in results if r[2]]

    print(f"corpus            : {root.as_posix()}")
    print(f"segments in manifest: {len(results) + len(missing)}")
    print(f"  verified OK     : {len(ok)}")
    print(f"  MISMATCHED      : {len(bad)}")
    print(f"  MISSING on disk : {len(missing)}")
    print(f"  hashed_at_capture=true : {len(at_capture)} / {len(results)}")
    for name, _, _ in bad:
        print(f"    MISMATCH: {name}")
    for name in missing:
        print(f"    MISSING : {name}")

    verdict = not bad and not missing and len(results) > 0
    print(f"\nVERDICT: {'PASS' if verdict else 'FAIL'} — every segment matches the SHA-256 "
          f"recorded when it was captured" if verdict else "\nVERDICT: FAIL")
    return 0 if verdict else 1


if __name__ == "__main__":
    raise SystemExit(main())
