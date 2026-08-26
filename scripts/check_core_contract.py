#!/usr/bin/env python3
"""Check a UNITARES Core contract artifact as an external consumer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from unitares_resident.contract import (
    ContractCompatibilityError,
    validate_core_contract,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Path)
    args = parser.parse_args()

    artifact = json.loads(args.contract.read_text())
    tool_names = [
        item["name"]
        for item in artifact.get("capabilities", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    ]
    try:
        report = validate_core_contract(artifact, tool_names)
    except ContractCompatibilityError as exc:
        print(json.dumps({"compatible": False, "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
