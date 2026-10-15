# zenmap 7.99 适配笔记（HarmonyOS PC / aarch64）

## 基本信息

| 项 | 值 |
|----|----|
| 软件 | zenmap（Nmap 图形前端 / 结果查看器） |
| 版本 | 7.99 |
| 上游 | https://nmap.org/zenmap/（源码随 Nmap 发布，无独立 tarball） |
| 源码包 | `https://github.com/nmap/nmap/archive/deb076224e9f138ea29fa4823bcce0030301dc54.tar.gz`（sha256 `640ff059…76e8c`） |
| 语言 | Python（纯 Python，112 个 `.py`；无 C/C++ 编译） |
| 构建系统 | setuptools / PEP 517（upstream `pyproject.toml`） |
| 运行时依赖 | `nmap/7.99`（OHOS 适配版扫描器） |
| 适配路径 | 路径 A（基础适配） |
| 编译状态 | built（conan-verify 通过；制品在 PR 合并后由 release 流水线 upload） |

## 适配要点

1. **zenmap 没有独立源码包**：它随 Nmap 源码树发布（`nmap-7.99/zenmap/`），
   upstream 的 `Makefile` 也是用 `$(PYTHON) -m build $(ZENMAPDIR)/` + `pip install`
   来构建安装。因此 `conandata.yml` 指向 Nmap 官方源码树，配方只打包 `zenmap/` 子树。

   **源码主机选择（重要）**：官方 release tarball 在 `nmap.org/dist/`，但 **CI worker
   访问不到 nmap.org**——连续 3 次 PR 构建（#88152/#90209/#90255，worker CI-041/030/011）
   均以 `源码下载超时 https://nmap.org/dist/nmap-7.99.tar.bz2` 失败（CI 侧诊断为
   "Worker 网络受限"）。而官方仓库 `nmap/nmap` 经 CI 的 github 镜像通道可达（实测
   conan 经 `gh-proxy.com` 成功下载 16.7MB），故改用**官方仓库归档并 pin 到产出 7.99
   release 的上游 commit**：

   - commit `deb076224e9f138ea29fa4823bcce0030301dc54`
     （"Reintegrate Nmap 7.99 release branch"，2026-03-27；其后触及 `nmap.h` 的
     commit `6dac43b5d892` 为 `Bump version to 7.99SVN`）；
   - **本地实证**：该 commit 的 `zenmap/` 子树与官方 `nmap-7.99.tar.bz2` 的
     `zenmap/` 子树 `diff -rq` **零差异**（逐字节一致）。
   - 注意**不要**用仓库里唯一的 tag `v7.991`：它是 7.99 之后 4 个多月的开发快照
     （2026-08），相对 7.99 release 有 35 个文件差异（含真实代码改动，如
     `radialnet` 的 `Gtk.Table` → `Gtk.Grid` 迁移），用它会与"7.99"版本号不符。

   > 同仓 `archives/n/nmap/7.99` 的 conandata 仍用 nmap.org URL——它是在当前 CI
   > 网络限制生效之前构建并已发布到制品仓的；本次适配实测该主机在 CI 上不可达。

   **唯一的补丁（打包层，非源码）**：CI worker 与 OHOS Python 都**没有 gettext 的
   `msgfmt`**，`setuptools-gettext` 后端在编译 `.po`→`.mo` 时报
   `error: command 'msgfmt' failed: No such file or directory`，导致 wheel 构建失败
   （CI 构建 #90318 实测）。`.mo` 只服务 GUI 翻译，而 GUI 需要 OHOS 上不可用的 GTK3，
   故用补丁 `0001-pyproject-drop-gettext-msgfmt.patch` 去掉 gettext 构建步骤
   （移除 `setuptools-gettext` 构建依赖与 `[tool.setuptools-gettext]` 段），
   `.po` 源文件原样保留在源码中。副作用：包内不再含 `share/locale/*/LC_MESSAGES/*.mo`。

2. **纯 Python → 用 Python 的方式安装**：`pip wheel . --no-deps`（PEP 517，隔离构建
   装上 upstream 声明的 `setuptools` 后端），再用
   `pip install <wheel> --target <stage> --no-deps --no-compile` 展开 wheel
   （`.data` 目录由 pip 正确落位）。未引入任何 C/C++ 依赖。
   （upstream 声明的 `setuptools-gettext` 后端已由 `patches/0001-*.patch` 移除，
   原因见上文"源码主机选择"末尾：OHOS/CI 无 `msgfmt`。）

3. **`nmap/7.99` 作为 run 依赖**：zenmap 运行时要调用 `nmap` 可执行文件。
   Conan 会把 `application` 类型的 требует自动提升为 `run=True`，因此
   `self.requires("nmap/7.99")` 即可，消费者 `conan install` 后 `PATH` 里就有
   OHOS 版 nmap —— 由 `test_package` 实际断言（见下）。

4. **`bin/zenmap` 的 shebang 改写**：pip 生成的 console script 首行是构建期
   解释器的绝对路径，未必存在于目标设备；打包时统一改写为
   `#!/usr/bin/env python3`。

5. **移除悬空的 `bin/ndiff`**：upstream `zenmap/pyproject.toml` 里同时声明了
   `py-modules = ["ndiff"]` 与 `[project.scripts] ndiff`，但 ndiff 早已是**独立
   上游包**（`nmap-7.99/ndiff/` 自带 `pyproject.toml`，由 `make build-ndiff` 单独
   构建），zenmap 目录里没有 `ndiff` 模块，wheel 里也不含它，生成的 `bin/ndiff`
   是悬空脚本。打包时删除，未修改 upstream 任何源文件。

## GTK3 / PyGObject 平台结论（关键）

`zenmapGUI` 与 `radialnet` 在 **导入期** 即 `import gi`：

- `zenmapGUI/higwidgets/gtkutils.py`：`import gi` → `gi.require_version("Gtk", "3.0")`
- `zenmapCore/NetworkInventory.py`：`from zenmapGUI.SearchGUI import SearchParser`

制品仓里 `pygobject/3.58.0`、`gtk/3.24.38`、`gobject-introspection/1.78.1` 都存在，
但**当前 OHOS 上无法消费**，实测两点：

| 阻塞点 | 证据 |
|--------|------|
| gi 扩展名不匹配 | pygobject 包内为 `gi/_gi.cpython-312-aarch64-linux-ohos.so`，而解释器 `_imp.extension_suffixes()` 只有 `['.cpython-312.so', '.abi3.so', '.so']` → `import gi` 报 `ImportError: cannot import name '_gi'` |
| 无 typelib | `find $CONAN_HOME -name '*.typelib'` 为 0；gtk 包只有 `libgtk-3.so`，无 `Gtk-3.0.typelib`；gobject-introspection 包只有 girepository 工具，无 `.gir`/`.typelib` |

结论：即便声明 `pygobject`/`gtk` 依赖，`import gi` 依然失败，等于引入一整条
**无实际用途的 C/C++ 依赖链**——正是任务要求避免的。故 GTK3 作为**平台运行期
前置条件**记录在 `README.md` / `notes.md`，不写进 `requirements()`。

纯 Python 的 `zenmapCore`（选项解析、nmap XML 解析、结果搜索/对比、配置）在
鸿蒙上完全可用，本包安装并由测试覆盖。

## 上游测试

upstream 的测试用例内嵌在各模块里，用 `zenmap/test/run_tests.py`（对 `*.py` 做
`unittest` discovery）驱动。7.99 共 **31** 个用例：

| 模块 | 用例类 | 数量 | 本环境 |
|------|--------|------|--------|
| `zenmapCore.NmapOptions` | `NmapOptionsTest` 17 + `SplitQuotedTest` 3 | 20 | 全部执行 ✅ |
| `zenmapCore.SearchResult` | `SearchResultTest` | 6 | 全部执行 ✅ |
| `zenmapCore.StringPool` | `StringPoolTest` | 1 | 全部执行 ✅ |
| `zenmapCore.NetworkInventory` | `NetworkInventoryTest` 2 + `FilteredNetworkInventoryTest` 1 + `PortChangeTest` 1 | 4 | ⛔ GTK 门控（见上） |

`NmapOptionsTest` 中 `test_default_executable` 有两个同名定义（后定义覆盖前者），
按 Python 语义实际收集 17 个。`build()` 运行 27 个（0 失败 0 错误），并**显式打印**
GTK 门控模块的 SKIP 原因（`SKIP(gtk) zenmapCore.NetworkInventory: …`），不做静默丢弃。

## 踩坑记录

本适配无需给 upstream 打任何补丁（`patches: []`）：纯 Python 代码在 OHOS CPython
上原样运行。构建/测试期注意：

| # | 问题 | 处理 |
|---|------|------|
| 1 | E002：`/tmp` 只读 | `build()` 内将 `TMPDIR` 指向 build folder 子目录；不写任何共享路径（R49） |
| 2 | 隔离构建需要网络装后端 | 主路径 `pip wheel`（隔离）；失败时回退 `--no-build-isolation`（用解释器自带 setuptools），并在输出中告警 |
| 2b | CI/OHOS 无 gettext `msgfmt` → `setuptools-gettext` 编译 `.mo` 失败（CI #90318） | 打包层补丁 `0001-pyproject-drop-gettext-msgfmt.patch` 去掉 gettext 构建步骤（`.mo` 仅服务 GUI 翻译，GUI 在 OHOS 无 GTK3 不可用） |
| 3 | `search()` 参数语义 | upstream `SearchResult.search(**kwargs)` 的值必须是**列表**（逐元素匹配），传裸字符串会被按字符迭代——自研测试里已按列表传参 |
| 4 | `StringPool.unique` | 它是 memo dict 的 `__getitem__`，不是去重函数；断言用 `assertIs` 判断同值同对象 |

## 产物

```
bin/zenmap                      # GUI 入口（#!/usr/bin/env python3）
zenmapCore/ zenmapGUI/ radialnet/
share/                          # 不含 .mo：gettext 步骤已由 patches/0001-*.patch 移除（OHOS 无 msgfmt）
zenmap-7.99.dist-info/
licenses/{LICENSE,COPYING_HIGWIDGETS}
```
---

**编译结束**: 2026-10-13 23:49
**最终状态**: built（conan-verify 通过；制品在 PR 合并后由 release 流水线 upload）
