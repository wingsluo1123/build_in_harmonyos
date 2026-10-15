# E429 — Python 适配两个隐蔽坑：`test_requires` 的上下文 & sdist 时间戳归一化

## 错误特征
1. 配方里已经 `self.test_requires("aiohttp/3.14.3")`，但收集依赖 site-packages 时**遍历结果为空**，
   随后跑测试报：
   ```
   ModuleNotFoundError: No module named 'aiohttp'
   ```
2. 上游套件里某个用例报：
   ```
   ValueError: ZIP does not support timestamps before 1980
       in zipfile/__init__.py:  if date_time[0] < 1980: raise ValueError(...)
   ```
   而同一个用例在 git 检出里是**通过**的。

## 触发条件
- 构建系统: 无（纯 Python 包，sdist 安装）
- 阶段: testing（`build()` 内跑上游套件）

## 根因分析
### 坑 1：`test_requires` 落在 **test 上下文**
Conan 2 的 `self.test_requires(...)` 与 `tool_requires` 不同，其依赖在 **test 上下文**下解析。
若像 host 依赖那样写：
```python
for _ref, dep in self.dependencies.items():      # 默认只有 host
    ...
```
或再加 `.build`，**都拿不到 test_requires**（实测：aiohttp 作 test_requires 时，host+build 两次遍历
都是空集合）。必须显式加上 `.test`：
```python
for group in (self.dependencies.host, self.dependencies.build,
              self.dependencies.test):
    ...
```
**衍生坑**：别用"库名子串"匹配 conan 包路径来确认依赖在不在——conan 的包目录名是**截断名**
（`~/.conan2/p/aioht9f1a043272ee1/p/…`，路径里根本没有 `aiohttp`），
`any("aiohttp" in s for s in sites)` 会**假阴性**。正确判据是看**模块目录**：
`os.path.isdir(os.path.join(site, "aiohttp"))`。

### 坑 2：PyPI sdist 把成员时间戳归一化到 **epoch**
不少构建后端（hatchling/uv 等）默认按 `SOURCE_DATE_EPOCH=0` 打包以求可复现 →
sdist 成员的 `mtime` 就是 **0（1970-01-01T00:00Z）**。上游那个用例干的是：
```python
archive = tmp_path / "vendored.zip"
package = pathlib.Path(update_checker.__file__).parent
with zipfile.ZipFile(archive, "w") as zipped:
    for name in ("__init__.py", "core.py"):
        zipped.write(package / name, name)      # ← 取源文件 mtime 当 zip 条目时间
```
`zipfile` 不支持 1980 年之前的时间戳 → 报错。于是"从 sdist 解出来的源码"必挂，
而从 **git 检出/仓库归档**（mtime 正常）跑就通过——这不是上游代码缺陷。

## 解决方案

### 推荐方案
1. **依赖收集**：三上下文都遍历（`.host`/`.build`/`.test`），并**按模块目录判定**依赖是否到位；
   顺带把"是否找到 aiohttp"做成**守卫**（找不到就响亮失败，不默默跑出假结果）。
2. **时间戳坑**：先判定再处置——
   ```bash
   python3 -c "import tarfile;print([(m.name,m.mtime) for m in tarfile.open('<sdist>').getmembers() if m.name.endswith('.py')][:3])"
   # mtime=0 → 被归一化
   ```
   处置优先用**上游跑测试的语义**（上游是在 git 检出里跑的）：把同 tag 的**仓库归档源码**置于
   `PYTHONPATH` 最前（实测 43 passed），并在 `manifest.yaml` / `MANIFEST.yml` / `notes.md` /
   PR 正文**如实披露"被测源码取自仓库归档、与 sdist 同版本同源码"**；**包产物仍由 sdist 源码树打包**。
3. 实测口径要摆出来（本例）：sdist 源码 42 passed / 1 failed（即上述 zip 用例）；仓库归档源码 43 passed。

### 禁止做法
- ❌ 改上游测试（注释掉/放宽断言）来"修"这个用例
- ❌ 偷偷 `os.utime` 伪造文件时间戳而不披露
- ❌ 因为 `import aiohttp` 失败就断言"上游测试跑不了"并跳过整套（那其实是依赖没接上）
- ❌ 别用库名子串匹配 conan 包路径（截断名 → 假阴性）

## 验证
```bash
# 依赖是否真的在路径上
PYTHONPATH=<…> python3 -c "import aiohttp;print(aiohttp.__file__)"
# 时间戳是否被归一化
python3 -c "import tarfile;print([(m.name,m.mtime) for m in tarfile.open('<sdist>').getmembers() if m.name.endswith('.py')][:3])"
# 真跑（期望 43 passed）
PYTHONPATH=<repo-src>:<repo-root>:<test-deps>:<dep sites> python3 -m pytest tests/ -q
```

## 关联条目
- 相关: E429（同一草稿 id 下的其它 Python 测试期条目：sdist 测试落点 / 上游自带 runner /
  离线子集 marker / src 布局与 pytest 插件型 addopts / console_scripts 入口落地）
