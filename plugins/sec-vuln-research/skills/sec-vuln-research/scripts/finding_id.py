# /// script
# requires-python = ">=3.11"
# ///
"""Stable, content-derived finding IDs for sec-vuln-research.

Derives an ID from a normalized hash of the code at the finding — the CWE,
the enclosing function symbol, and the whitespace/comment-normalized
snippet. The ID stays the same across scans while that code is unchanged,
survives line-number shifts and file renames, and lets tooling (ci_gate.py)
tell a known finding from a net-new one. It is NOT tied to a session.

Usage:
    uv run finding_id.py --repo <path> --file net/parser.c \\
        --start 42 --end 67 --cwe CWE-122 [--function parse_packet]

    # or when the snippet is already in hand:
    echo "$SNIPPET" | uv run finding_id.py --cwe CWE-122 --function parse_packet --stdin

Prints one line: the stable id, e.g.  SVR-3f9c2ab81e04d7f2

Hard-coded-credential findings (CWE-798, CWE-259, CWE-321) hash the
LOCATION (file + function) instead of the snippet, because the snippet IS
the secret and must not feed any derived artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

SECRET_CWES = {"CWE-798", "CWE-259", "CWE-321"}

COMMENT_PATTERNS = [
    re.compile(r"//.*$"), re.compile(r"#(?!include|define|if|endif|else|pragma).*$"),
    re.compile(r"/\*.*?\*/", re.S), re.compile(r"--.*$"),
]


def normalize(snippet: str) -> str:
    text = snippet
    for pat in COMMENT_PATTERNS[:1] + COMMENT_PATTERNS[2:3]:
        text = pat.sub("", text)
    lines = []
    for line in text.splitlines():
        collapsed = re.sub(r"\s+", " ", line).strip()
        if collapsed:
            lines.append(collapsed)
    return "\n".join(lines)


def derive(cwe: str, function: str, material: str) -> str:
    h = hashlib.sha256(f"{cwe}|{function}|{material}".encode("utf-8")).hexdigest()
    return f"SVR-{h[:16]}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, default=None)
    parser.add_argument("--file", default=None, help="File path relative to --repo")
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--cwe", required=True)
    parser.add_argument("--function", default="")
    parser.add_argument("--stdin", action="store_true",
                        help="Read the snippet from stdin instead of --repo/--file")
    args = parser.parse_args()

    if args.cwe in SECRET_CWES:
        # Never hash the secret itself — location-derived ID instead.
        if not args.file:
            sys.exit("Error: secret-class CWEs need --file (location-derived ID).")
        material = f"location:{args.file}:{args.function}"
        print(derive(args.cwe, args.function, material))
        return

    if args.stdin:
        snippet = sys.stdin.read()
    else:
        if not (args.repo and args.file and args.start and args.end):
            sys.exit("Error: need --repo, --file, --start, --end (or --stdin).")
        target = (args.repo / args.file).resolve()
        try:
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as e:
            sys.exit(f"Error: cannot read {target}: {e}")
        if args.start < 1 or args.start > len(lines):
            sys.exit(f"Error: --start {args.start} out of range (file has {len(lines)} lines).")
        snippet = "\n".join(lines[args.start - 1:args.end])

    normalized = normalize(snippet)
    if not normalized:
        sys.exit("Error: snippet is empty after normalization.")
    print(derive(args.cwe, args.function, normalized))


if __name__ == "__main__":
    main()
