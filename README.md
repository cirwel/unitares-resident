# UNITARES Resident

UNITARES Resident is the first-party agent userland for
[UNITARES](https://github.com/cirwel/unitares): a cohesive, persistent agent
experience built as an ordinary client of UNITARES Core.

Core records, scores, interrupts, and remembers. Resident owns the conversation
loop, model/provider adapters, tools, scheduling, queues, and user interaction.
The split is intentional:

```text
user / operator
      |
UNITARES Resident       conversation · providers · tools · queues
      |
public unitares-sdk     identity · check-ins · policy responses · memory
      |
UNITARES Core           governance · audit · knowledge · dialectic
```

Resident has no direct database access, imports no UNITARES server internals,
and receives no privileged scoring or policy path. A Hermes, Claude, Codex, or
custom runtime should be able to use the same public contract.

## Status

This repository is an **early skeleton**, not a usable general-purpose agent
yet. It establishes the product boundary and a tested runtime seam for model
backends. Provider adapters, durable conversations, tool execution, scheduling,
and operator interfaces are subsequent milestones.

Core compatibility is negotiated live rather than inferred from matching
repository or package versions. `unitares-resident doctor` connects through the
public SDK, calls `list_tools(lite=true)`, and verifies Core's versioned
interface contract, normalized lifecycle envelope, and required lifecycle
capabilities. It exits nonzero when Core is unreachable or incompatible. Use
`doctor --offline` only for an explicitly configuration-only check.

## Development

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev
uv run pytest
uv run unitares-resident doctor
uv run unitares-resident doctor --offline
```

Runtime configuration uses ordinary environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `UNITARES_RESIDENT_NAME` | `UNITARES Resident` | Cosmetic resident name and identity-anchor label |
| `UNITARES_MCP_URL` | `http://127.0.0.1:8767/mcp/` | Public UNITARES MCP endpoint |
| `UNITARES_RESIDENT_INTERVAL_SECONDS` | `60` | Seconds between runtime cycles |
| `UNITARES_RESIDENT_CYCLE_TIMEOUT_SECONDS` | `120` | Maximum duration of one cycle |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the non-privileged boundary and
[CONTRIBUTING.md](CONTRIBUTING.md) for the development contract.
