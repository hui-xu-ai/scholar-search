# scholar-search · 学术检索

只读的学术题录检索服务。微内核 + 渠道插件：知网是第一个渠道，万方、维普等以后按同一契约接入。

> 独立项目，非官方，与任何数据库运营方无隶属或合作关系。

## 它做什么

- 按关键词、年份、来源类别检索，返回结构化题录
- 读取单篇详情：摘要、关键词、DOI、卷期页、作者单位
- 按 ISSN 列出整期目录
- 导出 RIS / EndNote 题录文本

## 它不做什么

- 不下载 PDF / CAJ，不调用任何下载接口
- 不破解验证码，遇到风控立即停机并提示人工处理
- 不做批量循环抓取，不提供公网服务，不共享账号

## 安全边界

- 浏览器动作词汇固定为九个：`goto` `wait_for` `type` `click` `select` `read_html` `read_text` `scroll` `sleep`
- 没有任意 JS 执行，没有文件动作，没有下载动作
- 域名、动词、频率、配额由内核强制，插件只能收紧不能放宽
- 最小间隔 3 秒硬下限，并发 1，单次最多 3 页，每日上限 200 次

## 状态

v0.1.0 开发中。当前处于 P0（骨架与契约冻结），尚未实现检索逻辑。

## 安装与使用

```bash
pip install -e ".[dev]"
scholar-search --help
```

MCP 接入见 `docs/integration/`。

## 目录

```
src/scholar_search/core/       内核：契约、策略、风控、审计、缓存
src/scholar_search/channels/   渠道插件（当前只有 cnki）
src/scholar_search/adapters/   浏览器适配器（bridge / fixture / cdp）
native-host/                   原生消息宿主（仅通讯层）
extension/                     浏览器扩展（九个通用动作）
```

## 合规声明

本项目仅用于个人学术研究中的题录检索。使用者应遵守目标站点的服务条款与所在机构的使用规定。项目本身不附带任何数据、凭证或会话材料。

## License

MIT，见 `LICENSE`；第三方参考与商标说明见 `NOTICE`。
