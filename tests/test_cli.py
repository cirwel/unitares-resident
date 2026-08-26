from __future__ import annotations

import json

from unitares_resident import cli


def test_offline_doctor_reports_config_only_boundary(capsys):
    assert cli.main(["doctor", "--offline"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "config_only"
    assert payload["governance_boundary"] == "unitares-sdk"
    assert payload["server_internals"] is False
    assert payload["database_access"] is False
    assert payload["checks"]["core_connection"]["status"] == "skipped"


def test_live_doctor_exit_code_tracks_probe(monkeypatch, capsys):
    async def failing_probe(config):
        return {"status": "error", "config": config.public_summary()}

    monkeypatch.setattr(cli, "run_live_doctor", failing_probe)
    assert cli.main(["doctor"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "error"


def test_doctor_reports_invalid_configuration(monkeypatch, capsys):
    monkeypatch.setenv("UNITARES_MCP_URL", "not-a-url")
    assert cli.main(["doctor", "--offline"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["checks"]["configuration"]["status"] == "error"
