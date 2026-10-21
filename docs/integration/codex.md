# Codex / MCP 客户端接入

本文件说明如何把 scholar-search 作为 MCP 服务接入 Codex 类客户端。目标是最小权限、
显式工具发现、无 MCP 时停止，而不是绕过风控或改用脚本直连站点。

## 1. 安装

源码安装：

```bash
pip install -e ".[dev]"
```

发行包安装：

```bash
pip install scholar_search-0.3.2-py3-none-any.whl
```

发行包自带浏览器资源。安装后先导出：

```powershell
scholar-search assets --target .\browser
pwsh .\browser\native-host\install.ps1
```

`assets` 默认拒绝覆盖已有目录；升级时显式加 `--force`。

## 2. MCP 配置模板

stdio（推荐）：

```json
{
  "mcpServers": {
    "scholar-search": {
      "command": "scholar-search",
      "args": ["serve", "--transport", "stdio"],
      "env": {
        "SCHOLAR_SEARCH_HOME": "%LOCALAPPDATA%\\scholar-search"
      }
    }
  }
}
```

HTTP（仅本机，需 bearer token）：

```json
{
  "mcpServers": {
    "scholar-search": {
      "url": "http://127.0.0.1:8765/mcp",
      "headers": { "Authorization": "Bearer <token>" }
    }
  }
}
```

token 在 `%LOCALAPPDATA%\scholar-search\http-token`。

## 3. 工具发现与依赖

连接后应先调用 `status`，确认：

- `channels` 含 `cnki`；
- `bridge_ready` 为 `true`（表示至少一个宿主回应 ping，而不只是端点文件存在）；
- `cooldown_until` 为 `null`。

可用工具只有四个：`search`、`detail`、`export`、`status`。客户端发现的集合必须与
`schemas/tools.json` 一致；多出或缺失都按安装错误处理。

运行依赖：`mcp>=1.20`、`beautifulsoup4`、`lxml`、`uvicorn`。没有浏览器侧宿主与扩展时，
MCP 服务可以启动，但 `search`/`detail` 会返回桥接错误。

## 4. 无 MCP / 工具不可用时的行为

以下情况必须停止并把原因告诉用户，不得改用脚本、curl 或直接访问站点：

- 客户端无法启动 MCP 进程；
- 工具列表为空或缺少 `search`；
- `status.bridge_ready` 为 `false`；
- 任意工具返回 `blocked`。

`blocked` 表示风控或验证页；24 小时冷却由内核持久化，不要换关键词、换实例或换客户端
绕过。

## 5. 技能文件

`skills/` 下三份 `SKILL.md` 可直接复制到客户端的技能目录：

- `scholar-search`：检索与专业检索式；
- `scholar-detail`：单篇详情；
- `scholar-export`：RIS/EndNote 题录。

技能中的约束与服务端一致：只读、单次一页、逐年筛选只作用当前页、遇阻即停。

## 6. 自定义 HOME

浏览器启动的宿主无法继承 shell 环境变量，因此 `install.ps1` 会把
`SCHOLAR_SEARCH_HOME` 写入 `native-host/runtime-home.txt`，宿主启动时读取该文件。
MCP 客户端一侧用 `env.SCHOLAR_SEARCH_HOME` 指向同一目录，两边才会共享配额、冷却与
桥接端点。
