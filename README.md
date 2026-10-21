# scholar-search · 学术检索

只读的中文文献题录检索服务，以 MCP 工具的形式提供给 AI 客户端。微内核 + 渠道插件：
知网是第一个渠道，万方、维普等以后按同一契约接入。

> **独立项目，非官方**，与任何数据库运营方无隶属、合作或授权关系。

## 它能做什么

- **关键词检索**：标题、作者、刊名、年份、被引、下载、详情链接
- **专业检索式**：知网官方 17 个字段（`SU/TKA/KY/TI/FT/AU/FI/RP/AF/FU/AB/CO/RF/CLC/LY/DOI/CF`），
  支持 `and/*`、`or/+`、`not/-`、`%` 与括号
- **翻页**：每次 1 页，页码 1–3；每页 20 或 50 条
- **排序**：相关度 / 发表时间降序 / 被引降序
- **单篇详情**：摘要、关键词、作者单位、卷期页、DOI
- **导出**：RIS / EndNote 纯文本，保留页面给出的文献类型（期刊 / 学位论文 / 会议 / 图书 / 报纸…）

## 它不做什么

- **不下载 PDF / CAJ**，不调用任何下载接口，不碰全文
- **不把题录写入 Zotero / EndNote / Mendeley**。只输出 RIS / EndNote 文本，
  导入由你自己在软件里完成（原因见 [ADR 0006](docs/adr/0006-no-third-party-ingest.md)）
- **不破解验证码**，遇到验证页立即停机，等你人工处理
- **不做批量抓取**，没有"爬全库"模式，日上限 300 次由内核强制
- 不实现来源类型筛选（传了会明确报错）；年份筛选只作用于本次已抓取的记录

## 安全边界

| 约束 | 值 |
|---|---|
| 动作词汇 | 固定九个：`goto` `wait_for` `type` `click` `select` `read_html` `read_text` `scroll` `sleep` |
| 任意 JS | 没有。扩展只认这九个动作，选择器由计划带下来 |
| 域名 | 白名单，由渠道 manifest 声明，内核与宿主双重校验 |
| 最小间隔 | 3000 ms 硬下限，外加 0–1.2 s 随机抖动，并发 1 |
| 单次计划 | ≤ 40 个动作 / ≤ 120 s |
| 每日配额 | 300 个网络动作（读类动作不计数） |
| 风控 | 验证页 / 验证码 / 403 / 登录跳转 → 立即终止，返回 `blocked`，冷却 24 h，不自动重试 |
| 凭证 | 零。不读也不存任何账号、Cookie、会话材料 |

## 工作原理

```
MCP 客户端 ──stdio / HTTP──▶ MCP server
                               │
                        内核：契约 / 策略 / 风控 / 计划 / 审计 / 缓存
                               │
                        渠道插件 channels/cnki/v2026_10
                               │
                     桥接适配器 ──TCP(loopback+token)──▶ 原生宿主
                                                          │
                                                    stdio │ 浏览器原生消息
                                                          ▼
                                                       扩展 ──▶ 你的浏览器
```

你不需要开调试端口，也不需要交出浏览器控制权：扩展只做九个通用动作，
站点知识（选择器、流程、解析）全部在 Python 侧的渠道插件里。

## 快速开始

前置：Windows、Python 3.11+、Edge（或 Chrome）。浏览器侧目前只在 Windows 上提供。

```powershell
# 1) 装包（从 Releases 下载 wheel，或本地 uv build 生成）
pip install .\scholar_search-0.3.17-py3-none-any.whl

# 2) 导出浏览器侧资源并注册原生宿主
scholar-search assets --target .\browser
pwsh .\browser\native-host\install.ps1

# 3) 装扩展：edge://extensions → 开发者模式 → 加载解压缩的扩展 → 选 .\browser\extension
#    扩展 ID 由 manifest 里的 key 固定，恒为 gmaimbocfjkolcpljeekjcomakipoaph

# 4) 验证
scholar-search status
```

`status` 里 `bridge_ready: true` 就通了。

更细的步骤（新建独立 Edge 环境、多浏览器、扩展 ID 对不上等）见
[浏览器环境与扩展](docs/browser-setup.md)。让 agent 帮你装，见
[skills/scholar-install](skills/scholar-install/SKILL.md)。

## 接入 MCP 客户端

stdio 方式（Claude Desktop、Codex、大多数客户端）：

```json
{
  "mcpServers": {
    "scholar-search": {
      "command": "scholar-search",
      "args": ["serve", "--transport", "stdio"]
    }
  }
}
```

HTTP 方式（本地回环 + 令牌）：

```bash
scholar-search serve --transport http --host 127.0.0.1 --port 8765
```

令牌在首次启动时写入 `%LOCALAPPDATA%\scholar-search\http-token`，请求带
`Authorization: Bearer <token>`，端点 `http://127.0.0.1:8765/mcp`。
细节见 [docs/integration/dsh.md](docs/integration/dsh.md)。

## 工具

| 工具 | 参数 | 返回 |
|---|---|---|
| `search` | `query`（关键词或专业检索式）、`channel`、`page` 1–3、`limit` 1–50、`sort`、`year_from`/`year_to` | `total`、`page`、`page_count`、`records[]` |
| `detail` | `url`（`search` 返回的链接）、`channel` | 单条完整题录（含摘要、DOI、卷期页） |
| `export` | `records`、`format`：`ris` 或 `endnote` | 纯文本，不落盘 |
| `status` | 无 | 渠道、剩余配额、冷却状态、桥接是否就绪 |

`search` 的年份筛选是**客户端筛选**：只对本次抓到的那一页生效，`total` 仍是站点总数。
筛选后为空说明目标年份不在这一页，换页或换检索式，不要连续翻页扫库。

## 升级到新版本

```powershell
pip install --upgrade .\dist\scholar_search-<新版>-py3-none-any.whl
scholar-search assets --target .\browser --force
pwsh .\browser\native-host\install.ps1 -Python <venv>\Scripts\python.exe
# 重启 MCP 客户端，让它重新拉起 server 进程
```

要点：

- **必须重启 MCP 客户端**。server 是 stdio 子进程，模块在启动时导入，换文件不会热生效。
- 扩展**通常不用重装**：Python 侧改动不影响扩展；只有 `extension/` 里的 JS 或
  `manifest.json` 变了才需要重新加载扩展。
- 原生宿主在升级后要重跑 `install.ps1`（它负责写清单、注册表项和低完整性标签）。

完整流程、目录布局与回滚见 [docs/operations.md](docs/operations.md)。

## 状态

当前 v0.3.17。真机验证过的能力（2026-10-21，知网 2026.10 版页面）：

| 能力 | 状态 |
|---|---|
| 关键词检索 | 通过（`IPMC` 595 条、`钙钛矿太阳能电池` 11820 条） |
| 专业检索式 | 通过（`SU='IPMC' and KY='驱动器'`） |
| 翻页 1–3 | 通过 |
| 每页 50 条 | 通过 |
| 排序（时间 / 被引） | 通过，稳定降序 |
| 单篇详情 | 通过（含摘要、作者单位、卷期页） |
| 导出 RIS / EndNote | 通过（图书 → `TY  - BOOK`，学位论文 → `THES`） |

## 目录

```
src/scholar_search/core/       内核：契约、注册表、策略、风控、审计、缓存、导出
src/scholar_search/channels/   渠道插件（当前只有 cnki/2026.10）
src/scholar_search/adapters/   浏览器适配器（bridge 生产 / fixture 测试）
src/scholar_search/transports/ stdio 与 HTTP
native-host/                   原生消息宿主（纯通讯层，Windows）
extension/                     浏览器扩展（九个动作，零站点知识）
schemas/                       记录与工具 JSON Schema
skills/                        给 agent 的技能说明
docs/                          架构、ADR、协议、运维、接入说明
tests/                         单元 + 契约 + fixture 回放
```

## 文档

| 文档 | 内容 |
|---|---|
| [架构说明](docs/architecture.md) | 分层、请求流、策略与风控、扩展点 |
| [运维手册](docs/operations.md) | 目录布局、部署、升级、回滚、排障 |
| [知网改版应对](docs/cnki-maintenance.md) | 站点变了改哪里、怎么验证 |
| [浏览器环境](docs/browser-setup.md) | 新建独立 Edge 环境、装扩展、扩展 ID |
| [Zotero 接入](docs/integration/zotero.md) | 手动导入 RIS 的步骤（不做自动化） |
| [发布到 GitHub](docs/publishing.md) | 推送、tag、CI 与发布 |
| [渠道契约](docs/channel-contract.md) | 新增渠道要实现的接口 |
| [桥接协议](docs/bridge-protocol.md) | 宿主与扩展的帧格式与校验 |
| [ADR 索引](docs/adr/) | 关键决策记录 |
| [故障台账](docs/incidents.md) | 线上踩过的坑与结论 |

## 合规声明

本项目仅用于个人学术研究中的题录检索。使用者应遵守目标站点的服务条款与所在机构的
使用规定。项目本身不附带任何数据、凭证或会话材料，也不提供把数据灌入第三方系统的能力。

## License

MIT，见 [LICENSE](LICENSE)；第三方参考与商标说明见 [NOTICE](NOTICE)。
