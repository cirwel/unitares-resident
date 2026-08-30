from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from bump_sdk_pin import bump, next_pin  # noqa: E402
from check_sdk_drift import DriftError  # noqa: E402

PYPROJECT = '[project]\ndependencies = ["unitares-sdk>=0.3.0,<0.4.0"]\n'


def test_next_pin_treats_minor_as_the_breaking_boundary():
    assert next_pin("0.4.0") == ">=0.4.0,<0.5.0"
    assert next_pin("0.4.7") == ">=0.4.7,<0.5.0"


def test_bump_rewrites_only_the_spec_leaving_the_rest_untouched():
    new_text, old_pin, new_pin = bump(PYPROJECT, "0.4.0")
    assert old_pin == ">=0.3.0,<0.4.0"
    assert new_pin == ">=0.4.0,<0.5.0"
    assert new_text == '[project]\ndependencies = ["unitares-sdk>=0.4.0,<0.5.0"]\n'


def test_bump_to_the_pins_own_lower_bound_is_a_no_op():
    _, old_pin, new_pin = bump(PYPROJECT, "0.3.0")
    assert old_pin == new_pin == ">=0.3.0,<0.4.0"


def test_unreadable_pin_refuses_to_guess():
    with pytest.raises(DriftError):
        bump('[project]\ndependencies = ["httpx>=0.27"]\n', "0.4.0")
