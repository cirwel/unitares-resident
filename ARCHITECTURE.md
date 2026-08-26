# Architecture

UNITARES Resident is a sibling product to UNITARES Core, not a subsystem inside
it. Resident may make Core easy to use, but it must remain observationally and
operationally comparable to any other governed client.

## Dependency rule

The allowed inward dependency is `unitares_sdk` plus public network contracts.
Resident must not import the UNITARES server package (`src` or
`governance_core`), connect to its database, or call a private dispatcher.

CI guards this in two places, because the boundary has two halves and an import
check only sees one of them:

| Guard | Covers | Where |
|---|---|---|
| import scan | reaching Core through a library | `tests/test_boundary.py` |
| literal scan | a privileged Core route written into the source | `tests/test_boundary.py` |
| endpoint check | being *pointed* at a privileged route | `config._reject_privileged_url`, at runtime |

The third is not a test but a refusal: `UNITARES_MCP_URL` is validated to name
the public MCP surface. Before it, `startswith("http")` accepted `/v1/tools/call`,
`/v1/lease/`, `/v1/agents` and `/admin` equally, so the strongest claim in this
document was enforced only by nobody having tried. Reaching a privileged route
is a configuration act, and no amount of import checking can see one.

The rule is keyed on the URL **path**, not the host or port. Deployments move
between loopback, a tailnet name, and a public gateway; the surface is the
contract and does not move. It is an allowlist, so a Core route added later is
refused by default rather than permitted until someone remembers to list it.

Explicitly **not** covered, so that the guarantee is not over-read: provider
traffic (OpenAI, Anthropic, local models) is expected and unconstrained, and a
URL assembled at runtime from parts is invisible to a static scan.

## Runtime seam

`ResidentAgent` subclasses the public SDK's `GovernanceAgent`. The SDK owns MCP
connection, identity anchors, check-ins, heartbeats, and pause delivery. An
injected `TurnBackend` owns reasoning and returns a transport-neutral
`ResidentTurn`. The runtime converts that turn into the SDK's `CycleResult`.

This seam keeps provider choice outside governance. OpenAI, Anthropic, local
models, or a Hermes adapter can implement `TurnBackend` without changing the
Core contract or gaining a privileged path.

## Planned layers

1. Provider-neutral conversation and turn store
2. Model and tool adapters
3. Durable task queue and scheduler
4. Operator-facing CLI/API/UI
5. Reference deployment profiles

Each layer must preserve the same identity, check-in, outcome, and policy
semantics available to an external SDK consumer.
