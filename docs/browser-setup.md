# 浏览器环境与扩展

本项目不接管你现有的浏览器配置。推荐**单独开一个 Edge 环境**专供检索：
互不干扰、卸载方便、出问题直接删目录。

## 1. 为什么要单独的环境

- 扩展只在 `https://*.cnki.net/*` 上注入内容脚本，但仍会占用扩展位；
- 宿主的注册表项是**按扩展 ID** 绑定的，独立环境方便确认是哪一个扩展在连；
- 检索要求"只留一个可见窗口、一个 CNKI 标签页"，专用环境更容易保持这个状态；
- 出问题时删掉整个用户数据目录即可，不影响日常浏览器。

## 2. 新建一个独立 Edge 环境

Edge 支持用 `--user-data-dir` 指定独立的用户数据目录：

```powershell
$profile = "$env:LOCALAPPDATA\scholar-search\edge-profile"
New-Item -ItemType Directory -Force $profile | Out-Null
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" `
    --user-data-dir="$profile" `
    --no-first-run `
    --no-default-browser-check
```

这会打开一个全新的、与日常浏览器隔离的 Edge 实例。建议给它建个桌面快捷方式，
以后都从这里进。Edge 装在哪可以用 `(Get-Command msedge).Source` 查。

用 Chrome 也一样，把 `msedge.exe` 换成 `chrome.exe`；宿主注册脚本会同时写
Edge 和 Chrome 两处的注册表项。

## 3. 安装扩展

1. 在新环境里打开 `edge://extensions`；
2. 打开左下角（或右侧）的**开发者模式**；
3. 点**加载解压缩的扩展**，选择：
   - 部署树：`%LOCALAPPDATA%\scholar-search\installations\<版本>\browser\extension`
   - 源码：`<仓库>\extension`
4. 记下扩展卡片上的 **ID**。

### 扩展 ID 是固定的

`extension/manifest.json` 里带一个 `key` 字段，Chromium 用它推导扩展 ID。
所以无论在哪台机器、哪个 profile 里加载这个目录，ID 恒为：

```
gmaimbocfjkolcpljeekjcomakipoaph
```

`install.ps1` 的 `-ExtensionId` 默认值就是这个，多数情况不用传。

**如果你改了 `key`**（比如要发布到商店），ID 会变，必须显式注册：

```powershell
pwsh .\browser\native-host\install.ps1 `
     -Python "C:\path\to\venv\Scripts\python.exe" `
     -ExtensionId "你的新扩展ID"
```

ID 不匹配的表现：扩展连不上宿主，`scholar-search status` 一直 `bridge_ready: false`，
`host/logs/host.log` 里没有新的 `start`。

## 4. 注册原生宿主

```powershell
# 源码安装
pwsh .\native-host\install.ps1 -Python .\.venv\Scripts\python.exe

# 部署树
pwsh "$env:LOCALAPPDATA\scholar-search\installations\0.3.17\browser\native-host\install.ps1" `
     -Python "$env:LOCALAPPDATA\scholar-search\installations\0.3.17\venv\Scripts\python.exe"
```

脚本做四件事：

1. 编译 `scholar-host.exe`（若不存在，用系统自带的 `csc.exe`）；
2. 写 `python-path.txt`（宿主启动哪个解释器）与 `runtime-home.txt`；
3. 写 `com.scholar.search.json` 并注册到 `HKCU\Software\Microsoft\Edge\NativeMessagingHosts\`
   与 `HKCU\Software\Google\Chrome\NativeMessagingHosts\`，**不需要管理员权限**；
4. 把 `%LOCALAPPDATA%\scholar-search\host` 标为低完整性可写——浏览器以低完整性启动宿主，
   不标的话宿主写不了端点文件。

## 5. 验证

```powershell
scholar-search status
```

期望看到：

```json
{
  "channels": ["cnki"],
  "cooldown_until": null,
  "quota_remaining": 300,
  "bridge_ready": true
}
```

`bridge_ready: true` 说明：扩展已连上宿主，宿主已把端点写进 `host/bridge.json`，
适配器能 ping 通。此时可以在浏览器里开一个知网页面，然后从 MCP 客户端调 `search`。

## 6. 运行时的硬性要求

这几条不是建议，是会让检索失败的前提：

| 要求 | 原因 |
|---|---|
| **只留一个可见的浏览器窗口** | `goto` 作用于"最后聚焦窗口的活动标签页"，多窗口会导航错标签 |
| **窗口不要最小化，尽量在前台** | 非前台时浏览器把定时器按整秒分桶，暂停会迟到；隐藏过久节流更狠 |
| **只留一个 CNKI 标签页** | 长期复用会累积页面状态，`goto` 容易 15s 超时 |
| **代理要对 cnki.net 直连** | 否则 TLS 被中间人换证，页面变"隐私错误"，动作全部 `content_not_ready` |

前两条的排障细节见 [运维手册](operations.md#7-排障)。

## 7. 卸载

```powershell
pwsh .\browser\native-host\install.ps1 -Uninstall      # 删注册表项、清单、launcher
```

然后在 `edge://extensions` 里移除扩展，最后删掉用户数据目录
`%LOCALAPPDATA%\scholar-search\edge-profile` 与（可选的）整个 `scholar-search` 运行目录。
