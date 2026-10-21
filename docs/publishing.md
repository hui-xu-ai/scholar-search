# 发布到 GitHub

仓库目前**没有配置远程**，所有 tag 只在本地。本文是从"本地仓库"到"GitHub 上有 release"的
完整操作，以及发布前的检查清单。

## 1. 发布前检查

```powershell
cd D:\Python\DeepSeek\DateWork\scholar-search

# 工作区必须干净
git status --short

# 不能有构建产物、虚拟环境、运行期数据入库
git ls-files | Select-String -Pattern '^(dist/|\.venv/|tmp/)'     # 应为空

# 三处版本号一致
Select-String -Path pyproject.toml,src\scholar_search\__init__.py -Pattern '0\.3\.'
Select-String -Path NOTICE -Pattern '^Version:'
Select-String -Path extension\manifest.json -Pattern '"version"'

# 全绿再发
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\mypy.exe src
```

还要确认：

- `.gitignore` 覆盖 `dist/`、`.venv/`、`*.log`、`native-host/` 下的生成物
  （`scholar-host.exe`、`python-path.txt`、`com.scholar.search.json`）；
- 没有任何真实 Cookie、账号、会话参数、个人检索记录混进 `tests/fixtures/`；
- `README.md` 里的版本号与 `pyproject.toml` 一致。

## 2. 首次推送

```powershell
git remote add origin git@github.com:<你的账号>/scholar-search.git
git branch -M main
git push -u origin main
git push origin --tags
```

仓库里没有任何凭证，公开或私有都可以。`HANDOFF.md`（本机路径、个人排障笔记）已经
`git rm --cached` 并写进 `.gitignore`，之后的提交不会再带它；但**历史提交里仍然有**，
如果要彻底清掉需要重写历史（`git filter-repo --path HANDOFF.md --invert-paths`），
公开前可以自己权衡。

## 3. CI 与发布流水线

| 工作流 | 触发 | 做什么 |
|---|---|---|
| `.github/workflows/ci.yml` | push 到 `main`、所有 PR | Ubuntu + Windows × Python 3.11/3.12：`ruff check .`、`mypy src`、`pytest -m "not e2e"` |
| `.github/workflows/release.yml` | 推送 `v*` tag | 构建 wheel + sdist，校验 tag 与 `__version__` 一致，创建 GitHub Release 并附产物 |

`release.yml` 里的版本校验会拦下"tag 打了但版本号没改"：

```python
tag = github.ref_name.lstrip("v")
version = re.search(r'__version__ = "([^"]+)"', ...)
sys.exit(0 if tag == version else 1)
```

所以发布顺序必须是：改版本号 → 提交 → 打 tag → 推送 tag。

### tag 与 main 一起推时的时序坑

首次建库时实测：先 `git push -u origin main`、紧接着 `git push origin --tags`，
25 个 tag 全部推上去了，但**一个 release 工作流都没触发**。原因是 GitHub 处理 tag 事件时，
`release.yml` 在默认分支上还没生效（工作流文件刚随 main 推上去几秒）。

处理：单独重推需要发版的那个 tag 即可——

```powershell
git push origin :refs/tags/v0.3.18    # 删远端 tag
git push origin v0.3.18               # 重新推，触发 release
```

不需要（也不建议）把历史 tag 挨个重推，那会一次生成几十个 release。

### 补 tag 但不想重新发版

场景：手滑删掉了某个旧版本的 release（GitHub UI 里"删除 release"还有个"同时删除 tag"的勾选项，
很容易一起删掉），想把 tag 补回来，但不希望再生成一个 release。

直接 `git push origin v0.3.17` 会触发 `release.yml`，于是又造一个新 release。正确做法是先停工作流：

```powershell
# 1) 禁用 release 工作流（需要 token 有 actions:write）
gh api -X PUT repos/<owner>/<repo>/actions/workflows/release.yml/disable

# 2) 补 tag
git push origin v0.3.17

# 3) 确认没有新的 release 运行，再启用
gh api -X PUT repos/<owner>/<repo>/actions/workflows/release.yml/enable
```

实测（2026-10-21）：补完 `v0.3.17` 后 tag 指向原提交，release 仍然只有 `v0.3.18` 一个。

顺带一句：**tag 不占存储**，只删 release 就够了；每个 release 的产物才是空间大头。

## 4. 发布一个新版本（标准动作）

```powershell
# 1) 同步四处版本号 + CHANGELOG + NOTICE
#    pyproject.toml / src/scholar_search/__init__.py / extension/manifest.json / NOTICE

# 2) 提交
git add -A
git commit -m "fix: <一句话> (0.3.18)"

# 3) 构建并核对产物
uv build
python -c "import zipfile;print(zipfile.ZipFile('dist/scholar_search-0.3.18-py3-none-any.whl').namelist()[:3])"

# 4) 打 tag 并推送
git tag -a v0.3.18 -m "scholar-search 0.3.18"
git push origin main
git push origin v0.3.18
```

推送 tag 后看 Actions 是否变绿；Release 里应出现
`scholar_search-0.3.18-py3-none-any.whl` 与 `.tar.gz`。

## 5. 分支保护与合并

建议在 GitHub 上对 `main` 开启：

- 要求 PR（不能直接 push）；
- 要求 CI 通过（`test` 两个平台四个组合）；
- 禁止 force push。

本地开发用短分支 + `gh pr create`，或直接在 `main` 上做小改动（个人项目可接受，但 CI 必须绿）。

## 6. 要不要发 PyPI

项目现在只出 GitHub Release 的 wheel，没有配 `pypi` 的 trusted publishing。要发 PyPI 的话：

1. 在 `pyproject.toml` 里补 `[project.urls]` 与 classifiers（已有部分）；
2. 在 PyPI 上建项目并配置 trusted publisher 指向本仓库的 `release.yml`；
3. 在 `release.yml` 里加一步 `pypa/gh-action-pypi-publish`。

没做这一步之前，用户安装靠 `pip install <wheel 路径>`，README 也是这么写的。

## 7. 不要提交的东西

- `HANDOFF.md`（本机路径、个人排障笔记；已加入 `.gitignore`）
- `dist/`、`.venv/`、`browser/`（资源构建产物）
- `native-host/python-path.txt`、`com.scholar.search.json`、`scholar-host.exe`
- 任何 `%LOCALAPPDATA%\scholar-search` 下的运行期文件
