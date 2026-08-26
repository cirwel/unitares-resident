from __future__ import annotations

import sys
from pathlib import Path

import pytest
from packaging.specifiers import SpecifierSet

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_sdk_drift import DriftError, assess, read_pin  # noqa: E402

PIN = SpecifierSet(">=0.2.2,<0.3.0")


def test_reads_the_real_pin_from_this_repo():
    """Not a fixture: if the dependency is renamed, this check goes blind."""
    root = Path(__file__).resolve().parents[1]
    pin = read_pin((root / "pyproject.toml").read_text())
    assert pin.contains("0.2.2")


@pytest.mark.parametrize(
    "pyproject",
    [
        '[project]\ndependencies = ["httpx>=0.27"]\n',
        '[project]\ndependencies = ["unitares-sdk"]\n',
        '[project]\ndependencies = ["unitares-sdk>=not-a-version"]\n',
    ],
)
def test_unreadable_pin_raises_instead_of_reporting_clean(pyproject: str):
    """A missing subject must never render as 'no drift'.

    Absent dependency, absent specifier and unparseable specifier all produce
    zero findings if handled quietly, which is indistinguishable from health.
    """
    with pytest.raises(DriftError):
        read_pin(pyproject)


def test_no_drift_when_pin_covers_the_latest_release():
    report = assess(["0.1.0", "0.2.0", "0.2.2"], PIN)
    assert report["drift"] is False
    assert report["highest_allowed_by_pin"] == "0.2.2"
    assert report["published_beyond_pin"] == []


def test_drift_when_core_publishes_past_the_upper_bound():
    """The failure this exists for: nothing breaks, the pin just stops tracking."""
    report = assess(["0.2.2", "0.3.0", "0.3.1"], PIN)
    assert report["drift"] is True
    assert report["published_beyond_pin"] == ["0.3.0", "0.3.1"]
    assert report["latest_published"] == "0.3.1"


def test_prereleases_do_not_count_as_drift():
    """A 0.3.0a1 is not a contract Resident should be chasing."""
    report = assess(["0.2.2", "0.3.0a1", "0.3.0rc2"], PIN)
    assert report["drift"] is False


def test_pin_matching_nothing_is_reported_separately():
    """Distinct from drift, and worse: the pin resolves to no release at all."""
    report = assess(["0.1.0", "0.4.0"], PIN)
    assert report["pin_matches_nothing"] is True


def test_malformed_upstream_versions_are_skipped_not_fatal():
    report = assess(["0.2.2", "not-a-version", "0.3.0"], PIN)
    assert report["drift"] is True
    assert "not-a-version" not in report["published_beyond_pin"]


def test_no_parseable_versions_is_blind_not_clean():
    with pytest.raises(DriftError):
        assess(["nonsense", "also-nonsense"], PIN)
