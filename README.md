# scholar-search · 学术检索

只读的学术题录检索服务。微内核 + 渠道插件：知网是第一个渠道，万方、维普等以后按同一契约接入。

> 独立项目，非官方，与任何数据库运营方无隶属或合作关系。

## 它做什么

- 关键词检索：标题、作者、刊名、年份、被引、下载、链接
- 专业检索式：`SU='IPMC' and KY='驱动器'`，支持 `SU/TI/KY/AU/AF/AB/FT/LY/DOI/CF`
- 翻页：一次最多 3 页
- 单篇详情：摘要、DOI、卷期页、关键词、作者单位
- 导出 RIS / EndNote 题录文本

## 它不做什么

- 不下载 PDF / CAJ，不调用任何下载接口
- 不破解验证码，遇到风控立即停机并提示人工处理
- 不做批量循环抓取，不提供公网服务，不共享账号
- 不实现年份 / 来源 / 排序筛选（传了会明确报错，不会静默忽略）

## 安全边界

- 浏览器动作词汇固定为九个：`goto` `wait_for` `type` `click` `select` `read_html` `read_text` `scroll` `sleep`
- 没有任意 JS 执行，没有文件动作，没有下载动作
- 域名、动词、频率、配额由内核强制，插件只能收紧不能放宽
- 最小间隔 3 秒硬下限，并发 1，单次最多 3 页，每日上限 200 次
- 遇到验证页 / 验证码 / 403 / 登录跳转：终止计划、返回 `blocked`、冷却 24 小时

## 架构

```
MCP 客户端 ──stdio/HTTP──▶ MCP server ──▶ 内核（策略/风控/计划/审计/缓存）
                                              │
                                         渠道插件 cnki/v2026_10
                                              │
                                     桥接适配器 ──TCP──▶ 原生宿主 ──stdio──▶ 扩展 ──▶ 浏览器
```

宿主只做管道转发；扩展只认九个动作；站点知识全部在渠道插件里。换站点 = 加一个版本目录，不改内核。

## 状态

v0.2.0。真机验证过的能力：

| 能力 | 状态 |
|---|---|
| 关键词检索 | 通过（IPMC：595 条） |
| 专业检索式 | 通过（`SU='IPMC' and KY='驱动器'`：57 条） |
| 翻页 1–3 | 通过（第 2 页内容不同） |
| 详情 | 通过（摘要、DOI、作者、单位、关键词） |
| 导出 RIS | 通过 |
| 卷期页 | 通过（力学学报 2022, 54(01): 184-195） |
| 年份/来源/排序筛选 | 未实现（显式报错） |

## 安装与使用

```bash
pip install -e ".[dev]"
scholar-search --help
```

浏览器侧（只需一次）：

```powershell
pwsh native-host/install.ps1
```

然后在 `edge://extensions` 打开开发者模式，加载 `extension/` 目录。

MCP 接入：

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

HTTP 方式见 [docs/integration/dsh.md](docs/integration/dsh.md)。

## 工具

| 工具 | 作用 |
|---|---|
| `search` | 关键词或专业检索式，返回一页题录 |
| `detail` | 读取单篇详情 |
| `export` | 题录转 RIS / EndNote |
| `status` | 渠道、配额、冷却、桥接状态 |

## 目录

```
src/scholar_search/core/       内核：契约、策略、风控、审计、缓存
src/scholar_search/channels/   渠道插件（当前只有 cnki）
src/scholar_search/adapters/   浏览器适配器（bridge / fixture）
native-host/                   原生消息宿主（仅通讯层）
extension/                     浏览器扩展（九个通用动作）
skills/                        给 agent 的技能说明
docs/                          架构、ADR、协议、对照表、故障台账
tests/                         单元 + 契约 + 真机 fixture 回放
```

## 文档

- [架构](docs/architecture.md)
- [渠道契约](docs/channel-contract.md)
- [桥接协议](docs/bridge-protocol.md)
- [借鉴对照表](docs/reference-parity.md)
- [故障台账](docs/incidents.md)
- [ADR 索引](docs/adr/)

## 合规声明

本项目仅用于个人学术研究中的题录检索。使用者应遵守目标站点的服务条款与所在机构的使用规定。项目本身不附带任何数据、凭证或会话材料。

## License

MIT，见 `LICENSE`；第三方参考与商标说明见 `NOTICE`。
