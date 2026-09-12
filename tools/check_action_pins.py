"""Verify digest-pinned GitHub Actions match their `# vX.Y.Z` annotations.

Runs in CI (lint job). Every `uses: owner/repo@<40-hex sha>` line in
`.github/workflows/` must carry a comment naming a tag that resolves to
exactly that commit, resolved live via `git ls-remote` — so a Renovate bump
that leaves a stale comment behind fails here instead of misinforming review.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

USES_RE = re.compile(
    r"^\s*-?\s*uses:\s*(?P<action>[\w.-]+/[\w.-]+(?:/[\w.-]+)*)@(?P<sha>[0-9a-f]{40})(?:\s+#\s*(?P<comment>\S+))?\s*$"
)


def resolved_tag_map(action: str) -> dict[str, set[str]]:
    """Map commit sha -> set of tag names for a GitHub action repository.

    ``action`` may include a subpath (``owner/repo/sub``); the git remote is
    always the first two path components.
    """
    repo = "/".join(action.split("/")[:2])
    output = subprocess.run(
        ["git", "ls-remote", f"https://github.com/{repo}", "refs/tags/*"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    raw: dict[str, str] = {}
    for line in output.splitlines():
        sha, ref = line.split(maxsplit=1)
        raw[ref.strip()] = sha
    commits_to_tags: dict[str, set[str]] = {}
    for ref, sha in raw.items():
        if not ref.startswith("refs/tags/"):
            continue
        if ref.endswith("^{}"):  # peeled commit of an annotated tag
            tag = ref[len("refs/tags/") : -len("^{}")]
        else:
            tag = ref[len("refs/tags/") :]
            if f"refs/tags/{tag}^{{}}" in raw:
                continue  # the peeled entry carries the commit sha
        commits_to_tags.setdefault(sha, set()).add(tag)
    return commits_to_tags


def main() -> int:
    workflow_dir = Path(".github/workflows")
    pins: list[tuple[Path, str, str, str | None]] = []
    for workflow in sorted({*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")}):
        for line_number, line in enumerate(workflow.read_text(encoding="utf-8").splitlines(), start=1):
            match = USES_RE.match(line)
            if match:
                pins.append((workflow, line_number, match.group("action"), match.group("comment"), match.group("sha")))  # type: ignore[arg-type]

    cache: dict[str, dict[str, set[str]]] = {}
    failures: list[str] = []
    for workflow, line_number, action, comment, sha in pins:  # type: ignore[misc]
        if action not in cache:
            cache[action] = resolved_tag_map(action)
        tags = cache[action].get(sha)
        if tags is None:
            failures.append(f"{workflow}:{line_number}: {action}@{sha[:12]} does not match any tag")
            continue
        if comment is None:
            failures.append(f"{workflow}:{line_number}: {action}@{sha[:12]} has no version annotation (tags: {sorted(tags)})")
        elif comment not in tags:
            failures.append(
                f"{workflow}:{line_number}: {action}@{sha[:12]} is annotated {comment} but resolves to {sorted(tags)}"
            )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(f"ok: {len(pins)} action pins match their annotations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
