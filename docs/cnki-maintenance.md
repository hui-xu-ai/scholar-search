# 知网改版应对：改哪里、怎么验证

知网平均每年会动几次页面。本项目的设计前提就是"改版是常态"，所以改版不等于重构：
**新增一个站点版本目录，内核、宿主、扩展都不动。**

本文给出定位方法、需要改的文件清单、以及升级流程。

## 1. 怎么发现改版了

| 现象 | 大概率原因 |
|---|---|
| `ParseError: page has no result-grid structure` | 结果表容器或分页标记的选择器失效 |
| 检索成功但 `records` 为空、`total` 有值 | 行选择器失效，或字段选择器全对不上 |
| `total` 为 `None` | "共找到 N 条"的容器变了 |
| 年份/被引/下载全部为 `None` | `td.date` / `td.quote` / `td.download` 变了 |
| 详情页 `ParseError: detail page has no article header or abstract` | 标题或摘要容器变了 |
| 详情有标题但摘要/关键词/单位为 `None` | 对应选择器变了，解析器静默留空 |
| 动作 `not_found` 或 `wait_for` 超时 | 输入框、提交按钮、下一页、每页条数等交互选择器变了 |
| 排序纠正反复触发 | `#orderList` 的 `cur`/`ASC` 类名约定变了 |

先看 `audit/audit.jsonl` 里失败的动作和错误码，再看 `ParseError` 的具体消息——
解析器抛错的位置基本就指向要改的文件。

## 2. 需要改的文件（都在 `channels/cnki/` 下）

| 文件 | 管什么 | 什么时候改 |
|---|---|---|
| `manifest.json` | 渠道名、域名白名单、动作集、能力、`min_core` | 域名或能力变化；`min_core` 只在用到新内核 API 时抬 |
| `v<版本>/selectors.py` | **所有** CSS 选择器与入口 URL | 九成改版只改这个文件 |
| `v<版本>/plan_search.py` | 检索流程、等待策略、分页、排序、每页条数 | 交互流程变了（多一步弹窗、按钮换位置、异步时机变了） |
| `v<版本>/plan_detail.py` | 详情页的开页与就绪判定 | 详情页不再是 `.wx-tit h1` / `#ChDivSummary` 就绪 |
| `v<版本>/parse_search.py` | 结果表 → `Record` | 列结构、字段含义、总数/页码文案变了 |
| `v<版本>/parse_detail.py` | 详情页 → `Record` | 题名、作者、单位、摘要、关键词、DOI、卷期页的来源变了 |
| `v<版本>/doc_types.py` | 文献类型归一化 | 出现新的类型词（如「法律法规」）或新的前缀 |
| `tests/fixtures/*.html` | 回放用的页面快照 | 每次改版都要补 |
| `tests/unit/test_cnki_*.py` | 断言 | 跟着 fixture 更新 |

`selectors.py` 里的每个键对应页面上一个位置：

```
SEARCH.input / submit          检索输入框与提交按钮
SEARCH.row                    结果行
SEARCH.title_link             行内标题链接（同时给出详情 URL）
SEARCH.authors/source/date    行内作者、刊名、日期
SEARCH.citations/downloads    被引、下载
SEARCH.data                   文献类型单元格
SEARCH.total / page_marker    共找到 N 条、当前页/总页
SEARCH.next_page              下一页
SEARCH.page_size_open/50      每页条数下拉与 50 条选项
SORT.relevance/date/citation  排序列（data-sort=FFD/PT/CF）
EXPERT.page/input/submit      专业检索页 URL、表达式输入框、检索按钮
DETAIL.title/authors/...      详情页各字段容器
SEARCH_READY / DETAIL_READY   "结果/详情已就绪"的判定选择器
```

注意 `SEARCH_READY` 与 `DETAIL_READY` 不是普通选择器：它们是 `wait_for` 的目标，
改错会让整条链路要么等满超时、要么提前读到半渲染页面。

## 3. 新增一个站点版本

```powershell
cd src\scholar_search\channels\cnki
Copy-Item v2026_10 v2027_04 -Recurse
```

然后：

1. 改 `v2027_04/__init__.py` 的 docstring 版本号（可选，但建议）；
2. 按第 2 节表格改 `selectors.py`（先只改这里，跑测试看还剩什么）；
3. 补 fixture（见下节），让 `tests/unit/test_cnki_*.py` 指向新 fixture；
4. 交互流程变了才动 `plan_*.py`；字段来源变了才动 `parse_*.py`；
5. 跑全量测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\mypy.exe src
```

6. 真机验证一次（会消耗配额）：检索、翻页、50 条/页、两种排序、一篇详情、一次导出；
7. 发版本：版本号 + CHANGELOG + NOTICE 同步 → `uv build` → tag。

注册表按版本号排序取最高，所以新目录一进包就是默认版本；旧目录可以留着做回滚，
也可以在下一个版本里删掉。

## 4. 录制与脱敏 fixture

解析逻辑必须有回放测试，禁止"只看线上一眼就改"（硬约束）。抓页面最省事的方式是用本项目
自己的桥，只读、不下载：

```python
from scholar_search.adapters.bridge import BridgeAdapter
from scholar_search.core.contracts import Action

adapter = BridgeAdapter()
moved = adapter.execute(Action("goto", {"url": URL}, timeout_ms=10_000), timeout_ms=10_000)
html = adapter.execute(Action("read_html"), timeout_ms=6_000).data["html"]
open("cnki_search_2027_04.html", "w", encoding="utf-8").write(html)
adapter.close()
```

放进仓库前必须脱敏：

- 删掉 Cookie、`v=` 参数里的真实会话片段、个人检索历史；
- 作者名可以保留（公开题录），但不要把"当前登录用户"信息带进来；
- 检查有没有 `<script>` 里的埋点参数带 token；
- fixture 里不允许出现任何账号、学号、机构 IP。

## 5. 什么时候要抬 `min_core`

只有当渠道用到了**新版本内核才有的 API**（新动作参数、新契约字段、新解析辅助）时才抬
`manifest.json` 的 `min_core`。抬了之后，旧内核会明确拒绝加载该渠道，而不是运行时崩：
`registry.select()` 会抛 `ChannelError: channel 'cnki' requires core >= x.y.z`。

## 6. 兼容性约定

- **只增不改**：新版本目录里可以删选择器，但不要把旧目录改坏——旧目录是回滚路径。
- **动作词汇不动**：改版几乎不需要新动词。如果需要，走 ADR 流程，四处同步
  （`core/params.py`、`core/contracts.py`、宿主、扩展）。
- **限额不动**：改版不能成为放宽频率或页数的理由。
