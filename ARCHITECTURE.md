# Architecture

UNITARES Resident is a sibling product to UNITARES Core, not a subsystem inside
it. Resident may make Core easy to use, but it must remain observationally and
operationally comparable to any other governed client.

## Dependency rule

The allowed inward dependency is `unitares_sdk` plus public network contracts.
Resident must not import the UNITARES server package (`src` or
`governance_core`), connect to its database, or call a private dispatcher. CI
guards the import boundary.

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
