# Zotero 接入（手动导入，无自动化）

**本项目不提供把题录写入 Zotero 的功能，也不打算提供。**
`export` 只返回一段纯文本（RIS 或 EndNote），把它存成文件、由你自己在 Zotero 里导入。
原因是法律与责任边界，见 [ADR 0006](../adr/0006-no-third-party-ingest.md)。

下面是从检索到入库的完整手动流程，全部动作都由你完成。

## 1. 拿到 RIS 文本

在 MCP 客户端里，把 `search` 或 `detail` 的结果交给 `export`：

```jsonc
// 工具：export
{
  "format": "ris",
  "records": [ /* search 返回的 records，或 detail 返回的单条记录 */ ]
}
```

返回示例（节选）：

```
TY  - JOUR
TI  - 钙钛矿太阳能电池:光伏领域的新希望
AU  - 魏静
AU  - 赵清
T2  - 中国科学:技术科学
PY  - 2014
VL  - 44
IS  - 08
SP  - 801
EP  - 821
AB  - 2013年6月以来,…
KW  - 钙钛矿基太阳能电池
UR  - https://kns.cnki.net/kcms2/article/abstract?v=…
ER  -
```

## 2. 保存成文件

- 文件名任意，扩展名必须是 **`.ris`**（Zotero 靠扩展名识别，不能是 `.txt`）；
- 编码必须 **UTF-8**。Windows 上用记事本另存时选 "UTF-8"，否则中文会变乱码；
- 一次可以放多条，每条以 `ER  - ` 结尾，Zotero 会逐条导入。

PowerShell 里从剪贴板存成文件：

```powershell
Get-Clipboard -Raw | Set-Content -Path .\refs.ris -Encoding utf8
```

## 3. 在 Zotero 里导入

1. Zotero → 菜单 **文件 → 导入…**（File → Import…）；
2. 选 **一个文件**，指向刚才的 `.ris`；
3. 勾选 **将导入的条目放入新分类**（或选已有分类）；
4. 关于重复条目：如果库里已有同一 DOI/标题，选 **不要导入重复条目**；
5. 完成。

导入后建议抽查两条：类型是否正确（期刊 / 学位论文 / 图书 / 报纸）、页码是否落在
`页码` 字段而不是塞进 `卷`。

## 4. 类型映射

导出时的 `TY` 来自页面给出的文献类型，不是猜的：

| 页面类型 | `doc_type` | RIS `TY` | Zotero 结果 |
|---|---|---|---|
| 期刊 / 期刊论文 / 学术期刊 | `journal` | `JOUR` | 期刊文章 |
| 硕士 / 博士 / 学位论文 | `thesis` | `THES` | 学位论文 |
| 会议 / 会议论文 | `conference` | `CPAPER` | 会议论文 |
| 报纸 | `newspaper` | `NEWS` | 报纸文章 |
| 图书 / 专著 | `book` | `BOOK` | 图书 |
| 专利 / 标准 / 年鉴 / 成果 | `patent` / `standard` / `yearbook` / `achievement` | `PAT` / `STAND` / `BOOK` / `GEN` | 对应类型 |
| 无法识别 | `None` | `GEN` + `N1  - document type not reported by source` | 通用条目 |

出现 `GEN` 说明页面上的类型词没有进规范表。这不会伪造类型，但会丢信息；
遇到可以提 issue，附上页面上的类型原文。

## 5. EndNote 与其他软件

`export` 的 `format` 改成 `endnote` 会输出 EndNote 标签格式（`%0` `%T` `%A` `%J` `%D` …），
存成 `.enw` 即可双击导入 EndNote；其他管理器（Mendeley、Papers、JabRef）都支持 RIS，
优先用 `format: "ris"`。

## 6. 批量与配额

- `search` 一次最多 50 条（`limit` 50，且只返回一页）；
- 每多拿一页就多花 3 个网络动作（翻页还会额外增加点击），日上限 300；
- 合理做法：先在客户端里筛掉明显无关的，再 `export` 剩下的，而不是"先抓 150 条回来慢慢挑"。

## 7. 明确不做的事

- 不调用 Zotero 的本地连接器端点（`http://127.0.0.1:23119`）或 Web API；
- 不读写 `zotero.sqlite`、`.enl`、Mendeley 库；
- 不生成"一键入库"脚本、插件或 agent 技能。

如果你的工作流需要自动化，正确的位置是**你自己**在 Zotero 侧写脚本消费 RIS 文件，
本项目只负责产出文本。
