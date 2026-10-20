# Architecture

## Layers

```
transports/      stdio | http(loopback + token)
server.py        MCP tool surface (5 stable tools)
core/            contracts, registry, policy, risk, planner, audit, cache
channels/        cnki/2026_10 (site knowledge lives only here)
adapters/        bridge (default) | fixture (tests) | cdp (future)
native-host/     action router + second validation layer
extension/       nine generic verbs, zero site knowledge
```

Dependencies point downward only. A channel never imports a transport; a
transport never imports a channel implementation.

## Request flow

1. A transport receives a tool call and builds a typed request.
2. The service validates parameters against `core/contracts.py`.
3. The registry resolves the channel and its `site_version`.
4. The channel emits a `Plan` (a tuple of nine-verb actions).
5. The policy layer validates domains, verbs, plan size, interval, quota.
6. The adapter executes the plan; every outcome is checked for risk signals.
7. Any risk signal aborts the plan, writes audit, sets a 24h cooldown.
8. The channel parses returned HTML into `Record` objects.
9. The service returns records plus pagination metadata.

## Why a microkernel

Site changes are expected, not exceptional. Confining them to
`channels/<name>/<site_version>/` means a layout change is a new directory,
not a refactor. The kernel, tool schemas, and agent skills stay put.

## Invariants

- The action vocabulary is closed. There is no `eval` and no download verb.
- Hard limits are floors/ceilings; channels may tighten, never loosen.
- Parsing happens server-side so it can be tested against fixtures offline.
- The extension holds no site knowledge; selectors arrive inside plans.

## Decision records

- `docs/adr/0001-microkernel.md`
- `docs/adr/0002-read-only.md`
- `docs/adr/0003-native-bridge.md`
- `docs/adr/0004-risk-stop.md`
