from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_contract_drift import DriftError, assess, read_pinned_ref  # noqa: E402


def test_reads_the_real_pin_from_this_repo():
    """Not a fixture: if the job is renamed, this check goes blind."""
    root = Path(__file__).resolve().parents[1]
    ref = read_pinned_ref((root / ".github/workflows/ci.yml").read_text())
    assert len(ref) == 40
    assert all(c in "0123456789abcdef" for c in ref)


@pytest.mark.parametrize(
    "ci_yml",
    [
        "jobs:\n  test:\n    steps: []\n",
        "jobs:\n  core-contract:\n    steps:\n      - ref: not-a-sha\n",
    ],
)
def test_missing_pin_raises_instead_of_reporting_clean(ci_yml: str):
    """A missing subject must never render as 'no drift'."""
    with pytest.raises(DriftError):
        read_pinned_ref(ci_yml)


def test_ambiguous_multiple_refs_raises():
    ci_yml = (
        "jobs:\n"
        "  a:\n    steps:\n      - ref: " + "a" * 40 + "\n"
        "  b:\n    steps:\n      - ref: " + "b" * 40 + "\n"
    )
    with pytest.raises(DriftError):
        read_pinned_ref(ci_yml)


def test_no_drift_when_hashes_match():
    report = assess("a" * 40, "a" * 40, "same-hash", "same-hash")
    assert report["drift"] is False
    assert report["ref_behind"] is False


def test_drift_when_surface_hash_diverges():
    """The failure this exists for: the pinned ref stopped matching Core's contract."""
    report = assess("a" * 40, "b" * 40, "old-hash", "new-hash")
    assert report["drift"] is True
    assert report["ref_behind"] is True


def test_ref_behind_without_content_drift_is_not_drift():
    """Advancing the pin is still due, but the gate isn't lying yet."""
    report = assess("a" * 40, "b" * 40, "same-hash", "same-hash")
    assert report["drift"] is False
    assert report["ref_behind"] is True


def test_missing_contract_file_is_blind_not_clean():
    with pytest.raises(DriftError):
        assess("a" * 40, "b" * 40, None, "new-hash")
    with pytest.raises(DriftError):
        assess("a" * 40, "b" * 40, "old-hash", None)
