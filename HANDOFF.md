# 交接文档 · scholar-search（2026-10-21）

给下一个会话的接手人。先读 `AGENTS.md` 的硬约束，再读本文件。

## 1. 现状一句话

只读的 CNKI 题录检索 MCP 服务，已通过 DSH 的**官方 bundle 方式**注册并在真实会话中验证：
`mcp__scholar-search__search` 返回 `total=150`，工具与浏览器宿主链路正常。

## 2. 代码与版本

| 项 | 值 |
|---|---|
| 仓库 | `D:\Python\DeepSeek\DateWork\scholar-search` |
| 分支 / HEAD | `main` / `f94b417` |
| 最新 tag | `v0.3.13` |
| 已安装 | `C:\Users\xuhui\AppData\Local\scholar-search\installations\0.3.13` |
| Codex 配置 | `C:\Users\xuhui\.codex\config.toml` → 0.3.13 venv |
| 扩展 | 0.3.11 加载的 JS；0.3.12/0.3.13 只有 Python 改动，**无需重载** |

### 未提交的改动（重要）

`git status` 显示两个文件未提交：

- `src/scholar_search/channels/cnki/v2026_10/plan_search.py`
  - `goto` 后新增 `sleep 2500`（等 CNKI 首屏后的二次跳转完成，避免内容脚本被替换导致 `type` 超时）
- `tests/unit/test_cnki_channel.py`
  - 计划动作序列断言加入 `sleep`，索引相应后移

这份工作区代码已经**热更新**到 0.3.13 安装目录，所以线上行为包含该修复，但 tag 里没有。

**接手后第一件事**：把这两个文件提交，发 `0.3.14`（版本号、CHANGELOG、NOTICE 同步），再决定是否部署。

## 3. 已真机验证（2026-10-21）

- 第 1 页 / 第 2 页：`page: 2`，2024/2024/2024 降序
- 专业检索式 `SU='IPMC'`：539 条
- 50 条/页：50 条
- 学位论文详情：`thesis`，RIS `THES`，EndNote `Thesis`
- 排序方向反馈纠正：读 `#orderList` 的 `cur` 类，ASC 才补一次点击
- 风控：无验证码、无 403、无冷却
- 通过 DSH MCP 的真实调用：`search` 成功（total 150）

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

- 日期 `2026-10-21`，已用 191 / 300，剩余 **109**，无冷却。
- 每日 300 个网络动作（ADR 0005）。
- 3000ms 下限 + 0–1.2s 随机抖动（约 10% 额外 2–4s），并发 1。
- `page` 1–3，`limit` 1–50，单计划 ≤40 动作 / 120s。
- 遇验证码/403/登录跳转：立即停、返回 `blocked`、写 24h 冷却；人工完成后用
  `scholar-search reset --confirm` 显式清除，不自动重试。

## 7. 已知问题与排查顺序

### `type failed: bridge.timeout`（已缓解）

现象：`goto`、`wait_for` 成功，`type` 3 秒超时。
原因：CNKI 首屏完成后又跳转一次，旧内容脚本被替换，后台重试耗尽且未回包。
已加 `goto` 后 2.5s 稳定等待。若仍偶发：

1. 看 `audit.jsonl` 确认失败动作；
2. 确认 Edge 只有一个可见窗口、一个 CNKI 标签页，且窗口未最小化；
3. 让用户开一次 CNKI 搜索页再重试；
4. 不要连续重试，不要换 IP，不要延时重试。

### 复制 venv 后 `scholar-search.exe` 指向旧版本

从旧安装目录复制 venv，`Scripts\scholar-search.exe` 仍指向更早版本（例如 0.3.13 目录里跑出 0.3.2）。
0.3.13 已删除该 exe，改用 `Scripts\scholar-search.cmd`（`python -m scholar_search.cli`）。
新部署时照做，或统一用 `python -m`。

### 页面状态导致 `goto` 超时

长时间复用同一个 CNKI 标签页会出现 `goto` 15s 超时。关闭所有 CNKI 标签页或重启 Edge 后恢复。不是代码问题。

## 8. 沙箱里自测（不需要用户点浏览器）

1. 复制状态到工作区 HOME：

```powershell
$lh='D:\Python\DeepSeek\DateWork\tmp\live-home'
Copy-Item 'C:\Users\xuhui\AppData\Local\scholar-search\host\bridge.json' "$lh\host\bridge.json" -Force
Remove-Item "$lh\cache" -Recurse -Force -ErrorAction SilentlyContinue
```

2. 用已安装解释器 + 仓库源码跑：

```powershell
$env:SCHOLAR_SEARCH_HOME=$lh
$env:PYTHONPATH='D:\Python\DeepSeek\DateWork\scholar-search\src'
& 'C:\Users\xuhui\AppData\Local\scholar-search\installations\0.3.13\venv\Scripts\python.exe' -B tmp\accept-live.py
```

3. 跑完把 `$lh\state\quota.json` 复制回 AppData，避免配额分叉。

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

## 11. 待办

- [ ] 提交 `plan_search.py` + 测试改动，发 `0.3.14`
- [ ] 决定是否把 DSH bundle 的 command 路径升级到 0.3.14（会需要一次 DSH 重启/插件重装）
- [ ] 观察 `type` 超时是否还会出现；若出现，优先查标签页是否被冻结/最小化
- [ ] 配额跨天后确认 `quota.json` 的 `day` 字段自动重置
