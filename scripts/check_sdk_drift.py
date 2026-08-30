#!/usr/bin/env python3
"""Report when the pinned `unitares-sdk` range has fallen behind what Core ships.

Resident depends on Core through one published artifact. The pin
(`unitares-sdk>=0.3.0,<0.4.0`) is what keeps that dependency honest, and it is
also how the dependency goes quietly stale: Core can publish 0.4.0 and Resident
keeps resolving 0.3.x forever, tracking a contract nobody is maintaining. Nothing
fails. That is the problem — cross-repo version skew does not announce itself.

This is a REPORTER, not a gate. It exits 0 whether or not drift is found, and the
workflow turns a finding into an issue. Failing CI on an upstream release would
redden every unrelated pull request over something no author can fix, which is a
reliable way to teach people to ignore the signal.

⚠️ Detects VERSION drift only. A release *inside* the pinned range can still
change behaviour, and this will not see it. Contract drift needs contract tests
against a live Core, which is a different piece of work.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

PACKAGE = "unitares-sdk"
PYPI_JSON = "https://pypi.org/pypi/{name}/json"

# Matches the dependency entry regardless of quoting/spacing, e.g.
#   "unitares-sdk>=0.3.0,<0.4.0"
#   'unitares_sdk >= 0.3.0, < 0.4.0'
DEP_RE = re.compile(
    r"""["']\s*unitares[-_]sdk\s*(?P<spec>[^"']*)["']""",
    re.IGNORECASE | re.VERBOSE,
)


class DriftError(RuntimeError):
    """Raised when the pin cannot be read.

    Never swallowed into a clean report: a check that cannot find its own
    subject must say so, not return "no drift".
    """


def read_pin(pyproject: str) -> SpecifierSet:
    match = DEP_RE.search(pyproject)
    if not match:
        raise DriftError(
            f"no {PACKAGE} dependency found in pyproject.toml — "
            "the pin moved or was renamed, and this check is now blind"
        )
    raw = match.group("spec").strip()
    if not raw:
        raise DriftError(
            f"{PACKAGE} is declared with no version specifier; an unpinned "
            "dependency cannot drift because it was never anchored"
        )
    try:
        return SpecifierSet(raw)
    except InvalidSpecifier as exc:
        raise DriftError(f"unreadable {PACKAGE} specifier {raw!r}: {exc}") from exc


def published_versions(name: str = PACKAGE) -> list[str]:
    with urllib.request.urlopen(PYPI_JSON.format(name=name), timeout=30) as response:
        payload = json.load(response)
    return sorted(payload["releases"])


def assess(versions: list[str], pin: SpecifierSet) -> dict:
    """Which published releases the pin excludes, and whether any is newer."""
    parsed = []
    for raw in versions:
        try:
            parsed.append(Version(raw))
        except InvalidVersion:
            continue  # a malformed upstream version is not this check's business
    if not parsed:
        raise DriftError(f"no parseable versions returned for {PACKAGE}")

    releases = sorted(v for v in parsed if not v.is_prerelease)
    latest = str(max(releases)) if releases else str(max(parsed))
    allowed = sorted(v for v in releases if pin.contains(v))
    highest_allowed = max(allowed) if allowed else None
    ahead = [str(v) for v in releases if highest_allowed is None or v > highest_allowed]

    return {
        "package": PACKAGE,
        "pin": str(pin),
        "latest_published": latest,
        "highest_allowed_by_pin": str(highest_allowed) if highest_allowed else None,
        "published_beyond_pin": ahead,
        "drift": bool(ahead),
        # An empty allowed set means the pin resolves to nothing at all — a
        # harder failure than drift, and one `uv sync` would surface anyway.
        "pin_matches_nothing": not allowed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyproject", default="pyproject.toml")
    parser.add_argument(
        "--versions",
        help="comma-separated version list instead of querying PyPI (testing)",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    try:
        pin = read_pin(Path(args.pyproject).read_text(encoding="utf-8"))
        versions = (
            [v.strip() for v in args.versions.split(",") if v.strip()]
            if args.versions
            else published_versions()
        )
        report = assess(versions, pin)
    except DriftError as exc:
        print(f"CHECK IS BLIND: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    if report["pin_matches_nothing"]:
        print(f"PIN MATCHES NOTHING: {report['pin']} selects no published release.")
    elif report["drift"]:
        print(
            f"SDK DRIFT: pin {report['pin']} tops out at "
            f"{report['highest_allowed_by_pin']}, but "
            f"{', '.join(report['published_beyond_pin'])} "
            f"{'is' if len(report['published_beyond_pin']) == 1 else 'are'} published."
        )
        print("Resident is tracking a contract that has moved on.")
    else:
        print(
            f"ok: pin {report['pin']} covers the latest published "
            f"{report['package']} {report['latest_published']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
