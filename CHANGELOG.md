# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Kernel pipeline: registry, policy, risk guard, planner, audit, cache, service.
- Channel registry with site-version selection and manifest/version consistency checks.
- Policy engine: verb/domain allowlists, 3s hard floor, daily quota, plan size and duration limits.
- Risk guard: captcha/verify/403/login detection, 24h persisted cooldown, manual reset only.
- JSONL audit log (structural facts only, no page content or credentials).
- SQLite response cache with TTL.
- RIS and EndNote text export.
- Fixture adapter for offline replay.
- 40 unit and contract tests covering policy, risk, planner, cache, registry, service, export.
- Native bridge: 4-byte-length JSON framing, request correlation, timeout handling.
- Bridge policy: nine-verb allowlist, https-only, CNKI host allowlist, sleep bound.
- Loopback TCP channel between host and MCP server, per-run random token.
- MV3 extension skeleton (background relay + nine generic DOM verbs).
- `native-host/install.ps1` registers the host for Edge and Chrome under HKCU.
- 47 tests including bridge framing, policy and TCP round-trip.



## [0.1.0] - 2026-10-20

### Added

- Project skeleton: microkernel layout, channel plugin directory, adapters, transports.
- Core contracts (`core/contracts.py`): action vocabulary, plan, record, channel and adapter protocols.
- Hard limits in `core/config.py` (3s floor, 1 concurrency, 3 pages per call, 200 per day, 24h cooldown).
- Error hierarchy with risk-blocked payload.
- ADRs 0001-0004: microkernel, read-only, native bridge, risk stop.
- JSON schemas for records and MCP tools.
- CNKI channel manifest (site version 2026.10), implementation pending.
