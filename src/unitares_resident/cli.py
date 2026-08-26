"""Command-line entry point for the Resident skeleton."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from unitares_resident.config import ResidentConfig


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="unitares-resident")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser(
        "doctor",
        help="validate configuration and print the public-client boundary",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "doctor":
        config = ResidentConfig.from_env()
        print(
            json.dumps(
                {
                    "status": "ok",
                    "config": config.public_summary(),
                    "governance_boundary": "unitares-sdk",
                    "server_internals": False,
                    "database_access": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    raise AssertionError(f"unhandled command: {args.command}")
