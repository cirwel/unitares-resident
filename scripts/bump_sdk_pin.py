#!/usr/bin/env python3
"""Bump the unitares-sdk pin in pyproject.toml to track a newly published version.

Companion to check_sdk_drift.py: once drift is confirmed, this computes the
next pin window and rewrites pyproject.toml in place. Pre-1.0 (0.x) releases
treat a minor bump as the breaking boundary, matching how this pin has always
been set (0.2.2 -> <0.3.0, then 0.3.0 -> <0.4.0) — so the new ceiling is the
next minor after the latest published release.

Only rewrites the file; it does not run `uv lock` or touch git. The workflow
does those steps and falls back to filing an issue if either fails, so a
version bump this script cannot express safely is never silently lost.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from packaging.version import Version

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_sdk_drift import DEP_RE, PACKAGE, DriftError, read_pin  # noqa: E402


def next_pin(latest: str) -> str:
    version = Version(latest)
    ceiling = f"{version.major}.{version.minor + 1}.0"
    return f">={latest},<{ceiling}"


def bump(pyproject_text: str, latest: str) -> tuple[str, str, str]:
    """Returns (new_text, old_pin, new_pin).

    Raises DriftError if the existing pin cannot be read — reuses read_pin's
    validation so this refuses to touch a file it does not understand rather
    than guessing at a replacement.
    """
    read_pin(pyproject_text)  # raises DriftError on a missing/unparseable pin

    match = DEP_RE.search(pyproject_text)
    if match is None:
        raise DriftError(f"no {PACKAGE} dependency found in pyproject.toml")

    # Read the raw matched text rather than str(SpecifierSet(...)) — a
    # SpecifierSet is backed by a set, so its __str__ does not preserve
    # input order (">=0.3.0,<0.4.0" can come back as "<0.4.0,>=0.3.0"),
    # which would make every bump look like a change even when it is not.
    start, end = match.span("spec")
    old_pin = pyproject_text[start:end]
    new_pin = next_pin(latest)
    new_text = pyproject_text[:start] + new_pin + pyproject_text[end:]
    return new_text, old_pin, new_pin


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyproject", default="pyproject.toml")
    parser.add_argument(
        "--latest", required=True, help="latest published version to pin to"
    )
    args = parser.parse_args(argv)

    path = Path(args.pyproject)
    try:
        new_text, old_pin, new_pin = bump(
            path.read_text(encoding="utf-8"), args.latest
        )
    except DriftError as exc:
        print(f"CANNOT BUMP: {exc}", file=sys.stderr)
        return 2

    if old_pin == new_pin:
        print(f"no change: pin is already {new_pin}")
        return 0

    path.write_text(new_text, encoding="utf-8")
    print(f"bumped {PACKAGE} pin: {old_pin} -> {new_pin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
