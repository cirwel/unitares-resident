"""Command-line entry point for the Resident skeleton."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from typing import Any

from unitares_sdk import GovernanceClient

from unitares_resident.config import ResidentConfig
from unitares_resident.contract import (
    ContractCompatibilityError,
    validate_discovery,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="unitares-resident")
    subcommands = parser.add_subparsers(dest="command", required=True)
    doctor = subcommands.add_parser(
        "doctor",
        help="validate configuration, Core reachability, and federation contract",
    )
    doctor.add_argument(
        "--offline",
        action="store_true",
        help="validate configuration only; report live checks as skipped",
    )
    return parser


def _base_report(config: ResidentConfig) -> dict[str, Any]:
    return {
        "config": config.public_summary(),
        "governance_boundary": "unitares-sdk",
        "server_internals": False,
        "database_access": False,
    }


async def run_live_doctor(
    config: ResidentConfig,
    *,
    client_factory: Any = GovernanceClient,
) -> dict[str, Any]:
    """Probe Core through the same public SDK/MCP path Resident will use."""

    report = _base_report(config)
    checks: dict[str, Any] = {
        "configuration": {"status": "ok"},
    }
    timeout = min(config.cycle_timeout_seconds, 30.0)
    try:
        client = client_factory(
            mcp_url=config.mcp_url,
            timeout=timeout,
            connect_timeout=min(timeout, 10.0),
        )
        async with client:
            discovery = await client.call_tool("list_tools", {"lite": True})
        checks["core_connection"] = {
            "status": "ok",
            "endpoint": config.mcp_url,
        }
        checks["contract_compatibility"] = {
            "status": "ok",
            **validate_discovery(discovery),
        }
        report.update({"status": "ok", "checks": checks})
        return report
    except ContractCompatibilityError as exc:
        checks.setdefault(
            "core_connection",
            {"status": "ok", "endpoint": config.mcp_url},
        )
        checks["contract_compatibility"] = {
            "status": "error",
            "error": str(exc),
        }
    except Exception as exc:
        checks["core_connection"] = {
            "status": "error",
            "endpoint": config.mcp_url,
            "error": f"{type(exc).__name__}: {exc}",
        }
        checks["contract_compatibility"] = {"status": "skipped"}

    report.update({"status": "error", "checks": checks})
    return report


def _offline_report(config: ResidentConfig) -> dict[str, Any]:
    report = _base_report(config)
    report.update(
        {
            "status": "config_only",
            "checks": {
                "configuration": {"status": "ok"},
                "core_connection": {"status": "skipped"},
                "contract_compatibility": {"status": "skipped"},
            },
        }
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "doctor":
        try:
            config = ResidentConfig.from_env()
        except ValueError as exc:
            print(
                json.dumps(
                    {
                        "status": "error",
                        "checks": {
                            "configuration": {
                                "status": "error",
                                "error": str(exc),
                            }
                        },
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 2
        report = (
            _offline_report(config)
            if args.offline
            else asyncio.run(run_live_doctor(config))
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] in {"ok", "config_only"} else 1
    raise AssertionError(f"unhandled command: {args.command}")
