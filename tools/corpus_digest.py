"""Reproducible digest of a capture corpus. Declares its own scheme (WO-051).

    python tools/corpus_digest.py [path]        # default: the ratified corpus

WHY THIS EXISTS (WO-051 §1 STOP)
--------------------------------
Five work-order reports (WO-045 through WO-050) certify the ratified corpus as digest
`a025db1e…`, and WO-051 §1 asks for that value to be snapshotted again. It cannot be: the code
that produced it was never committed — it lived in throwaway scripts — so the SCHEME is gone and
the number cannot be recomputed from the corpus bytes. Twenty candidate schemes were tried
against the real 88 files; none reproduces it (recorded in WO-051-REPORT.md).

That is the same defect this WO exists to fix, one level up. A fee with no citable source and a
digest with no reproducible definition fail in the identical way: a figure everyone repeats and
nobody can check. `a025db1e…` was never a verifiable claim about the corpus — it was a claim
about a script that no longer exists.

So this module DECLARES its scheme in code, and every future report cites a number any reader
can regenerate. The corpus itself is untouched: this only ever reads.

THE SCHEME (v1) — normative, do not change without renaming
-----------------------------------------------------------
    h = sha256()
    for each regular file, sorted by POSIX relative path (NFC, forward slashes):
        h.update(relative_path_utf8 + b"\\0")
        h.update(sha256(file_bytes).digest())
    digest = h.hexdigest()

Directories contribute nothing (an empty one carries no data). The path is included so that
renaming a file changes the digest. The NUL separator makes the concatenation unambiguous, so
"ab" + "c" cannot collide with "a" + "bc". POSIX separators make it identical on Windows and
Linux, which the historical Windows-backslash variants were not.
"""

import hashlib
import sys
from pathlib import Path

DEFAULT_CORPUS = Path("captures/corpus_24h/corpus_20260805")
SCHEME = "v1:sha256(relpath_posix_utf8 + NUL + sha256(bytes)), sorted by relpath"


def corpus_digest(root: Path) -> tuple[str, int]:
    """Return (hexdigest, file_count) under the declared v1 scheme. Read-only."""
    files = sorted(
        (p for p in root.rglob("*") if p.is_file()),
        key=lambda p: p.relative_to(root).as_posix(),
    )
    h = hashlib.sha256()
    for p in files:
        h.update(p.relative_to(root).as_posix().encode("utf-8"))
        h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest(), len(files)


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CORPUS
    if not root.is_dir():
        print(f"FAIL: not a directory: {root}")
        return 1
    digest, count = corpus_digest(root)
    print(f"corpus : {root.as_posix()}")
    print(f"scheme : {SCHEME}")
    print(f"files  : {count}")
    print(f"digest : {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
