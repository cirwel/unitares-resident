from __future__ import annotations

import json

from unitares_resident.cli import main


def test_doctor_reports_non_privileged_boundary(capsys):
    assert main(["doctor"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["governance_boundary"] == "unitares-sdk"
    assert payload["server_internals"] is False
    assert payload["database_access"] is False
