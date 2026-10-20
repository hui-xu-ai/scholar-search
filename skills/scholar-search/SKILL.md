---
name: scholar-search
description: 通过 scholar-search MCP 服务检索中文文献题录（知网渠道）。支持关键词检索、专业检索式、最多 3 页翻页；只返回题录，不下载全文。
---

# 文献检索

## 何时使用

- 用户要按主题、篇名、作者、刊名找中文论文；
- 需要一页题录（标题、作者、刊名、年份、被引、下载、链接）；
- 需要把检索结果交给后续的详情或导出技能。

## 硬约束

1. **只读**：不请求、不调用任何 PDF/CAJ 下载。
2. **遇阻即停**：返回 `status: blocked` 时立即停止，把 `signal` 和 `cooldown_until` 原样告诉用户，禁止重试、禁止换关键词绕开。
3. **量**：单次 ≤3 页，`limit` 1–50，两次调用之间不要连续轰炸；日上限 200 次由内核强制。
4. **不猜结果**：只转述工具返回的字段，不补全、不虚构作者或年份。

## 调用

工具：`search`

```json
{"query": "IPMC", "limit": 20, "page": 1}
```

### 关键词检索

`query` 是普通词组时走一站式检索。适合“大致找找”。

### 专业检索式

`query` 里出现 `字段=` 或 `字段%` 时自动切到专业检索页。可显著降低噪声：

```
SU='IPMC' and KY='驱动器'
SU='软体机器人' and AU='王'
TI='离子聚合物' and LY='复合材料学报'
```

可用字段：`SU` 主题、`TI` 篇名、`KY` 关键词、`AU` 作者、`AF` 单位、`AB` 摘要、`FT` 全文、`LY` 来源、`DOI`、`CF` 被引。

布尔运算用 `and` / `or` / `not`，括号可分组。

## 返回

```json
{
  "total": 595,
  "page": 1,
  "page_count": 30,
  "records": [
    {
      "title": "…",
      "authors": ["…"],
      "source": "复合材料学报",
      "year": 2026,
      "citations": null,
      "downloads": 22,
      "url": "https://kns.cnki.net/kcms2/article/abstract?v=…"
    }
  ]
}
```

检索结果**不含摘要和 DOI**；需要时把 `url` 交给 `scholar-detail`。

## 异常

- `blocked`：风控或验证页，停止。
- `PolicyError`：参数越界（如 `page` > 3、用了未实现的 `year_from`）。
- `ParseError`：页面结构变化，报告并停止，不要重试同一请求。

## 不要做的

- 不要用循环把同一关键词翻很多页；
- 不要为了“多拿点数据”把 `limit` 拉到 50 再本地截断；
- 不要把 `blocked` 解释成“稍后再试”。
