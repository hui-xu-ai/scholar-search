# 文溯插件市场索引

一份 format 1 的 DSH 插件市场索引，只收录 `hui-xu-ai` 发布的组合包。

## 添加索引源

在 DSH 里打开 **插件 → 实验性插件 → 更多 → 自定义插件市场**，再进 **发现 → 添加索引源**，粘贴：

```text
https://hui-xu-ai.github.io/wensu/market/index.json
```

GitHub Pages 还没开启时，可以先用 raw 地址（同样满足 https、无重定向）：

```text
https://raw.githubusercontent.com/hui-xu-ai/wensu/main/docs/market/index.json
```

## 收录内容

| 包 | 说明 |
|---|---|
| `@hui-xu-ai/dsh-wensu` | 文溯 · 知网文献检索 MCP |

## 维护

- 版本号、`publishTimestamp`（Unix 秒）与 npm 上的发布记录保持一致；
- 发新版本时，在 `versions` 数组里加一条，并同步 `publishTimestamp`；
- `icon` 使用相对路径，索引本身和 `icons/` 一起发布即可。
