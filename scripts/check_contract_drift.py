#!/usr/bin/env python3
"""Report when the pinned Core contract-provider commit has fallen behind Core.

Resident's `core-contract` CI job (.github/workflows/ci.yml) checks out a
pinned commit of cirwel/unitares and validates
`docs/interface-contract.v1.json` against it. That pin is exactly as
forgettable as the SDK pin `check_sdk_drift.py` already guards — Core can
change the contract on its default branch and the gate keeps comparing
against a snapshot nobody maintains, staying green while doing so.

This was not hypothetical: the pin shipped pointing at the tip of a
since-merged PR's source branch rather than the merge commit, and the merged
contract's `surface_sha256` differed from what the gate was actually
checking.

This is a REPORTER, not a gate — same reasoning as check_sdk_drift.py:
failing CI on an upstream contract change would redden every unrelated PR
over something no author here can fix, which teaches people to ignore the
signal.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "cirwel/unitares"
BRANCH = "master"
CONTRACT_PATH = "docs/interface-contract.v1.json"
RAW_URL = "https://raw.githubusercontent.com/{repo}/{ref}/{path}"
COMMIT_API = "https://api.github.com/repos/{repo}/commits/{ref}"

REF_RE = re.compile(r"^\s*ref:\s*([0-9a-f]{40})\s*$", re.MULTILINE)


class DriftError(RuntimeError):
    """Raised when the pin or its subject cannot be read.

    Never swallowed into a clean report: a check that cannot find its own
    subject must say so, not return "no drift".
    """


def read_pinned_ref(ci_yml: str) -> str:
    matches = REF_RE.findall(ci_yml)
    if not matches:
        raise DriftError(
            "no pinned Core contract ref found in ci.yml — the job moved or "
            "was renamed, and this check is now blind"
        )
    if len(matches) > 1:
        raise DriftError(
            f"found {len(matches)} candidate refs in ci.yml — ambiguous, and "
            "this check does not know which one guards the contract"
        )
    return matches[0]


def fetch_text(url: str) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def resolve_branch_head(repo: str = REPO, branch: str = BRANCH) -> str:
    with urllib.request.urlopen(
        COMMIT_API.format(repo=repo, ref=branch), timeout=30
    ) as response:
        return json.load(response)["sha"]


def fetch_surface_hash(repo: str, ref: str) -> str | None:
    raw = fetch_text(RAW_URL.format(repo=repo, ref=ref, path=CONTRACT_PATH))
    if raw is None:
        return None
    try:
        return json.loads(raw).get("surface_sha256")
    except json.JSONDecodeError as exc:
        raise DriftError(
            f"{repo}@{ref}'s {CONTRACT_PATH} is not valid JSON: {exc}"
        ) from exc


def assess(
    pinned_ref: str,
    head_ref: str,
    pinned_hash: str | None,
    head_hash: str | None,
) -> dict:
    """Whether the pinned contract snapshot still matches Core's current one."""
    if pinned_hash is None:
        raise DriftError(f"pinned ref {pinned_ref} has no {CONTRACT_PATH}")
    if head_hash is None:
        raise DriftError(f"{BRANCH}@{head_ref} has no {CONTRACT_PATH}")

    return {
        "repo": REPO,
        "branch": BRANCH,
        "pinned_ref": pinned_ref,
        "head_ref": head_ref,
        "pinned_surface_sha256": pinned_hash,
        "head_surface_sha256": head_hash,
        # A pin can fall behind in commit terms without the contract itself
        # having changed — worth flagging separately from actual drift.
        "ref_behind": pinned_ref != head_ref,
        "drift": pinned_hash != head_hash,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ci-yml", default=".github/workflows/ci.yml")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    try:
        pinned_ref = read_pinned_ref(Path(args.ci_yml).read_text(encoding="utf-8"))
        head_ref = resolve_branch_head()
        pinned_hash = fetch_surface_hash(REPO, pinned_ref)
        head_hash = fetch_surface_hash(REPO, head_ref)
        report = assess(pinned_ref, head_ref, pinned_hash, head_hash)
    except DriftError as exc:
        print(f"CHECK IS BLIND: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    if report["drift"]:
        print(
            f"CONTRACT DRIFT: pinned ref {report['pinned_ref']} has "
            f"surface_sha256 {report['pinned_surface_sha256']}, but "
            f"{report['branch']}@{report['head_ref']} has "
            f"{report['head_surface_sha256']}."
        )
        print("The core-contract gate is validating a stale artifact.")
    elif report["ref_behind"]:
        print(
            f"ok (content unchanged): pinned ref {report['pinned_ref']} is "
            f"behind {report['branch']}@{report['head_ref']}, but the "
            "contract surface is identical."
        )
    else:
        print(f"ok: pinned ref matches {report['branch']} HEAD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
