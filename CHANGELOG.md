# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/).

## [0.2.2] - 2026-10-21

### Changed

- Year filters are disabled: the result-page year control (`#btnFilterYear`) triggered an
  account verification gate (“手机号认证”) during a live test. `year_from` / `year_to`
  now fail with an explicit error instead of touching that control.
- Risk guard detects account verification gates via the content script (`auth_required`)
  and reports `login_redirect`, so a gate cannot be mistaken for an empty result page.
- Incident recorded in `docs/incidents.md`; 62 tests.

## [0.2.1] - 2026-10-21

### Fixed

- Detail parser reads volume/issue/pages from the `.top-first` citation line
  (`力学学报 . 2022 ,54 (01) : 184-195`); verified by fixture replay and a live MCP call.
- Added `tests/fixtures/cnki_detail_print_2026_10.html` and a regression test (59 tests).

## [0.2.0] - 2026-10-20

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
- CNKI channel v2026.10: search plan, result-table parser, detail plan and parser.
- MCP server with four tools: search, detail, export, status.
- stdio transport and loopback HTTP transport with bearer token and Host check.
- `scholar-search status` reports channels, cooldown, quota and bridge readiness.
- 51 tests; ruff and mypy --strict clean.
- Verified selectors against a live CNKI page (595 hits, 20 rows); trimmed fixture in `tests/fixtures`.
- Search plan now drives the search box (goto → type → click → wait → read) instead of a static URL.
- Native host launcher is a compiled .exe: Edge refuses to start `.cmd` hosts.
- Host runtime files (endpoint, log) moved to the per-user temp directory, because browsers launch native hosts at low integrity and `AppData\Local` is not writable there.
- Single-instance check and per-connection replies fix duplicate-host races.
- 52 tests.
- Expert search: field expressions (`SU=`, `TI=`, `KY=`, `AU=` …) go through `AdvSearch?type=expert`.
- Pagination: `page=2..3` clicks `#PageNext` and waits for the next result batch.
- Search limit is honoured (`limit` was previously ignored).
- Cache keys include the package version so parser changes do not serve stale hits.
- Plan budget stays under 120s via per-action timeouts; page capped at 3.
- 56 tests; live-verified: keyword 595 hits, expert expression 57 hits, page 2 distinct.
- Detail parser rewritten for the 2026 layout: `.wx-tit h1`, `h3.author`, `li.top-space` rows; strips author affiliation marks and “附视频” suffixes.
- Risk guard now flags verification interstitials by document title (“安全验证”), after an expired detail URL served one.
- Native host runs one process per browser connection: the previous single-instance check deadlocked reconnects.
- Skills: `scholar-search`, `scholar-detail`, `scholar-export`.
- Docs: reference parity table and incident log.
- 58 tests; release workflow on version tags.

## [0.1.0] - 2026-10-20

### Added

- Project skeleton: microkernel layout, channel plugin directory, adapters, transports.
- Core contracts (`core/contracts.py`): action vocabulary, plan, record, channel and adapter protocols.
- Hard limits in `core/config.py` (3s floor, 1 concurrency, 3 pages per call, 200 per day, 24h cooldown).
- Error hierarchy with risk-blocked payload.
- ADRs 0001-0004: microkernel, read-only, native bridge, risk stop.
- JSON schemas for records and MCP tools.
- CNKI channel manifest (site version 2026.10), implementation pending.
