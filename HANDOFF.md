# 交接文档 · scholar-search（2026-10-21）

给下一个会话的接手人。先读 `AGENTS.md` 的硬约束，再读本文件。

## 1. 现状一句话

只读的 CNKI 题录检索 MCP 服务，已通过 DSH 的**官方 bundle 方式**注册并在真实会话中验证：
`mcp__scholar-search__search` 返回 `total=150`，工具与浏览器宿主链路正常。

## 2. 代码与版本

| 项 | 值 |
|---|---|
| 仓库 | `D:\Python\DeepSeek\DateWork\scholar-search` |
| 分支 / HEAD | `main` / `376694a`（交接文档提交之前；以 `git log -1` 为准） |
| 最新 tag | `v0.3.16` |
| 已安装 | `C:\Users\xuhui\AppData\Local\scholar-search\installations\0.3.16`（已部署并真机验证） |
| Codex 配置 | `C:\Users\xuhui\.codex\config.toml` → 0.3.16 venv |
| DSH bundle | `scholar-search-dsh-bundle` 的 `command` 与 `version` 已改 0.3.16 |
| 扩展 | 0.3.11 加载的 JS；0.3.12–0.3.16 只有 Python 改动，**无需重载** |
| 原生宿主 | HKCU 注册已指向 0.3.16 的 manifest，进程已从 0.3.16 目录重启 |

### 0.3.16：文献类型归一化（本轮）

现象：按被引排序的一次检索里，一本图书的 `doc_type` 是 `"中文图书"` 而不是 `book`。
原因：`parse_search._doc_type` 用 `_DOC_TYPES.get(token, token.casefold())` 兜底，
`casefold()` 对中文无效，未映射的原始中文串直接进了记录；导出层认不出，RIS 退化成
`GEN`（图书被当成通用条目）。

修法：新增 `channels/cnki/v2026_10/doc_types.py`，两个解析器共用：
剥语言前缀（中文/外文/西文/英文/日文/俄文）、剥包装（《》〈〉()（）[]【】）、
剥 `文献类型:` 标签、剥「网络首发」等状态词，再查规范表；
**查不到就返回 `None`**，让导出层按通用类型渲染并注明「来源未给出类型」，
而不是把一个没有意义的中文字符串塞进记录。

真机验证（走 0.3.16 安装目录）：同一查询的 5 条记录里，
图书那条现在是 `'book'`，导出为 `TY  - BOOK` / `%0 Book`。

### 0.3.14 → 0.3.15 这一轮做了什么

- **0.3.14**（`7079948`）：`goto` 后加 `sleep 2500`，等 CNKI 首屏后的二次跳转，
  避免内容脚本被替换导致 `type` 超时。
- **0.3.15**（`69534c7`）：真机一跑就发现 0.3.14 的 `sleep` 自己会超时——
  实测 2500ms 的暂停在 **3004ms** 才回包，而超时预算正好 3000ms。
  根因是**浏览器定时器对齐**：CNKI 窗口不是前台窗口时，定时器被按整秒分桶，
  任何暂停都可能晚到近 1 秒。
  现在所有暂停走 `_settle(ms)`，超时 = 暂停时长 + 2s 余量。
  多出来的余量从别处腾：`read_html` 6→4s、结果栅格/筛选等待 8→6s、
  输入框/结果等待 12→10s，最坏计划仍 116.6s < 120s 上限。
  **ADR 0005 的限额一个都没动，动词集和计划形状也没变。**
- 两个版本都在 `dist/` 有 whl + sdist，并核对过 wheel 内容。
- 仓库**没有配置 remote**，tag 只在本地，release workflow 不会触发。

### 0.3.15 部署（已完成）

按第 9 节清单执行，0.3.13 目录保留未动：

1. `Copy-Item installations\0.3.13 installations\0.3.15 -Recurse`（49 MB）。
2. 用 `dist\scholar_search-0.3.15-py3-none-any.whl` 替换 `venv\Lib\site-packages`
   下的 `scholar_search` 与 `*.dist-info`。
3. 从仓库覆盖 `browser\native-host`（main.py / launcher.cs / install.ps1 / README.md）、
   `browser\extension`、`browser\schemas`。
4. `browser\native-host\install.ps1 -Python ...0.3.15\venv\Scripts\python.exe` ——
   重写 manifest、`python-path.txt` 与 HKCU 注册（Edge 和 Chrome 都指向 0.3.15）。
5. Codex `config.toml` 的 `mcp_servers.scholar-search.command` 改到 0.3.15。
6. DSH bundle 的 `cordis.patch.yml` 的 `command` 与 `package.json` 的 `version` 改 0.3.15。
7. 杀掉旧的 `scholar-host.exe` 与 `main.py`（pid 3684 / 32948），扩展自动重连，
   宿主从 0.3.15 目录起来（`host.log` 里 `cwd=...0.3.15\browser\native-host`）。
8. `Scripts\scholar-search.cmd` 仍是一行 `python.exe -m scholar_search.cli %*`，没有复制旧 exe。

9. 重启 DSH。重启后 MCP 服务进程换成
   `installations\0.3.16\venv\Scripts\python.exe`，官方 `mcp__scholar-search__*`
   链路才用上 0.3.15 的计划代码（已验证：进程路径、`status`、一次真实 `search`）。


## 3. 已真机验证（2026-10-21）

- 第 1 页 / 第 2 页：`page: 2`，2024/2024/2024 降序
- 专业检索式 `SU='IPMC'`：539 条
- 50 条/页：50 条
- 学位论文详情：`thesis`，RIS `THES`，EndNote `Thesis`
- 排序方向反馈纠正：读 `#orderList` 的 `cur` 类，ASC 才补一次点击
- 风控：无验证码、无 403、无冷却
- 通过 DSH MCP 的真实调用：`search` 成功（total 150）
- **0.3.15 修复后真机复验**：连续两次，均无冷却。
  `IPMC`、`limit=5` → 10.0 秒，`total=595`，5 条 journal 记录；
  `碳纳米管`、`limit=5` → 10.7 秒，`total=36375`。
  一次检索 = 3 个网络动作（配额 193→199）。
  审计里那次 `sleep` 耗时 2504ms（窗口在前台），而失败那次是 3004ms（窗口不在前台）——
  正是定时器按整秒分桶的证据。运行方式见第 8 节。
- **部署后复验（走安装目录，不用仓库源码）**：`石墨烯`、`limit=5` → 9.6 秒，
  `total=111875`，5 条记录，配额 101→98。用的是
  `installations\0.3.16\venv\Scripts\python.exe`，证明部署树本身可用。
- **重启 DSH 后走官方 MCP 链路**：`mcp__scholar-search__search`
  （`钙钛矿太阳能电池`、`limit=3`）→ `total=11820`，3 条记录，标题/作者/期刊正确。
  审计里那次 `sleep` 耗时 **3145ms** 且成功——正是被节流的场景，
  旧 3000ms 预算必挂，新 4500ms 预算通过，修复得到现场证明。

## 4. 关键路径

| 用途 | 路径 |
|---|---|
| 运行期 HOME | `C:\Users\xuhui\AppData\Local\scholar-search` |
| 配额 / 冷却 | `...\state\quota.json`、`...\state\cooldown.json` |
| 审计 | `...\audit\audit.jsonl` |
| 宿主日志 | `...\host\logs\host.log` |
| 桥接端点 | `...\host\bridge.json` |
| DSH bundle | `D:\Python\DeepSeek\DateWork\scholar-search-dsh-bundle` |
| DSH profile | `D:\DSH\.dsh\profiles\desktop` |

## 5. MCP 注册（DSH）

- profile 的 `package.json` 通过 `link:` 引用 bundle，并把 `scholar-search-dsh-bundle` 加进 `dsh.profile.bundles`。
- bundle 内 `cordis.patch.yml` 用**官方 `insert:` 形状**，依赖 `@deepseek-ai/dsh-mcp-client@0.2.1-rc.2`。
- **绝对不要**手改 profile 的 `cordis.patch.yml` 或手工往 profile 的 `node_modules` 拷包。
  2026-10-21 这样做过一次，导致桌面端启动崩溃，最后靠网页版恢复。
- 当前会话的工具清单在安装前生成，看不到 `mcp__scholar-search__*`；**新会话**里可见。

## 6. 当前配额与限制

- 日期 `2026-10-21`，已用 224 / 300，剩余 **76**，无冷却。
- 一次 `search` 记 **3** 个网络动作（`goto` + `type` + `click`）；`sleep`/`wait_for`/
  `read_html` 等读动词不占配额。
- 每日 300 个网络动作（ADR 0005）。
- 3000ms 下限 + 0–1.2s 随机抖动（约 10% 额外 2–4s），并发 1。
- `page` 1–3，`limit` 1–50，单计划 ≤40 动作 / 120s。
- 遇验证码/403/登录跳转：立即停、返回 `blocked`、写 24h 冷却；人工完成后用
  `scholar-search reset --confirm` 显式清除，不自动重试。

## 7. 已知问题与排查顺序

### `type` / `sleep` 在暂停动作上 `bridge.timeout`（0.3.15 已修）

现象：`goto` 成功，紧跟的 `sleep` 用满超时才报错（实测 2500ms 的暂停 3004ms 回包，
配 3000ms 预算）；`type` 也可能同样报错。
原因：**定时器对齐**。CNKI 窗口不是前台窗口时，浏览器把定时器按整秒分桶，暂停最多
晚到近 1 秒。0.3.15 起所有暂停的预算 = 暂停时长 + 2s。
如果 0.3.15 之后还出现：

1. 看 `audit.jsonl` 里 `duration_ms` 是不是贴着超时值；贴着就是又被节流了；
2. 把 CNKI 窗口切到前台（`WScript.Shell.AppActivate(<edge 进程 id>)` 即可），
   goto 走的是 `lastFocusedWindow` 的活动标签页；
3. Edge 只留一个可见窗口、一个 CNKI 标签页，窗口别最小化；
4. 不要连续重试，不要换 IP，不要延时重试。

### 复制 venv 后 `scholar-search.exe` 指向旧版本

从旧安装目录复制 venv，`Scripts\scholar-search.exe` 仍指向更早版本（例如 0.3.13 目录里跑出 0.3.2）。
0.3.13 已删除该 exe，改用 `Scripts\scholar-search.cmd`（`python -m scholar_search.cli`）。
新部署时照做，或统一用 `python -m`。

### Edge 报「隐私错误」`NET::ERR_CERT_COMMON_NAME_INVALID`（2026-10-21 遇到）

现象：`goto` 报 ok，紧跟的 `sleep`/`type` 报 `content_not_ready`，
因为浏览器停在证书错误页，那上面没有内容脚本。

原因：本机开着 Clash Verge（系统代理 `127.0.0.1:7897`，未开 TUN），Edge 走系统代理
被中间换证，`kns.cnki.net` 证书名不匹配。PowerShell 的 `Invoke-WebRequest` 不走
WinINET 注册表代理、直连 200，所以容易误判「站点没问题」。

处理（已做）：把 `*.cnki.net;cnki.net` 加进
`HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings` 的 `ProxyOverride`，
再用 `InternetSetOption(NULL, 39/37, ...)` 广播变更，重载页面即恢复。
回滚：把这两项从 `ProxyOverride` 删掉（原值末尾是 `<local>`）。
更持久的做法是在 Clash 规则里给 `DOMAIN-SUFFIX,cnki.net` 配 `DIRECT`。

判断口诀：`content_not_ready` 先看浏览器标题是不是错误页；证书类错误别重试，先修代理/证书。

### 页面状态导致 `goto` 超时

长时间复用同一个 CNKI 标签页会出现 `goto` 15s 超时。关闭所有 CNKI 标签页或重启 Edge 后恢复。不是代码问题。

## 8. 真机自测（会消耗配额）

最省事的方式：用**已安装解释器 + 仓库源码**，直接对着活的宿主桥跑，不用经过 MCP
服务，所以能立刻验证工作区代码。脚本模板在
`D:\Python\DeepSeek\DateWork\.tmp-low\accept-live.py`（副本可自己重写：

```python
from scholar_search.bootstrap import build_service
from scholar_search.core.contracts import SearchQuery

service = build_service()
print(service.status())
page = service.search(SearchQuery(text="IPMC", channel="cnki", limit=5))
print(page.total, page.page, len(page.records))
```

运行：

```powershell
$env:SCHOLAR_SEARCH_HOME='C:\Users\xuhui\AppData\Local\scholar-search'   # 直接用真 HOME，配额/审计不分叉
$env:PYTHONPATH='D:\Python\DeepSeek\DateWork\scholar-search\src'
$env:PYTHONDONTWRITEBYTECODE='1'
& 'C:\Users\xuhui\AppData\Local\scholar-search\installations\0.3.16\venv\Scripts\python.exe' -B accept-live.py
```

注意：
- 一次 `search` 花 3 个网络动作；跑之前先看 `quota.json`。
- 控制台是 GBK，中文标题会乱码显示；要核对内容就写 UTF-8 文件再看。
- 跑之前把 CNKI 的 Edge 窗口切到前台，并且只留一个可见窗口。

## 9. 构建与部署清单

1. 改版本号：`pyproject.toml`、`src/scholar_search/__init__.py`、
   `extension/manifest.json`、`NOTICE`、`CHANGELOG.md`。
2. `uv build`（wheel + sdist），产物放 `dist/`。
3. 复制上一版 venv 到 `installations\<新版>`，替换 `site-packages\scholar_search`
   与 `*.dist-info`，复制 `browser\native-host|extension|schemas`。
4. 跑 `browser\native-host\install.ps1 -Python <新版>\venv\Scripts\python.exe`。
5. 更新 Codex `config.toml` 的 venv 路径。
6. 停掉 `scholar-host.exe` 与 `native-host\main.py`，等待扩展重连。
7. 不要复制旧 `Scripts\scholar-search.exe`；用 `python -m` 或重建 `.cmd`。

## 10. 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\mypy.exe src
```

扩展断言脚本（历史审计目录）：

- `...\audits\independent-20261021-02-risk-followup\extension-followup.cjs`
- `...\audits\independent-20261021-03-v031-verification\extension-edges.cjs`

### 本机 DSH 沙箱下跑 python 的坑（2026-10-21 实测）

pwsh 里直接起的 python / ruff / uv / mypy 子进程是**低完整性 AppContainer 令牌**，只能写带
Low 完整性标签的路径。工作区根 `D:\Python\DeepSeek\DateWork` 有该标签，`scholar-search`
子目录、`%TEMP%`、`D:\uv-cache` 都没有，于是出现 `PermissionError`、`.ruff_cache 拒绝访问`、
`tempfile: No usable temporary directory` 这类假故障（代码本身没问题）。

绕过办法：新建一个目录（自动继承 Low 标签）当临时区，并把各种缓存指过去：

```powershell
$low='D:\Python\DeepSeek\DateWork\.tmp-low'
$env:TMP=$low; $env:TEMP=$low; $env:TMPDIR=$low; $env:UV_CACHE_DIR="$low\uv-cache"
$env:PYTHONDONTWRITEBYTECODE='1'; $env:PYTHONPYCACHEPREFIX="$low\pycache"
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp "$low\pytest"
.\.venv\Scripts\ruff.exe check --no-cache src tests
.\.venv\Scripts\mypy.exe --cache-dir "$low\mypy" src
uv build --out-dir "$low\dist"    # 再 Copy-Item 回 dist\
```

`git` 子进程不受影响，提交、打 tag 正常。**不要**给仓库加 Low 完整性标签来图省事——那等于
让任何低完整性进程都能改源码。

## 11. 待办

- [x] 提交 `plan_search.py` + 测试改动，发 `0.3.14`（`7079948`，tag `v0.3.14`）
- [x] 真机复验 0.3.14 —— **一跑就发现 `sleep` 自己超时**，遂发 `0.3.15`（`69534c7`）：
      暂停动作加 2s 回包余量，并从读/等待超时里腾出预算。真机已通过（见第 3 节）。
- [x] 升级线上到 0.3.15：安装目录、Codex、DSH bundle、HKCU 注册、宿主进程全部换好，
      部署后走安装目录真机复验通过（见第 2、3 节）。
- [x] 重启 DSH，MCP 服务进程换到 0.3.15，官方链路真机通过。
- [x] 修文献类型归一化，发 `0.3.16`（`376694a`），安装目录 / Codex / bundle / 宿主全部换到
      0.3.16，并走安装目录真机验证（图书 → `book` → `TY  - BOOK`）。
- [ ] **再重启一次 DSH**：当前 MCP 服务进程还是 0.3.15 的代码，`doc_type` 修复要重启后才在
      `mcp__scholar-search__*` 里生效。不重启也不影响检索，只是图书类型会退回 `中文图书`。
- [ ] 观察 `sleep` / `type` 超时是否还会出现；出现就先看 `duration_ms` 是否贴超时、
      再确认 CNKI 窗口在前台且只有一个可见窗口
- [ ] 配额跨天后确认 `quota.json` 的 `day` 字段自动重置
- [ ] 复验时按第 8 节自测，注意配额（写本文件时 224/300，余 76；一次检索 = 3）
- [ ] 旧安装目录可择日清理：`installations\0.3.2` … `0.3.15` 都已无用（0.3.16 是当前版本）

