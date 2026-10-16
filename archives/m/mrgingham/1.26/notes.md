# mrgingham 1.26 适配笔记

## 任务来源

- 平台任务 **8991**（开源鸿蒙PC专项积分赛），分支 `feat/mrgingham-1.26`，claimer=Ember5843
- 上游：github dkogan/mrgingham，tag **v1.26**（轻量标签，commit 03596d88…），
  tarball sha256=`3989191b764345b70d2574b56d68bb4151faa4e4804832bfde76dfc4232a2c53`
- 语言实测（R47 `lang-preflight`）：**cpp**（源文件 16 个，cpp:13 / c:2 / python:1，主体 81%）

## 选库核验

1. 无重复：main `archives/m/mrgingham` 不存在；ohpcd `conan list mrgingham/*` 无；本地 archives 无
2. 依赖：OpenCV（core/imgproc，必需）、Boost（Polygon/Voronoi，header-only）、pkg-config
3. 交付物：`libmrgingham.so` + 公共头 + `mrgingham` 等 CLI 工具

## 构建系统与关键适配

上游用**手写 Makefile**，由 **mrbuild** Makefile 框架驱动（`choose_mrbuild.mk`）。

### 1) mrbuild 框架的供给

mrbuild 无 Conan 包；`choose_mrbuild.mk` 的查找顺序是 `./mrbuild/` →
`/usr/include/mrbuild/` → 报错。配方在 `source()` 里下载上游 mrbuild **v1.13**
（`choose_mrbuild.mk` 内写死的版本，sha512 与上游登记一致）并解到 `<源码>/mrbuild`，
使其命中第一优先分支；构建期不需要联网。见 `conandata.yml:mrbuild`。

### 2) VERSION 注入

上游 Makefile 只定义 `ABI_VERSION := 2` / `TAIL_VERSION := 1`，把 `VERSION` 留给
mrbuild 的默认值 `$(ABI_VERSION).$(TAIL_VERSION)` = **"2.1"**（`git describe` 分支
在无 `.git` 的 tarball 上不可达）。配方显式传 `VERSION=1.26`，使工具/文档报告正确
的上游版本；ABI/TAIL 未动，`.so` 名仍为 `libmrgingham.so.2.1`（SONAME `libmrgingham.so.2`）。

### 3) 编译器/flags 来源（R33）

mrbuild 的 `CC ?= gcc` / `CXX ?= g++` 在 OHOS 上不存在，必须注入。
`footer` 明确**禁止**任何 `*FLAGS` 以命令行变量传入（`origin == command line` 直接
`$(error)`），但**允许环境变量**：

- `CC`/`CXX`：取 `tools.build:compiler_executables`（`self.conf.get`），走命令行参数
- `CXXFLAGS=-std=c++17`、`CPPFLAGS=-I<boost include>`：走**环境变量**

### 4) OpenCV 的 pkg-config

Makefile 用 `pkg-config --cflags/--libs opencv4` 取 OpenCV（在 Makefile 解析期求值）。
conan 的 `PkgConfigDeps` 只把 `.pc` 写进 generators 目录，故必须显式
`PKG_CONFIG_PATH`/`PKG_CONFIG_LIBDIR` 指向该目录（`PKG_CONFIG_LIBDIR` 会**替换**默认
搜索路径，顺带避免捞到设备 `~/usr/local` 下的同名 `.pc`）。

### 5) 源码补丁（1 个）——从 mrbuild footer 去掉 `--default-symver`

`patches/0001-ohos-lld-no-default-symver.patch`：mrbuild 的
`Makefile.common.footer` 给完整共享库目标加 GNU ld 专有的 `-Wl,--default-symver`；
OHOS SDK 用 **LLVM lld**，不认该参数
（`ld.lld: error: unknown argument '--default-symver'`）。
补丁直接改 vendored 的 `mrbuild/Makefile.common.footer`（`choose_mrbuild.mk` 优先
`./mrbuild/`；CI 日志报错路径正是 `mrbuild/Makefile.common.footer:213`，确认命中的是
它），把非 Darwin 分支那一行注释掉：

```diff
 ifeq ($(COND_DARWIN),)
-  $(LIB_TARGET_SO_FULL): LDFLAGS += -Wl,--default-symver
+#  $(LIB_TARGET_SO_FULL): LDFLAGS += -Wl,--default-symver  # OHOS LLVM lld does not implement this GNU ld option
 else
   $(LIB_TARGET_SO_FULL): LDFLAGS += -dynamiclib
 endif
```

只去掉该旗标，footer 其余 `+=`（`-shared -fPIC -soname`）与外部 `LDFLAGS` 原样保留。
与项目对**同一 footer** 的既有修法一致（`archives/m/mrcal/2.5.2` 的
`0003-mrbuild-drop-default-symver.patch`；`archives/l/libdogleg/0.18` 亦同）。

**为什么不再用「探测链接器是不是 lld」的写法（平台 CI #93329 的真因）**：初版补丁在
mrgingham 的 `Makefile` 末尾追加

```make
LDFLAGS_LINKER_IS_LLD := $(findstring lld,$(shell $(CC_LINKER) -Wl,--version 2>&1 | tr A-Z a-z))
```

即靠 `$(shell)` 在 **Makefile 解析期**跑一次链接器来判定。平台 CI 两次失败
（`#93287`、`#93329`）在**同一 HEAD** 上给出两种结果：`#93287` 探针命中、库链接正常
（命令里无 `--default-symver`）；`#93329` 探针未命中，`-Wl,--default-symver` 落到
`ld.lld`，报 `unknown argument`（同一 worker 镜像、同一 buildbot 环境变量）。
该探针会**重放链接器**，而链接器自身的依赖（`libxml2.so.16`，见下节）在 CI worker 上
可能不可用——探针一旦拿不到含 `lld` 的输出就**静默跳过覆盖**，于是构建硬失败。改为
直接改 footer 后不再依赖任何运行期探测，确定性地在所有路径去掉该旗标（GNU ld 上少一个
可选旗标，无影响）。

### 6) SDK lld 的 libxml2 隔离（平台 CI #93287 报错的真因）

OHOS 的 clang 驱动会调起 SDK 的 `lld`；`lld` 的 RUNPATH 是 `$ORIGIN/../lib`
（`<sdk>/ohos/native/llvm/lib`，内含 `libxml2.so.16`）。但 `LD_LIBRARY_PATH` 优先于
RUNPATH，若它前面出现**另一个** `libxml2.so.16`，lld 就加载错库并启动失败：

```
Error loading shared library libxml2.so.16: (needed by .../llvm/bin/lld)
Error relocating .../llvm/bin/lld: xmlFreeDoc: symbol not found
clang-15: error: unable to execute command: No such file or directory
```

- **触发链**：conan 的 `conanrun` 环境把本包全部传递依赖的 `lib` 目录（含
  `libxml2/2.15.3`，经 opencv 拉入）**前置**到 `LD_LIBRARY_PATH`；`test_package` 里那次
  消费者链接（`test()` 用 `env="conanrun"`）因此踩到它——正是 `#93287` 的失败点。
  设备上把一个不兼容的 `libxml2.so.16` 放到 `LD_LIBRARY_PATH` 首位，可**逐字复现**
  同一段报错。
- **隔离修法**：`conanfile.py` 与 `test_package/conanfile.py` 各加
  `_sdk_llvm_libdir()`（从 `tools.build:compiler_executables` 的编译器路径推出
  `<sdk>/llvm/lib`，并确认其中确有 `libxml2.so.16`），在链接命令前加
  `LD_LIBRARY_PATH="<sdk>/llvm/lib:$LD_LIBRARY_PATH"`，让 lld 先找到 SDK 自带的
  libxml2。该前缀在 `conanrun` **之后**求值，故仍优先于 conan 的目录；被测二进制仍以
  `conanrun` 运行，断言与副作用不变（不削弱测试）。这是项目既有做法
  （`archives/a/abr2gbr/1.0.2`、`archives/b/bubblewrap/0.11.0`、
  `archives/a/abseil/20260526`）。

## 依赖版本

- `opencv/4.12.0`（transitive_headers/libs：`mrgingham.hh` 公开 `#include <opencv2/core/core.hpp>`）
- `boost/1.89.0`（仅构建期 header-only，不传播）
  - **不用 1.85.0**：它会钉 `zlib/1.3.1`，与 OpenCV 拉的 `zlib/1.3.1.1` 冲突
    （`ERROR: Version conflict ... originates from boost/1.85.0`）

## 未构建项（如实申报，非移植缺陷）

| 产物 | 上游规则 | 缺什么 |
|---|---|---|
| CPython 扩展 `mrgingham$(PY_EXT_SUFFIX)` | `all: mrgingham$(PY_EXT_SUFFIX)` | `numpy/arrayobject.h`（OHOS 无 NumPy 移植） |
| `README.org` | `all: README.org` | `mawk`（本机只有 awk/gawk） |

因此 `build()` **不跑默认目标 `all`**，而是显式构建库+工具目标：

```
libmrgingham.so.2.1 mrgingham mrgingham-from-image \
test-dump-chessboard-corners test-dump-blobs test-find-grid-from-points
```

## 上游测试：9/9 实跑 PASS（测试期工具链，R51）

上游只有一套测试：`make test` → `test/test--mrgingham-rotate-corners`（zsh 脚本，
9 项检查）。此前因本平台缺 vnlog 的 Perl CLI 而无法运行；本轮以**测试期工具链**
（不入交付物、不占平台任务）把它**真正跑完**：`make test` 与直接
`/usr/bin/zsh test/test--mrgingham-rotate-corners` 两次运行均 **exit 0，9/9 `Test OK`**。

### 逐项结果（与最终日志逐字一致，2026-10-15）

| # | 用例 | 结果 |
|---|---|---|
| 1 | passthrough (`--gridn 3`) | Test OK |
| 2 | rot180 (`--gridn 3 --180 a`) | Test OK |
| 3 | rot180-multiple (`--gridn 3 --180 a --180 b`) | Test OK |
| 4 | rot90 (`--gridn 3 --90 a --180 b`) | Test OK |
| 5 | rot270 (`--gridn 3 --270 a`) | Test OK |
| 6 | failure-gridn-too-low--all-data (`--gridn 2`，期望 ERROR) | Test OK |
| 7 | failure-gridn-too-high--all-data (`--gridn 5`，期望 ERROR) | Test OK |
| 8 | failure-gridn-too-low--one-file (`vnl-filter filename=="a1"` + `--gridn 2`) | Test OK |
| 9 | failure-gridn-too-high--one-file (`vnl-filter filename=="a1"` + `--gridn 5`) | Test OK |

TOTAL=9，PASS=9，FAIL=0，SKIP=0，NOT_RUN=0。第 6-9 项是"期望非零退出"的用例，
已单独复核为**真实失败**而非假通过：`mrgingham-rotate-corners --gridn 2/5` 输出
`# File 'a0': expected 4/25 points but received 9` 且 rc=1（证据
`04-error-case-verification.txt`）。

### 测试期工具链（来源 + 缺口，均不入交付物）

`mrgingham-rotate-corners` 是无条件消费 vnlog 的工具；其测试需要下列**运行期**
组件（都不是构建依赖、不进 Conan 包）：

1. **vnlog 1.42 的 Perl CLI**（`vnl-filter`/`vnl-sort`/`vnl-gen-header` + `Vnlog/*.pm`），
   与 vnlog 1.42 上游源码**逐字节相同**（sha256 见证据 `05-toolchain-pin.txt`）。
   ohpcd 的 vnlog/1.42 制品只交付 C 库、不含这些脚本（见 `archives/v/vnlog/1.42`）。
2. **Perl 模块** `List::MoreUtils` 0.430 + `Exporter::Tiny` 1.006002（纯 Perl 安装；
   本机 perl 5.42 无 List::MoreUtils）。
3. **`mawk`**：vnlog 硬编码 `exec 'mawk'`；本机无 mawk，以 **gawk 5.4.0** 顶替。
4. **GNU `sort`**：vnl-sort 传 GNU 长选项（`--ignore-leading-blanks --key=`）；
   本机 `/usr/bin/sort` 是 toybox 0.8.12，以兼容 shim 翻译后调用。
5. **`/bin/bash` 与 `/bin/zsh`**：`mrgingham-rotate-corners` shebang 为 `#!/bin/bash`、
   测试脚本为 `#!/bin/zsh`，本平台 `/bin`→`/system/bin` 只读、无此二者；以 LD_PRELOAD
   的 execve/posix_spawn 小 shim 把缺失解释器重映射到真实
   `/data/service/hnp/bin/bash`、`/usr/bin/zsh`，**未改动任何上游文件**。

运行方式（经 `porting run`）：

```sh
PATH=<DK>/shim:<DK>/bin:$PATH PERL5LIB=<DK>/lib/perl5 \
LD_PRELOAD=<DK>/shim-src/interposer.so \
SHEBANG_SHIM_bash=/data/service/hnp/bin/bash SHEBANG_SHIM_zsh=/usr/bin/zsh \
  make test          # 或 /usr/bin/zsh test/test--mrgingham-rotate-corners
```

上述第 2-5 项是本轮为跑测试而补的**环境**（原交接只备了第 1 项 + List::MoreUtils），
仍属测试期、不进交付物。

### 交付物的运行期依赖（如实记录）

- `bin/mrgingham-rotate-corners`：运行需 vnlog 的 Perl CLI（上游 RPM 亦 `Requires: vnlog`），
  且脚本 shebang 为 `#!/bin/bash`——本平台 `/bin/bash` 不存在，直接执行需 bash 可用。
- `bin/mrgingham-observe-pixel-uncertainty`：shebang `#!/usr/bin/python3`，本平台该路径不存在。

## 构建内验证（消费者测试，真实执行）

`test_package/`（`conan create` 自动运行）：

- `test_mrgingham.cpp`：链接 `mrgingham.hh` 公开 API，调用
  `mrgingham::find_grid_from_points()` 在合成的 4x4 点阵（`FIND_GRID_SCALE=1000`
  整数坐标）上找网格，断言 ①返回 true ②点数=16 ③每个返回点与一个**互不重复**的
  输入点在 50（缩放单位）内重合（即检测网格是输入的置换）。
  实测：`PASS: find_grid_from_points() recovered a 4x4 lattice (16 points)`
- CLI 冒烟：运行已安装的 `bin/mrgingham --help`，断言输出含 `Usage:` 与 `gridn`

## 验证结果

| 项 | 命令 | 结果 |
|---|---|---|
| conan create（含消费者测试） | `conan create archives/m/mrgingham/1.26 -pr:h/-pr:b=ohos-aarch64 --build=mrgingham/* --build=missing` | PASS（exit 0） |
| 框架门禁 | `ohc-run.py conan-verify mrgingham 1.26 --profile <profile>` | PASS（exit 0；G0/G1/G2/G3/G4 实过；**L2/L4/L5 报告口径为「跳过（无 cache 路径）」，非实跑**，CI 同构里 L4/L5 实跑 pass、**L2 亦为 skip**；L2 冒烟面实际由 test_package 的 `mrgingham --help` 断言覆盖（已 PASS）） |
| CI 同构 | `ci/conan/build_and_test.sh`（CI_REPO_ROOT=worktree，CI_PACKAGES=archives/m/mrgingham/1.26，JUNK_PR_DIFF=本 PR diff） | PASS（exit 0；JC pass（prdiff 模式 9 文件）、L0 pass、L1 pass、L4 pass、L5 pass、L2 skip；库链接命令已无 `--default-symver`） |
| 上游 `make test` | `make test`（测试期 vnlog Perl CLI 环境） | PASS（9/9 `Test OK`，exit 0，见上） |

> 说明：本地跑 `build_and_test.sh` 必须给 `JUNK_PR_DIFF=<本 PR 的 diff>`，否则
> `ci/scripts/junk_check.sh` 会落到 `incremental` 模式（`git diff origin/main...HEAD`，
> 本 worktree 的 origin/main 陈旧），把全仓 5k+ 包误判成本 PR 的变更面。平台 CI 正是
> 以 PR diff 传入（日志「检查模式: prdiff」）。

## 交付物

| 路径 | 说明 |
|---|---|
| `lib/libmrgingham.so.2.1` + 软链 `libmrgingham.so.2` / `libmrgingham.so` | 共享库，SONAME `libmrgingham.so.2` |
| `include/mrgingham/{mrgingham.hh,point.hh}` | 公共头 |
| `bin/{mrgingham,mrgingham-rotate-corners,mrgingham-observe-pixel-uncertainty}` | 上游 `DIST_BIN` |
| `lib/pkgconfig` 由 `package_info.pkg_config_name=mrgingham` 供消费方 | `Requires: opencv4` |

## 注意事项

- 本库是**共享库**（mrbuild 不产静态库），`options.shared` 固定 True，`validate()` 拒绝 False
- 消费者必须能拿到 OpenCV 头（`mrgingham.hh` 直接 include `opencv2/core/core.hpp`），
  故 opencv 以 transitive_headers/libs 传播
- 构建在 build 目录内的源码副本中进行（mrbuild 是 in-source 构建），源缓存目录保持干净
