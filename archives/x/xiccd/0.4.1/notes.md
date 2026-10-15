# xiccd 0.4.1 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am，根 Makefile.am 直接编译 src/*.c，7 个源文件）
- 编译日期: 2026-10-15
- 编译器: clang / clang++（OHOS 设备原生工具链，profile `ci/conan/profiles/ohos-aarch64`）
- 目标平台: OHOS / aarch64-linux-ohos
- 状态: built

## 上游测试清点（R51 三步法）

**① 清点上游测试**

| 检查项 | 结果 |
|---|---|
| `tests/` / `test/` / `check/` 目录 | 无 |
| `configure.ac` 中 `AC_CONFIG_TESTDIR` | 无 |
| `configure.ac` / `Makefile.am` 中 `TESTS` / `check_PROGRAMS` 注册 | 无 |
| `make check` | 无实际动作（automake 生成 check/check-am 目标，但无 TESTS/check_PROGRAMS 注册，目标内为空） |

**② 可运行环境实测**：上游 0 个测试用例，CI/W3 内无法运行不存在的套件。
**③ 适配侧补齐**：`test_package/test_xiccd.sh` 补 3 条断言，全部**实跑** `bin/xiccd`（非空壳，R34）：

| # | 断言 | 期望 |
|---|---|---|
| 1 | `xiccd -V` | rc=0 且输出含版本串 `0.4.1`（回归补丁 0001 的 AC_INIT 固化） |
| 2 | `xiccd --help` | rc=0 且输出含 usage |
| 3 | `xiccd --nonexistent-flag` | rc≠0（GLib 选项解析错误路径） |

**通过率 3/3**（`ALL CHECKS PASSED`）。

> 守护主逻辑（RandR 输出变化 → colord D-Bus 推送 ICC）需要真实 X display 与 colord 服务，CI 无 display，故测试上限为二进制实调用级——与 xsel/1.2.1 等同型 X11 命令行工具一致。

## 编译步骤
1. `source()` 取官方 tag 归档（`v0.4.1`），sha256 校验通过；tarball **不含预生成 configure**（autoreconf 产物不进版本库）。
2. `build()` 先 `autoreconf -fi` 自举，automake/libtool 来自 `tool_requires`（真机自带版本损坏，见问题 1）。
3. `ACLOCAL_PATH` 指向 pkg-config 的 `share/aclocal`，使 `pkg.m4` 可被 aclocal 找到（四个 `PKG_CHECK_MODULES` 宏的来源）。
4. `configure` 前作用域注入 `PKG_CONFIG_PATH`（generators 目录 + 各依赖 `lib/pkgconfig`），四个模块全部解析成功：x11 / xrandr≥1.3 / glib-2.0≥2.36 / colord≥1.0.2。
5. 改写生成的 `configure`：`umask 077`→`022`（E114）、`ac_pwd`/`pwd` 判定补 `$PWD` 兜底（HMFS/HMDFS 无 getcwd）。
6. `make -j1` → `make install` 到包内 prefix；`conan create` 全流程 + test_package 实跑。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `autoreconf` 报 `cannot open < @datadir@/automake-1.19/am/header-vars.am`、随后 `./compile not found` | 真机自带 automake 1.19 的 `am/` 数据文件里 `@datadir@` 占位符未展开（设备镜像缺陷，**E178**） | `tool_requires` 补 `automake/1.18` + `libtool/2.5.4`，经 build profile 解析出可用工具链（同 xsel/1.2.1、afuse、argp-standalone） |
| 2 | `xiccd -V` 不打印版本号 | 上游 `AC_INIT` 版本取自 `m4_esyscmd_s([git describe ...])`，tag 归档内无 `.git` → 展开为空串 | 补丁 0001 固化为字面量 `0.4.1` |
| 3 | `autoreconf` 报缺 `AUTHORS` / `NEWS` | 上游仓库不含这两文件，`AM_INIT_AUTOMAKE` 默认严格度要求存在 | 补丁 0001 追加 `foreign` 严格度（**不新建空文件**，避免伪造上游产物） |
| 4 | `configure` 报 `working directory cannot be determined` | HMFS/HMDFS 不支持 `getcwd` | 进程 cwd 切到 build_folder + 预置 `PWD` + 改写 configure 的 pwd 判定（2.70+/2.69 两种形态，同 xsel/1.2.1、aribb24/1.0.4） |
| 5 | `configure` 找不到 X11/glib/colord | 真机 conan 的 `tc.environment()`/`PkgConfigDeps` 自动注入 `PKG_CONFIG_PATH` 实测不生效 | `build()` 内作用域注入，`try/finally` 恢复（同 xsel、pidgin） |
| 6 | **加载期崩溃**：`gtype.c:2555:g_type_register_static: assertion failed: (static_quark_type_flags)` → Signal 6（rc=134），`-V` 都到不了 | **E444：进程内两份 GObject 类型系统** | 见下节 |

## E444：GObject 多副本导致的加载期崩溃（本包核心问题）

**现象**：编译、链接、打包全部成功，但 test_package 一加载 `bin/xiccd` 即 abort——不是 `main()` 里崩，而是**加载期**（依赖库构造器执行时）就崩，`--help` 都来不及执行。

**取证**（设备上最小复现，5 组对照）：

| 变体 | 链接形态 | 结果 |
|---|---|---|
| gt1 | 只静态链 glib2 | rc=0，`g_object_new` 正常 |
| gt4 | 静态 glib2 + `-lcolord`（main 为空） | **加载期崩**（Signal 6） |
| gt5 | shim 让共享 glib 排在 libcolord 之前 | 崩：`cannot register existing type 'gchar'`（gvaluetypes.c:453）——双份类型注册冲突 |
| gt6A | glib2 静态归档 + colord + `-rdynamic` | 复现：exe 导出 4123 个 `g_*` |
| gt6B | glib 符号只由 `libcolordprivate.so.2` 提供 | rc=0，`g_object_new`/`GMainLoop` 正常 |

**根因**：制品仓的 `glib2/2.88.0` **只发静态库**（`libglib-2.0.a` 等，无 `.so`），`PkgConfigDeps` 生成的 `glib-2.0.pc` 其 `Libs` 带全量静态 glib 链接列表，于是 `Makefile.am` 的 `$(GLIB_LIBS)` 把静态 glib 链进 `bin/xiccd`；而 `colord/1.4.8.1` 的 `libcolordprivate.so.2` 同样内嵌了一份 glib 并导出全部 `g_*`/`g_object_*`/`g_io_*`（`nm -D` 实测 4123 个）。进程内两份 GObject 类型系统；libtool 默认给程序加 `-export-dynamic`，使 exe 内那份也参与全局符号插入；ELF 初始化顺序为「先依赖库构造器、后 exe 构造器」→ `libcolordprivate` 的构造器调到的是 exe 里**尚未初始化**的 glib。

**修法**（沿用同栈先例 `gssdp/1.6.6`、`gupnp/1.6.8` 的「去源头」方案）：`generate()` 中把 generators 目录下 `glib-2.0.pc` 的 `Libs:` / `Libs.private:` 置空（保留 `Cflags`，头文件仍需可见）；静态 glib 完全不进链接，exe 对 `g_*` 的引用全部是 UND，运行时统一解析到 `colord.pc` 已声明的 `libcolordprivate.so.2` 导出的唯一副本 —— 全进程单 GObject 域。

**修后核验**（可复现取证，针对 conan 包目录内 `bin/xiccd`）：

```bash
# conan 包目录内
sha256sum bin/xiccd
# 03c0f32e69a3f9a24091be3b5fd09fd17645e4214ae589d07dff6b8c3bd742f6

nm -D --defined-only bin/xiccd | grep -c ' T g_'      # 0        （修复前 4123）
nm -D --undefined-only bin/xiccd | grep -c ' g_'      # 64       （运行时解析到 colord）
readelf -d bin/xiccd | grep NEEDED
```

实测 NEEDED（**无 libglib 系**，g_* 由 colord 私有库提供）：

```text
libX11.so.6  libxcb.so.1  libXau.so.6  libXdmcp.so.6  libXrandr.so.2
libXext.so.6  libXrender.so.1  libcolord.so.2  libcolordprivate.so.2
liblcms2.so.2  libc.so
```

**单副本契约**：`bin/xiccd` 引用的全部 `g_*`/`g_object_*`/`g_io_*` 必须都由 `libcolordprivate.so.2` 的导出集提供（当前 64 个 UND 全部命中）。上游若新增其导出集之外的 glib 调用，将表现为**链接期** `undefined reference`（而非运行期静默错误）——这是该方案的预期失效模式，升级 xiccd 版本时按上面的自检命令核对即可。

**已证伪的对照修法**：
- `-Wl,--exclude-libs,ALL` 抑制静态库符号导出 —— `gssdp/1.6.6` 实测仍崩：该选项只隐藏动态符号表，`.so` **内部**对静态库符号的引用在链接期已绑定到未初始化的本地副本。
- 共享 glib shim 抢先初始化（gt5）—— 爆双份类型注册冲突 `cannot register existing type 'gchar'`，rc=134。
- `.preinit_array` 钩子提前初始化 —— 仍晚于依赖库构造器，无效。

> 官方口径（`knowledge/doc/E444.md`）是消费方在首次 GObject/GIO 使用前显式调 `g_type_ensure_initialized()`——对**加载期**崩溃无效（那时 `main()` 尚未进入），故本包必须走链接形态修复。

## 源码修改

`patches/0001-configure.ac.patch`（`configure.ac`，2 处改动）：

1. `AC_INIT` 版本：`m4_esyscmd_s([git describe ...])` → 字面量 `0.4.1`（tarball 无 `.git`）。
2. `AM_INIT_AUTOMAKE` 追加 `foreign` 严格度（上游无 `AUTHORS`/`NEWS`）。

无平台宏（未使用 `__OHOS__`），无空壳 stub；`configure` 的运行时改写（umask/pwd）在配方 `_patch_configure()` 内完成，不进补丁树。

## 依赖版本

| 依赖 | 版本 | 用途 |
|---|---|---|
| libx11 | 6.4.0 | X11 核心（6.4.0 线） |
| libxrandr | 1.5.5.1 | RandR 输出变化监听（force 钉 libx11/6.4.0） |
| libxext | 6.4.0 | xrandr 传递依赖 |
| glib2 | 2.88.0 | GLib/GObject/GIO（制品仓只发**静态**库；本包只用头文件 + 版本检查） |
| colord | 1.4.8.1 | colord D-Bus 客户端；其 `libcolordprivate.so.2` 是 glib 符号的唯一提供方 |

工具依赖（`tool_requires`）：`automake/1.18`、`libtool/2.5.4`。

## 许可证声明说明（W4 审计 P3 留痕）

配方 `license` 声明为 `GPL-3.0-or-later`。可核验证据如下，供评审确认是否需要收紧为 `GPL-3.0`：

- 上游 tag 归档内 `COPYING` 为**逐字 GPLv3 正文**（含末尾 "How to Apply These Terms" 附录样板，其中出现的 "either version 3 of the License, or (at your option) any later version" 是 GPL 文本自身的示范措辞，**不构成上游对该程序的授权声明**）；
- `src/*.c` / `configure.ac` 等源文件**无版权头、无 SPDX 标识、无 or-later 表述**；
- 上游仓库 GitHub 许可证分类为 `GPL-3.0`（非 `GPL-3.0-or-later`）。

即：可核验证据严格支持 `GPL-3.0`；`-or-later` 系按 GPL 项目常见传播惯例（Debian 等发行版对"仅拷贝 GPLv3 文本"的上游多按 v3+ 处理）所作选择。若评审要求与证据严格对齐，改 `conanfile.py` 的 `license = "GPL-3.0"` 一行即可。

## 验证结果

```text
$ conan create archives/x/xiccd/0.4.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<默认> --build=missing
...
xiccd/0.4.1: Package installed ...
test_package: 三条断言全部通过
ALL CHECKS PASSED
```

W3 本地 CI（`ci/conan/build_and_test.sh`，junk_check + knowledge_check + L0-L5）：

| 门禁 | 结果 |
|---|---|
| JC（junk_check） | pass（incremental 模式） |
| KC（knowledge_check） | pass |
| L0（结构完整性） | pass |
| L1（test_package） | pass：test_package executed |
| L2（smoke test） | skip：该检查不在 conan runenv 下执行，缺 `libcolordprivate.so.2` 运行期路径；在 runenv 下 `-V` / `--version` / `--help` 均 rc=0（已实测） |
| L4（安全扫描 NX/PIE/RELRO） | pass |
| L5（产物基线） | pass |

## 上游测试用例对比（R51）

| 指标 | 上游 | 适配后 |
|---|---|---|
| 测试用例数 | 0（无 tests/，无 TESTS/check_PROGRAMS 注册） | 3（`test_package/test_xiccd.sh`） |
| 可运行环境 | — | CI/W3 headless（无 X display） |
| 实跑结果 | — | 3/3 通过 |
| 通过率 | — | 100% |
| 上游用例修改 | 无（上游无套件，未做任何修改） | — |

## 注意事项

- `bin/xiccd` 运行期需要 `libcolord.so.2` / `libcolordprivate.so.2` 等依赖库路径；conan runenv（`conanrun.sh`）与 CI test_package 会自动注入，裸跑需手动设 `LD_LIBRARY_PATH`。
- **glib 不得重新链进本可执行文件**：任何后续改动若让 `$(GLIB_LIBS)` 复活静态 glib，E444 加载期崩溃即复现。回归自检命令：
  `nm -D --defined-only <prefix>/bin/xiccd | grep -c ' T g_'` 必须为 0。
- 上游无测试套件，回归依赖适配侧 3 条断言（覆盖 `-V` 版本串，即补丁 0001 的回归保护）。
---

**编译结束**: 2026-10-15 16:42
**最终状态**: built
