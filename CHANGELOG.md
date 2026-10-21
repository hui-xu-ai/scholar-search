# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/).

## [0.3.7] - 2026-10-21

### Fixed

- **Live detail type** Online-first journal detail pages have no volume/issue, so the
  previous metadata-only rule left `doc_type` empty and exported `GEN`. The journal
  header link text (`查看该刊数据库收录来源`) is now used as article-level structural
  evidence, so real online-first details export `JOUR`. Verified live on a CNKI
  journal article (abstract, DOI, keywords, 0 risk).

## [0.3.6] - 2026-10-21

### Fixed

- Read detail document types from complete type values or explicitly labelled
  type fields. Funding, subjects and source names cannot supply a document type;
  explicit online-first journal metadata is retained.
- Reserve two seconds between CNKI search content waits and their outer action
  deadlines, allowing a timeout response and its risk snapshot to reach the kernel.
- Add synthetic online-first metadata fixtures and regression coverage for all
  supported query/page/sort/page-size combinations. Live verification is pending.
- Accept wrapped (`《期刊》`) and status-suffixed (`期刊（网络首发）`) type values, and
  scan `.top-first` with the same exact-value rule, so explicit types are not lost
  to page decoration. Body/recommendation text still cannot supply a type.

## [0.3.5] - 2026-10-21

### Fixed

- **R034-01** Detail document type is read only from the article metadata header
  (`.top-first`, `.doc-top`, `.top-tip`, `li.top-space`). Body text, abstracts and
  related recommendations can no longer re-type the current article, and a concrete
  volume/issue/pages citation always wins as journal evidence. Fixtures added for
  "related thesis recommendation" and "conference notice in body".

## [0.3.4] - 2026-10-21

### Fixed

- **CSP** Clicks on CNKI's `<a href="javascript:void(0);">` pagination/sort links are
  cancelled at the default-action stage, so the page CSP no longer blocks a
  `javascript:` navigation while the site's own click handlers still run. Plain
  links and inputs are clicked as before.

## [0.3.3] - 2026-10-21

### Fixed

- **F01** The result table's `td.data` document type is parsed into `Record.doc_type`;
  RIS/EndNote now map journal/thesis/conference/newspaper/book/patent/standard/yearbook,
  and an unknown or missing type renders as `GEN` / `Generic` (plus a RIS note) instead of
  being silently exported as a journal article. `schemas/record.json` and the export
  validator include the new field; mixed-type fixture added.
- **F02** Detail readiness now waits for the article-level selector
  `.wx-tit h1, #ChDivSummary` instead of a bare `h1` (the login modal), and the inner wait
  is 8s so it finishes inside the 15s action budget and can still return the final page
  or risk snapshot.

## [0.3.2] - 2026-10-21

### Fixed

- **V01** A quota reservation that cannot be persisted now blocks that same action;
  an existing but corrupt/unreadable quota file is a hard error instead of being read
  as zero usage.
- **V02** If the cross-process plan lock cannot be created, the plan is refused; the
  process-local fallback was removed.
- **V03** The shared cooldown is re-checked after the interval sleep and immediately
  before the browser action.
- **V04** A cross-domain login redirect is still refused, but the reply keeps the final
  URL and risk metadata so the kernel can persist the 24h cooldown.
- **V05** Extension permissions and content injection are scoped to the enabled
  channel (`https://*.cnki.net/*`) and top frame only.

### Changed

- Skills now match the real contract: one page per call, no fabricated export
  `count`, and a single, consistent rule against batch detail loops.
- `install.ps1` falls back to `python`/`python3` on PATH and records the runtime HOME
  in `runtime-home.txt`; the host reads it at startup.
- Launcher logs move under `SCHOLAR_SEARCH_HOME/host/logs`.
- `scholar-search assets` refuses to overwrite existing directories without `--force`.
- Added `docs/integration/codex.md`.

## [0.3.1] - 2026-10-21

Risk follow-up fixes from `independent-20261021-02-risk-followup`.

### Fixed

- **R01** Every content-script reply (success, timeout, missing element, exception)
  carries the risk snapshot; `click`/`type`/`select` refuse to run while a captcha or
  login gate is already visible; the background no longer drops `data` on failures.
- **R02** A whole plan holds a cross-process lock; the quota slot is reserved
  atomically in `wait_turn` (interval check + increment + persist), so two processes
  cannot both spend the last request.
- **R03** The shared cooldown is re-checked before every action, not only at plan start.
- **R04** Actions stay bound to the tab opened by the plan's `goto`; a plan cannot
  drift to whatever tab the user activates. The extension keeps a configured host
  scope, and the host only lets a request narrow its trusted startup scope, never
  replace it.
- **R05** If quota persistence fails, the next `wait_turn` fails closed instead of
  trusting the stale on-disk counter.
- **R06** `HTTP 429` (status or error text) is now a terminal `rate_limited` signal.

### Compatibility

Two assertions in the earlier audit conflict with the newer risk scope and now fail
by design: the host no longer accepts an arbitrary `example.org` manifest without a
trusted scope, and the extension no longer navigates to unconfigured hosts.

## [0.3.0] - 2026-10-21

Security and contract hardening from the independent offline audit
(`independent-20261021-01`). Breaking: several invalid inputs that were quietly
accepted now fail loudly.

### Fixed

- **F01** Navigation replies carry the final URL and current title; the adapter
  surfaces a nested `data.url`; HTTP status is collected from the content script
  and `403` reaches the risk guard.
- **F02** Captcha visibility requires an on-screen, non-zero-size element that
  intersects the viewport; every action result carries the risk snapshot.
- **F03** Quota and interval are read and written under an inter-process lock;
  plans are serialized process-wide, so two servers cannot double-spend.
- **F04** The adapter never replays an action after a connection failure.
- **F05** A failed action stops the plan; the service raises `ActionError` and
  never parses or caches the page as a success.
- **F06** The cooldown deadline is latched in memory, so a failed state write
  cannot unblock the process that just detected a risk.
- **F07** Cache hits still respect an active cooldown.
- **F08** Replies are correlated with request ids; a handshake precedes the
  first action; the bridge protocol doc separates TCP JSON from native framing.
- **F09** One closed parameter schema (`core/params.py`) is enforced by kernel
  and host; deadlines above 15s are rejected; frames are capped at 2 MiB on
  write and `read_html` truncates by UTF-8 bytes with a `truncated` flag;
  `wait_for` honours `state=hidden`.
- **F10** Export validates records against the public schema and refuses
  newline/type injection in any field.
- **F11** Malformed search pages and non-article detail pages raise `ParseError`
  instead of being cached as empty/valid results.
- **F12** Detail URL authorisation uses the parsed path prefix.
- **F13** Old site-version directories stay discoverable; selecting a version
  no longer requires every directory to match the channel manifest.
- **F14** Domain authority moves to the selected manifest (sent per request);
  the host no longer hard-codes CNKI and the extension accepts any https host.
- **F15** Host runtime files live under `SCHOLAR_SEARCH_HOME/host`; the
  installer labels that directory low-integrity writable.
- **F16** HTTP Host check compares the whole hostname, not a prefix.
- **F17** Wheel ships native-host, extension and schemas as package assets;
  `scholar-search assets --target DIR` extracts them; sdist includes browser
  sources and fixtures.
- **F18** `schemas/tools.json` matches the four live tools; README, NOTICE and
  package metadata are on 0.3.0.
- **F19** `status.bridge_ready` probes a live host instead of checking for a file.
- **F20** `ruff format --check` passes and `.pre-commit-config.yaml` is present.


## [0.2.6] - 2026-10-21

### Added

- `sort=date` and `sort=citation` drive the result grid's sort tabs (`#orderList`).
  A relevance reset precedes the target click, because the grid remembers the previous
  direction and a bare click would toggle unpredictably.
- Live-verified: `limit=50, sort=date` returns 50 rows in strict descending date order
  (2026 → 2024), 12 pages, no verification prompt.

## [0.2.5] - 2026-10-21

### Added

- Field detection for expert search now covers every documented code: `SU`, `TKA`, `KY`,
  `TI`, `FT`, `AU`, `FI`, `RP`, `AF`, `FU`, `AB`, `CO`, `RF`, `CLC`, `LY`, `DOI`, `CF`.
  Unknown `XX=` / `XX%` codes also route to the expert page instead of the one-box search.
- Skill documentation now lists the official field table and operators (`and`/`*`,
  `or`/`+`, `not`/`-`, `%` for author matching).
- Live-verified: `TI='IPMC' and AU % '王'` returns 43 hits across 2014–2026.

## [0.2.4] - 2026-10-21

### Added

- `limit > 20` switches the result grid to 50 rows per page (12 pages for the 595-hit
  `IPMC` query); with the 3-page cap a single call returns up to ~150 records.
- `year_from` / `year_to` are applied client-side to the fetched records. The site's own
  year control is never touched; `total` still reports the site's full result count.

### Fixed

- Search URLs carry a per-call nonce so every call starts from the grid's default state;
  previously a repeat navigation could inherit the previous page size and break the switch.

## [0.2.3] - 2026-10-21

### Fixed

- Account-gate detection now requires a **visible** login modal; the previous body-text match
  flagged CNKI's always-present login panel and produced a false cooldown.
- Native hosts register themselves under `hosts/` and answer a ping; the adapter picks a live
  host instead of trusting a single stale `bridge.json`.
- Removed host “retirement”: it caused reconnect churn where each new host killed the previous one.
- Verified after the fix: one read-only search returned 595 hits, no cooldown.

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






