"""Verify the changelog documents the version being released.

Run by the release workflow before anything is published, and by a maintainer
while preparing a release:

    python tools/release_check.py 0.7.0            # check
    python tools/release_check.py 0.7.0 --print    # emit the section body

A release whose changelog entry is still sitting under "Unreleased" ships with
no record of what changed, and the GitHub Release body is built from the same
section, so the two cannot drift.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CHANGELOG = REPO_ROOT / "CHANGELOG.md"

# Keep a Changelog allows "## [1.2.3] - 2026-01-01"; this project has also used
# a bare "## 1.2.3". Accept either, with or without a trailing date, and let
# "## Unreleased" match as a heading so it still delimits the section above it.
HEADING_RE = re.compile(r"^##\s+\[?(?P<version>[^\]\s]+)\]?\s*(.*)$")


def section_for(version: str, changelog: Path | None = None) -> str | None:
    """Return the changelog body for a version, or None if it has no section.

    An existing but empty section returns the empty string, which callers must
    treat as a failure -- see `main`. "Unreleased" is deliberately not matched
    as a version: tagging before moving those entries into a dated section is
    the mistake this check exists to catch.
    """
    path = DEFAULT_CHANGELOG if changelog is None else changelog
    lines = path.read_text(encoding="utf-8").splitlines()

    start: int | None = None
    for index, line in enumerate(lines):
        heading = HEADING_RE.match(line)
        if heading is None:
            continue
        if start is not None:
            return "\n".join(lines[start:index]).strip("\n")
        if heading.group("version") == version:
            start = index + 1
    if start is None:
        return None
    return "\n".join(lines[start:]).strip("\n")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="the version being released, e.g. 0.7.0")
    parser.add_argument("--changelog", type=Path, default=None, help="changelog path (defaults to the repo's)")
    parser.add_argument("--print", dest="emit", action="store_true", help="write the section body to stdout")
    args = parser.parse_args(argv)

    body = section_for(args.version, args.changelog)
    if body is None:
        print(
            f"FAIL: CHANGELOG.md has no section for {args.version}. "
            f"Move the Unreleased entries into a '## {args.version} - <date>' section before tagging."
        )
        return 1
    if not body.strip():
        # An empty section passes a "does it exist" test but produces a release
        # with a blank body, which is the outcome this check exists to prevent.
        print(
            f"FAIL: the CHANGELOG.md section for {args.version} is empty. "
            f"A release cannot be published with no record of what changed."
        )
        return 1
    if args.emit:
        print(body)
    else:
        print(f"ok: CHANGELOG.md documents {args.version}")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
