# toilet 0.3.r155.3eb9d58 适配笔记

## 编译环境

- 设备：HarmonyOS PC（MateBook Pro HAD-W32），HongMeng Kernel 1.12.0，aarch64
- Conan 2.29.1（OHOS 适配版），profile `ohos`（os=OHOS / os.version=6.0 / arch=armv8 /
  compiler=clang 15 / libcxx=libc++ / build_type=Release），**build 与 host 同 profile = 本机原生编译**
- 编译器：clang 15.0.4（`/data/service/hnp/bin/clang`）
- 构建系统：Autotools（configure.ac + Makefile.am，源码归档内**无**生成好的 configure/Makefile.in）

## 版本与源码身份（逐项核实）

| 项 | 值 | 证据 |
|---|---|---|
| 上游仓库 | <https://github.com/cacalabs/toilet>（Sam Hocevar，WTFPL v2） | 仓库 API `license=WTFPL`、`language=C` |
| 上游 tag | **无任何 tag** | GitHub API `/repos/cacalabs/toilet/tags` → `[]`；`/git/refs/tags` → 404；故不存在 git describe 形态版本串 |
| 上游版本 | `0.3` | `configure.ac`：`AC_INIT([toilet],[0.3])` |
| 提交 | `3eb9d58037afb0a1baec6dca82caa045fb2217c0` | 该提交即 master 最新提交（2016-09-27T11:54:13Z，Merge PR #6 "build: use more modern autotools features"） |
| 提交序号 r155 | 155 | GitHub commits API `per_page=1` 响应 `Link rel="last"` = `page=155`（本机实测），与哈希互证 |
| 源码归档 | `codeload.github.com/cacalabs/toilet/tar.gz/3eb9d58…`（GitHub 官方归档主机） | sha256 `a16b3a6217852d4ec5e9fa94c5600b900710d652910ac041bf1c5c61524a03d4`，本地与 init-build 两次下载逐字节一致 |

> **版本串命名口径**：`0.3.r155.3eb9d58` 由任务与分支名（`feat/toilet-0.3.r155.3eb9d58`）逐字给定，
> 本版本据此采用、**不自行改名**（改名会同时破坏分支名与平台任务绑定，触发 PF9/L0m 口径问题）。
> 本仓库同类「无 tag 仓库 + master tip + 提交序号」的版本串写作 `X.Y.Z.rN.g<sha>`（如
> `archives/m/ming/0.4.8.r68.g04aee523`、`archives/l/libelfin/0.3.r7.ge017276`），差别仅在哈希段的
> `g` 前缀——上游无 tag、本版本非 git describe 产物，故按任务给定原样使用。

语言预检（R47）：`lang-preflight toilet 0.3.r155.3eb9d58 --lang cpp` →
`detected_language=c`，证据 = 构建系统 `autotools`（configure.ac/Makefile.am）、源文件 7 个（c:7，主体占比 100%）；
C 与 C++ 属同一兼容族，继续适配主流程。

## 编译步骤（实际执行，全部由 conanfile.py 固化）

```bash
# conan 内部（build_folder = 源码目录，源码内构建）：
bash ./bootstrap                     # 上游自带：aclocal → autoconf → autoheader → automake
# 生成 configure 内两处 umask 077 改写为 umask 022（HMDFS 必需，见下）
"$SRC/configure" --prefix=<pkg> \
  --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
  --bindir=… --datarootdir=…        # 后四项由 AutotoolsToolchain 生成
make -j1
make check                           # 上游官方完整测试（下方统计）
make install                         # Autotools helper（DESTDIR + 包目录 prefix）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type; you must specify one` | 本机 `config.guess`(2024-07-27) 不识别 HarmonyOS 内核；且在 HMDFS 上它 `mkdtemp` 后写 `dummy.c` 直接 `Permission denied`（同一权限族） | 显式 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`（build==host → 跳过 config.guess，保持本机原生编译）。conan 只在 build profile ≠ host profile 时才自动注入三元组，本任务两侧同为 ohos profile，必须在配方里显式给 |
| 2 | `config.status[762]: can't create ./confXXXXXX/subs1.awk: Permission denied` → `could not setup config files machinery` | `config.status` 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录，HMDFS 下该目录实际为 `drwx--S---`(2700)；本机 uid 20020082 并非文件属主，目录访问靠 `file_manager` 组位判定，而组位无 rwx → 写入 EACCES。实测 `chmod 770` 无效（ls 仍 2700，写入继续失败），说明 chmod 在 HMDFS 上是 no-op | 改写**生成**的 `configure` 中两处 `umask 077` → `umask 022`（这两行由 autoconf 的 config.status 模板生成，不在源码树内，无法用补丁打到源码上；同 `archives/l/libcaca/0.99.beta20.1` 的处理），并对替换次数做契约断言（≠2 即报错） |
| 3 | `aclocal/automake: Can't locate Automake/Config.pm in @INC (@INC … //share/automake-1.18 …)` | automake/1.18（制品仓）以 perl 脚本分发，脚本内烤死 `@datadir@`；其 `package_info` 用 `PERL5LIB`/`ACLOCAL_PATH` 修正，**只在 conanbuild 环境内生效**，直接调包内 `bin/aclocal` 会失败 | 以 `tool_requires("automake/1.18")` 拉入，且**先** append `buildenv_info` 再 `VirtualBuildEnv.generate()`（顺序错则注入不生效），全部构建命令走 `env="conanbuild"` |
| 4 | 上游测试假失败：`grep: ../src/main.c: No such file or directory`、`could not load font *.tlf` | 上游 `test/check-source` 与 `test/check-fonts` 按**源码树相对路径**取 `../src/*.c`、`../fonts`，只在 `srcdir == builddir` 时成立；conan `basic_layout` 默认把构建放在 `build-release/` 子目录（VPATH 构建）→ 两个测试都在错误的目录里找文件 | 源码内构建：`basic_layout(self, src_folder=".")` + `self.folders.build = "."`（同 `archives/a/adjtimex/1.29` 先例）。**上游测试脚本一字未改**（本版本另有 1 个源码补丁，见下节，与该测试无关） |
| 5 | 链接期 `undefined symbol: gzopen / inflateInit2_ …`（探索阶段手工构建时） | libcaca 是静态库且传递依赖 zlib（libcaca.a 内部用 zlib 解压 PKZIP 字体） | 由 conan 依赖环境自动提供（`libcaca` 的传递依赖 zlib/1.3.1 计入 LIBS）；配方不需要手工写 `-lz`。手工探索阶段曾用 `LIBS=-lncursesw -lz` 复现验证 |
| 6 | 安装后的 `toilet` 运行期报 `error: could not load font pagga`（不带 `-d` 时找不到包内字体） | conan 惯例用 `--prefix=/` + `make install DESTDIR=<包目录>` 安装，于是 `src/Makefile.am` 的 `-DFONTDIR=\"$(datadir)/figlet\"` 展开为 `/share`、二进制内烤死 `//share/figlet`；上游未提供任何覆盖点（`src/main.c`: `cx->dir = FONTDIR;`，无 configure 选项、无环境变量） | `patches/0001-src-Makefile.am.patch` 把该写法改为可覆盖的 `FONTDIR ?= $(datadir)/figlet`（默认行为与上游完全一致），配方在 `make` 命令行传 `FONTDIR=<包目录>/share/figlet`（同 `archives/f/figlet/2.2.5` 的既有做法）。实测 `strings bin/toilet` 已指向包内 `share/figlet`，HM-E2E-01/03 因此通过 |

## 源码修改

本版本有 **1 个源码补丁**：`patches/0001-src-Makefile.am.patch`
（在 `conandata.yml` 的 `patches` 段声明，由 `conanfile.py` 的 `apply_conandata_patches()`
在 `build()` 开头应用；`manifest.yaml` 的 `patches_applied` 同步声明）。

| 文件 | 改动 | 理由 |
|---|---|---|
| `src/Makefile.am` | `toilet_CPPFLAGS = -DFONTDIR=\"$(datadir)/figlet\"` → 增加 `FONTDIR ?= $(datadir)/figlet` 并把 `toilet_CPPFLAGS` 改为 `-DFONTDIR=\"$(FONTDIR)\"` | 为**编译期字体目录**增加一个 make 命令行覆盖点：conan 用 `--prefix=/` + DESTDIR 安装使 `$(datadir)` 展开为 `/share`，二进制内烤死 `//share/figlet`，运行期找不到包内字体（见问题 #6）。默认值与上游逐字一致，未改任何逻辑分支；**不含任何平台宏**（无 `#ifdef __OHOS__`、无平台条件分支），仅 packager 覆盖点，故 `manifest.yaml` 标注 `type: portability / platform_only: False / guard: 'none'` |

上游**测试脚本**（`test/check-source`、`test/check-fonts`）与其余所有上游文件零改动：
两个测试按源码树相对路径取值，配方通过源码内构建（`folders.build = "."`）让它们**原样**通过，
而不是去改测试。

除该补丁外，对**生成物**还有一处必需改动：`build()` 内把生成后的 `configure` 里 2 处
`umask 077` 改写为 `umask 022`（见问题 #2；该字符串由 autoconf 的 config.status 模板生成，
不在源码树内，无法、也不应做成源码补丁；同 `archives/l/libcaca/0.99.beta20.1` 的处理）。

编辑过程记录：`python3 scripts/ohc-run.py track-edit add toilet 0.3.r155.3eb9d58 src/Makefile.am`，
补丁由 `python3 scripts/ohc-run.py refresh-patch --auto toilet 0.3.r155.3eb9d58` 生成（非手写 diff）。

## 依赖版本

| 依赖 | 版本 | 类型 | 验证 |
|---|---|---|---|
| libcaca | `0.99.beta20.1` | 运行期硬依赖（`PKG_CHECK_MODULES(CACA, caca >= 0.99.beta18)`） | `conan download --only-recipe` + `conan install --build=never` 均命中 prebuilt（含传递 ncurses/6.4、zlib/1.3.1），未从源码补建 |
| automake | `1.18` | 构建期 `tool_requires` | 同上，prebuilt 命中 |
| autoconf / m4 / pkg-config | 2.72 / 1.4.x / 0.29.2 | 构建期，设备自带 | 设备 `/data/service/hnp/bin` |

## 验证结果

### 上游官方完整测试（conanfile.py 的 `build()` 内 `make check` 实际执行）

`test/Makefile.am`：`TESTS = check-source check-fonts`（清点 = 2 个测试脚本）。

| 测试 | 实际运行 | 结果 | 实测口径 |
|---|---|---|---|
| check-source | ✅ | PASS | `11 files, 1147 lines, 0 errors in source code` |
| check-fonts | ✅ | PASS | `24 fonts, 0 load errors`（构建出的 toilet 逐个加载包内全部字体） |
| automake 汇总 | ✅ | `# TOTAL: 2 / # PASS: 2 / # FAIL: 0 / # ERROR: 0 / # SKIP: 0` | `make check` 退出码 0 |

### 消费者端到端用例（鸿蒙 PC 目标机，安装后的包，test_package）

| 用例 ID | 场景 | 输入 | 预期业务输出 | 实测 |
|---|---|---|---|---|
| HM-E2E-01 | 文本渲染端到端 | 真实文件 `input.txt` = `OHOS`，`toilet -f pagga --width 80`（stdin） | 3 行 pagga 字形，逐字节等于黄金文件 | ✅ PASS（`cmp` 一致，exit=0） |
| HM-E2E-02 | 字体资产端到端 | 包内 `share/figlet/*.tlf` 全部 24 个字体，`toilet -d <包字体目录> -f <font> "Hello World"` | 24/24 加载成功、exit=0、输出非空 | ✅ PASS（0 个加载错误） |
| HM-E2E-03 | HTML 导出端到端 | `toilet --html -f pagga "OHOS"` | 完整 XHTML（DOCTYPE + `</div></body></html>`）+ 3 行字形 span（含 `&#9608;`） | ✅ PASS（3 行 span，结构齐全，exit=0） |

（本表为设计口径；实机执行后的实际数字与日志路径见下方「实机执行记录」。）

### 实机执行记录（2026-10-16，鸿蒙 PC HAD-W32 本机原生构建）

强制重建本包的完整干净验证（等价 CI 的 `conan create … --build=toilet/*`）：

```bash
conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build=toilet/*
# CREATE_EXIT=0
# Apply patch (portability): src/Makefile.am: make the compiled-in FONTDIR overridable…
# checking for caca >= 0.99.beta18... yes
# # TOTAL: 2  # PASS: 2  # FAIL: 0  # ERROR: 0  # SKIP: 0
#   check-source : 11 files, 1147 lines, 0 errors in source code
#   check-fonts  : 24 fonts, 0 load errors
# [E2E] 被测二进制 = <被测包目录>/bin/toilet（位于被测包目录内）✓
# [E2E] 系统：HarmonyOS aarch64 / HongMeng Kernel 1.12.0
# [E2E] PASS HM-E2E-01 — 渲染输出与黄金文件逐字节一致（147 字节，exit=0）
# [E2E] PASS HM-E2E-02 — 包内 24/24 个字体全部加载并渲染成功，0 个加载错误
# [E2E] PASS HM-E2E-03 — HTML 文档结构完整且含 3 行字形（757 字节，exit=0）
# [E2E] 消费者端到端用例统计：PASS=3/3 FAIL=0
```

产物核对（同一次 conan create 的缓存包目录）：

| 项 | 实测 |
|---|---|
| `bin/toilet` | 存在（1,284,608 B，可执行） |
| `share/figlet/*.tlf` | 24 个（= 上游 `fonts/Makefile.am` 的 `allfonts`） |
| `share/man/man1/toilet.1` | 存在（由 `doc/toilet.1.in` 生成） |
| `licenses/COPYING` | 存在（WTFPL v2） |
| 二进制内烘焙 `FONTDIR` | `<包目录>/share/figlet`（`strings` 实测；未打补丁时曾是 `//share/figlet`） |

原始日志与 E2E 证据全部保存在本机（不入 PR）：
`/storage/Users/currentUser/tmp/toilet-evidence/conan-create-w3.log`、
`/storage/Users/currentUser/tmp/toilet-evidence/test-logs/`、
`/storage/Users/currentUser/tmp/toilet-e2e-17920/`。

## 知识引用（W5）

| 知识 | 用途 |
|---|---|
| E175（HMDFS 临时目录限制，`configure`/`config.status`） | 定位问题 #2 的 `config.status` 临时目录 EACCES |
| E490（Autotools helper 执行位）/ E178/E248（设备无 automake） | 问题 #3 的 automake 自举方案 |
| E524（依赖注入用私有 prefix、HMDFS 权限按组判定） | 问题 #2 的权限机理与 `PKG_CONFIG_PATH` 只指向本配方 generators_folder |

## 注意事项

1. `configure.ac` 里的 `AM_CONFIG_HEADER` 已过时（autoconf 2.72 给出 obsolete 警告，automake 1.18 仍接受），
   只是警告、不影响产物；未做改动（避免无必要偏离上游）。
2. `configure.ac` 会用未定义的 shell 变量 `$stamp` 拼 DATE，故 `toilet --version` 输出
   `Version: 0.3, date:` 后为空——上游自身行为，未改动。
3. clang 15 对上游 CFLAGS 里的 `-fno-strength-reduce` 报 `warning: optimization flag … is not supported`，
   仅警告、产物正常；未删除上游标志（无必要偏离上游）。
---

**编译结束**: 2026-10-16 01:38
**最终状态**: built
