# gem5 25.1.0.1 适配笔记（HarmonyOS PC / OHOS aarch64）

## 编译环境

| 项 | 值 |
|---|---|
| 构建系统 | scons（SCons 4.11.1，generate() 内 pip 引导） |
| 编译日期 | 2026-10-08（本次全量重建复验；基线 2026-09-26） |
| 编译器 | hnp clang 15.0.4 / clang++（target aarch64-unknown-linux-ohos） |
| 构建目标 | `build/ARM/gem5.opt`（KVM 保留编译；**protobuf/png/hdf5/capstone/tcmalloc 可选依赖已全部接线**，2026-10-09 二次验证） |
| 依赖 | `zlib/1.3.1`（conan 静态 `libz.a`） |
| 源码 | GitHub tag `v25.1.0.1`（sha256 `86bf3123…119b9`） |
| 运行期 | `PYTHONHOME=<python 前缀>`、可写 `TMPDIR`；rpath 已内嵌（libpython 免 LD_LIBRARY_PATH） |

## 编译步骤（配方自动化，2026-09-26 固化）

1. `generate()`
   - `python3 -m pip install --target=<build>/_scons_env scons==4.11.1`（ohpcd 无 scons 配方；与 dxx-rebirth 0.6 先例一致）
   - 从“将运行 SCons 的实际 CPython”发现 include/lib/prefix，生成 `python3-config` shim（OHOS 不带 python3-config，gem5 SConstruct:486-503 强制要求）
   - 生成 `cc` shim（`ext/libelf/native-elf-format` 用裸 `cc` 探测本机 ELF 格式；缺失会生成空 ELFCLASS/ELFDATA2 头导致 libelf 编译失败）
   - 写出 4 个私有兼容头（见下），经 `CCFLAGS_EXTRA -I<compat>` 注入
   - 环境注入（gem5 的 SCons **不认 CLI 变量赋值**，必须走进程环境）：
     `CC`/`CXX`（defaults.py var_overrides）、`PYTHON_CONFIG`、`CCFLAGS_EXTRA`、`LINKFLAGS_EXTRA`（SConstruct:987/988）、`PYTHONPATH`、`PYTHONHOME`、`TMPDIR`、`LD_LIBRARY_PATH`、`PATH`（cc shim）
   - `LINKFLAGS_EXTRA = /system/lib64/libc.so -L<zlib>/lib -Wl,-rpath,<python>/lib`
     （ucontext 符号仅在运行期 libc；zlib 静态包 -L 先于 sysroot；rpath 供 libpython 加载）
2. `build()`：`apply_conandata_patches` → `python3 -m SCons build/ARM/gem5.opt -j8`
3. `package()`：`bin/gem5.opt` + `share/gem5/configs/`（上游 configs 树）+ `licenses/LICENSE`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SCons CLI 变量赋值无效 | gem5 只从进程 env 读取（defaults.py） | 全部走 `Environment` → `CCFLAGS_EXTRA`/`LINKFLAGS_EXTRA`/`CC`/`CXX`/`PYTHON_CONFIG` |
| 2 | 无 python3-config | OHOS 未提供；hnp sysconfig 路径失真（/python3） | generate() 从实际 python 发现真实路径并生成 shim |
| 3 | zlib 硬依赖、系统库不可写 | SConstruct 无 zlib 直接 error；R26 禁止系统同名 .so | conan 静态 `zlib/1.3.1`，`-I/-L` 注入；**禁用 `-L/system/lib64`**（会劫持 libc++ 解析，实测复现） |
| 4 | `__containerof` 未定义（ext/libelf/elf_scn.c） | OHOS `sys/cdefs.h` 缺；`sys/queue.h` 使用 | 兼容头 `sys/cdefs.h`（include_next + 定义） |
| 5 | ucontext 符号缺失 | SDK 头是空壳、sysroot 不导出，运行期 libc 有弱符号 | 兼容头声明 + 绝对路径链接 `/system/lib64/libc.so` |
| 6 | `#define stdin (stdin)` 破坏 C++ 用法 | OHOS stdio.h 括号宏；含自动生成的 `param_BaseSemihosting.cc` | 兼容头 `stdio.h`：include_next 后 `#undef stdin/stdout/stderr` |
| 7 | `struct sockaddr_storage` 重复定义 | OHOS `linux/socket.h` 与 `sys/socket.h` 冲突 | 兼容头 `linux/socket.h`：先引 sys/socket.h，复补 2 个 UAPI 项，用头卫跳过真实头 |
| 8 | `/tmp` 只读导致 guest 打开 `/dev/urandom` 崩溃 | `tmpfile()` 失败后 `fileno(NULL)` | 源码补丁 0003：回退 `TMPDIR` mkstemp+fdopen，并加 NULL 检查 |
| 9 | AArch32 hello guest 模拟退出码 13 | AArch32 SE loader 实现细节（OHA 无关） | P3 复核：aarch64 静态 guest SE 运行退出码 0（test_package 断言覆盖） |
| 10 | gem5 25.1 无 `--version`（RC=2） | 上游 25.1 仅 `--help`；L2 冒烟需回退 | 配方 test_package 用真实 SE 运行断言；conan-verify L2 自动回退 `--help`（RC=0） |

## 源码修改（5 个补丁，全部由 `refresh-patch --auto` 从 `.orig`↔`.work` 生成）

| # | 补丁 | 文件 | 改动 | 原因 |
|---|---|---|---|---|
| 1 | `0001-src-arch-arm-freebsd-se_workload.cc.patch` | `src/arch/arm/freebsd/se_workload.cc` | `#if !defined(__GNU_LIBRARY__)` → `#if defined(__FreeBSD__) \|\| defined(__APPLE__)`（2 处） | musl 不定义 `__GNU_LIBRARY__`，误编译 BSD `sysctl` 路径 |
| 2 | `0002-src-cpu-kvm-timer.cc.patch` | `src/cpu/kvm/timer.cc` | `SIGEV_THREAD_ID` 分支用 `#if defined(__GLIBC__)` 守卫，否则 `SIGEV_SIGNAL` | OHOS signal.h 无 `SIGEV_THREAD_ID`/`_sigev_un`（KVM 保留编译，本机无 /dev/kvm） |
| 3 | `0003-src-kern-linux-linux.cc.patch` | `src/kern/linux/linux.cc` | `tmpfile()` 失败时回退 `TMPDIR` 下 `mkstemp`+`fdopen`，并做 NULL 检查 | `/tmp` 只读；guest 打开 `/dev/urandom` 即崩 |
| 4 | `0004-src-base-circular_queue.hh.patch` | `src/base/circular_queue.hh` | +`#include <sys/types.h>` | `ssize_t` 未定义（OHOS libc++ 不传递包含） |
| 5 | `0005-src-sim-fd_entry.hh.patch` | `src/sim/fd_entry.hh` | +`#include <sys/types.h>` | `mode_t` 未定义 |

补丁内**无 `__OHOS__` 宏**（R8/PF5），使用标准平台宏/通用回退；`patch --dry-run` 全部通过。

## 非源码适配（配方 generate() 固化，不进补丁）

- scons 4.11.1 pip 引导（`--target=<build>/_scons_env`，build() 用 `PYTHONPATH=… python3 -m SCons`）
- `python3-config` shim（路径来自当期 python 发现，**不写死设备路径**）
- `cc` shim → `tools.build:compiler_executables.c`（缺省 clang）
- 兼容头 4 个（内容与 P2 现场一致；`ucontext.h` 注释修正为“绝对路径链接 libc”）
- zlib 注入：`-I<zlib pkg>/include`、`-L<zlib pkg>/lib`（静态 `libz.a`，gem5 自身 `-lz` 落位）

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|---|---|---|---|
| zlib | 1.3.1 | ohpcd（conan） | 静态 `libz.a`，package id `6b129b068851896169fae42d399fa922d239ce8a` |
| scons | 4.11.1 | pip（pypi.cnb.cool 镜像） | `python3 -m SCons` |
| CPython | 3.12.8 | hnp（`/data/service/hnp/python.org/python_3.12`） | 构建与内嵌解释器 |

## 验证结果

### conan create（全量清洁构建，Official cache 预热）

- 命令：`conan create <archive> -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
- 用时：**85 分钟**（16:48:43 → 18:13:48，含源码下载、pip 引导、~2000 TU 编译、链接、打包、test_package）
- recipe revision `827b4b7f833d03f591bfb75bc44a878d`；package_id `d19813127f0ec2ca84c0b48cbd85080965097448`
- RC=0；日志 `~/tmp/gem5-precreate.log`
- `bin/gem5.opt` = 1,129,097,792 B；SHA256 `1922a845eaaea56123c3c51b237e0d539039bd3dedd7edf0e080a5e08954e4fe`

### conan-verify

- 命令：`OHC_PROJECT_DIR=$HOME/runner/gem5-wt python3 $HOME/build_in_harmonyos/scripts/ohc-run.py conan-verify gem5 25.1.0.1`
- **RC=0，Verdict PASS**（G0/G1/G2/G3/G4/L2/L4/L5 全绿；日志 `~/tmp/gem5-verify1.log`，报告 `reports/conan-verify-report.md`）
- 备注：G4 因工具对 Conan 2.29 `conan list --format=json` 结构解析告警（“无法找到程序包 ID”），L2/L4/L5 被跳过；已按 test-report.md §2 对打包产物手工复核（`--help` RC=0；PIE/NX/BIND_NOW/RUNPATH 通过）。
- `.conan-verified` marker：`verified_at=2026-09-26T18:16:04.266198`

### test_package（真实 SE 仿真）

4/4 断言通过（`Hello world!`、RC=0、模拟退出码 0、stats.txt），详见 `reports/test-report.md`。

## 交付物

| 文件 | 大小 | 说明 |
|---|---|---|
| `bin/gem5.opt` | ~1.05 GiB | ARM 优化版模拟器（含内嵌 Python m5 包） |
| `share/gem5/configs/` | ~2 MiB | 上游配置脚本树（se.py 位于 `configs/deprecated/example/se.py`，25.1 起 se.py 已弃用） |
| `licenses/LICENSE` | 3.4 KiB | BSD-3-Clause |

## 注意事项

- 运行期必须 `PYTHONHOME=<python 前缀>`（内嵌 CPython 的编译期前缀是 `/python3`，设备不存在）；配方已把 libpython 目录写入 rpath，`LD_LIBRARY_PATH` 可省略。
- `TMPDIR` 需可写（本机 `/tmp` 只读）；源码补丁 3 已兜底 gem5 自身的临时文件。
- guest 程序须为**静态** aarch64 ELF；OHOS musl 动态/启动代码会触发 gem5 SE 未实现的 `prctl(167)`，测试用 freestanding 程序规避。
- KVM 未启用（本机无 `/dev/kvm`），但相关代码保留编译（关 KVM 会断 SimObject 引用，P2 已复现）。

## 上游测试清点（R51 三步法）

### 1. 清点（基于 `v25.1.0.1` 纯净源码）

| 类别 | 数量 | 说明 |
|---|---|---|
| `tests/` 文件总数 | 756（219 个 `.py`） | `tests/main.py`（testlib 入口）、`tests/run.py`、`tests/run_pyunit.py`、`tests/pyunit/`、`tests/gem5/`（489 目录 / 200 `.py`）、`tests/test-progs/`、`tests/deprecated/` |
| Python 单测（pyunit） | 12 个模块 / 127 个 test 函数 | `tests/pyunit/{pystats,stdlib,stdlib/resources,util}`，经 `gem5.opt tests/run_pyunit.py` 运行 |
| 套件测试（testlib） | 200 个 `.py` 测试定义 | 需 gem5 resources（磁盘镜像/内核/参考输出等外部资源，多数用例需下载或预置） |
| C++ 单测 | 66 个 `*.test.cc` | `build/ALL/unittests.opt` 或单目标 `build/ARM/<path>.test.opt` |

### 2. 实跑（OHOS 真机，2026-09-26）

| 项 | 命令 | 结果 |
|---|---|---|
| pyunit（打包二进制） | `<pkg>/bin/gem5.opt tests/run_pyunit.py`（cwd=构建树） | **Ran 110 / 100 passed / 7 failed / 3 error**（9.2s） |
| pyunit（P2 同源二进制复核） | `.../gem5-25.1.0.1.work/build/ARM/gem5.opt tests/run_pyunit.py` | 结果一致（110/100/7/3） |
| C++ 单测抽样 | `SCons build/ARM/base/bitunion.test.opt -j4` + 运行 | **构建 RC=0；13/13 PASSED** |
| testlib 套件 | 未执行 | 用例依赖外部 gem5 resources（磁盘镜像/内核/参考输出，服务正处 429 限流），不具备可复现条件 |
| 全量 `unittests.opt` | 未执行 | 需 `build/ALL` 二次全量构建（~2000 TU），与清洁构建/并行会话共享 8 核/32GB 额度，超出本阶段预算；改为单目标抽样 |

未通过 10 项（全部 `tests/pyunit/stdlib/resources`，gem5 resources 客户端 API 测试）技术原因：
两次运行均收到 `HTTP Error 429: Too Many Requests`（resources.gem5.org 外部服务限流），
期望的 API 错误信息与 429 不匹配 → 7 FAIL + 3 ERROR；非 OHOS 平台问题、非 gem5 代码缺陷。

### 3. N / N′（如实）

- **N（清点）**：pyunit 127 个 test 定义（标准 runner 实发现 110）；C++ 单测 66 个目标；testlib 套件 ~200 个测试脚本。
- **N′（实跑）**：pyunit 110 项（12 模块）+ C++ 单测抽样 1 目标（13 用例）。
- **通过率**：pyunit 100/110 = **90.9%**（10 项为外部服务 429 限流）；C++ 抽样 13/13 = 100%。
- 完整数据与逐项清单见 `reports/test-report.md`。
---

## CI 修复记录（第 1 轮，2026-09-26）

**现象**：CI 构建 #62101（PR #12974）在 `conan create` 的 SCons 配置阶段 53 秒即失败：本机 W3 全绿的同版本配方在 CI 上**所有** SCons 编译器探测均为 no，`Checking for C header file Python.h` 失败（fatal）。

**根因**：`generate()` 中 `shutil.which("python3")` 使用的是 **conan 进程**的 PATH（CI worker 上 `/data/app/bin/python3` 优先，为 CI 应用私有 CPython，prefix `/data/service/hnp/OpenHarmonyPCDeveloper_build_in_harmonyos_ci_o.org/...`），而 `build()` 中运行 SCons 的 `python3` 来自 conan **buildenv** PATH（`ohos-aarch64` profile 前置 `/data/service/hnp/bin` → hnp 公共 CPython）。两个解释器不是同一安装 → `python3-config` shim、`PYTHONHOME`、`LD_LIBRARY_PATH`、rpath 全部指向错误安装，SCons 探测环境不一致而整体失败。

**修复**（`conanfile.py: _run_python_discovery`）：候选顺序镜像 buildenv 解析顺序——`/data/service/hnp/bin/python3` → `~/usr/local/bin/python3` → `~/.local/bin/python3` → `/usr/local/bin/python3` → `/usr/bin/python3` → `/data/service/hnp/python.org/python_3.12/bin/python3` + `/data/service/hnp/python.org/*/bin/python3` 通配 → **最后**才 `shutil.which("python3")`；确保 shim 与实际运行 SCons 的解释器恒为同一安装。

**本地验证**：
1. 微测（含诱饵场景：把 `shutil.which` 伪造成应用私有 python）→ 仍稳定选择 `/data/service/hnp/python.org/python_3.12`；新 shim 的 `--includes/--ldflags --embed` 输出正确；clang 编译+链接+运行内嵌 Python 测试 RC=0。
2. 既有构建树 fresh configure（配方同款 env：新 shim/PYTHONHOME/LD_LIBRARY_PATH/CCFLAGS/LINKFLAGS）→ `-Wl,--as-needed … yes`、`Python.h … yes`、`Python version 3.12.8`、`accept(0,0,0) … yes` 等全部恢复通过，并正常进入编译阶段。
3. 说明：修复只改变解释器**选择顺序**；本机选择结果与修复前相同（同为 python.org python_3.12），故未重复 85 分钟全量重建，上述配置阶段复现覆盖了唯一受影响路径。

---

## CI 修复记录（第 2 轮，2026-09-26）

**现象**：修复轮 1（`360a44bb30`）后 CI #62144（worker CI-038）仍在同一位置失败（45.6s）：SCons 全部编译器探测为 no、Python.h fatal；`python3-config shim` 仍指向 CI 应用私有 CPython（worker 上无 hnp python.org 公共包，属环境事实）。

**根因定位（本机机理复现）**：
- worker 的 app 私有 CPython `lib/` 会捆绑一批基础运行库（hnp python 实测含 `libz.so.1` 等）。原配方 `prepend_path("LD_LIBRARY_PATH", <python libdir>)` 把该目录排到 OHOS SDK `llvm/lib` **之前**。
- OHOS SDK 的 **lld 动态依赖 `llvm/lib/libxml2.so.16`**（profile 注释亦明示）。本机复现：`LD_LIBRARY_PATH` 前置一个含残缺 `libxml2.so.16` 的目录后，`lld` 报 `Error loading shared library libxml2.so.16`（符号重定位失败），SCons 链接类检查（`-Wl,--as-needed`、`-gz`、Python 版本探测）全部转 no——与 CI 失败签名一致。

**修复**（`conanfile.py: generate()`）：
1. `LD_LIBRARY_PATH` 由 prepend 改为 **append**（`append_path`）：llvm/lib 优先，libpython 仍可被 `CheckPythonLib` 运行期解析；
2. 显式 `SHELL=/system/bin/sh`（dxx-rebirth 0.6 先例：CI 继承的 shell 路径对 SCons 派生的构建动作不可用）;
3. `TMPDIR` 尊重环境已有值（worker 的 app 私有 cache），无则回退 build 目录。

**本地验证**：按新 env 语义（llvm/lib 在前 + python libdir 追加 + SHELL=/system/bin/sh + TMPDIR 环境值）fresh configure 全部检查通过（含 `Python version 3.12.8`），与“前置污染”复现形成对照（同一构建树、同一批检查）。
---

**编译结束**: 2026-09-27 00:48
**最终状态**: built

---

## CI 修复记录（第 3 轮，2026-09-27，阶段 7）

**现象**：修复轮 1/2（`360a44bb30`/`6ed0f12aed`）后 CI #62101/#62132/#62144/#62199 仍同错：`conan create` 的 SCons 配置阶段 45–53s 失败，**全部**编译/链接探测为 no（`-Wl,--as-needed`、`-Wno-c99-designator`、`-gz`…）直到 `Checking for C header file Python.h... no` fatal；本机 W3 全绿，两轮修复均本地复现通过但 CI 症状不变。

**根因（两个独立问题，均已在本地复现）**：
1. **SCons POSIX SHELL 硬编码**：SCons 4.11.1 `SCons/Platform/posix.py` 写死 `env['SHELL'] = 'sh'`，所有 action 以 `['sh','-c',...]` 启动，`sh` 按**子进程 PATH** 解析；进程环境 `SHELL` 对 SCons 无效。CI worker（buildbot appspawn 沙箱）中该解析失败 → spawn 抛 `FileNotFoundError: 'sh'`，SCons Configure 捕获后仅记 `... no`（细节只在 config.log）→ 所有探测静默失败。本机受限 PATH 复现：stock SCons `LINK_OK=0 HEADER_OK=0` + config.log `FileNotFoundError: 'sh'`；同环境把 posix.py 的 SHELL 固定为 `/system/bin/sh` 后 `LINK_OK=1 HEADER_OK=1`。godot 4.7.2 / gpsd 3.26 / serf 1.3.10 / vixl 5.1.0 均已用同一补丁通过 CI。
2. **构建期 Python 依赖 worker 环境**：原实现按 `/data/service/hnp/bin/python3`→…→`shutil.which` 查找，CI worker 上解析到 CI 应用私有 CPython（`/data/service/hnp/OpenHarmonyPCDeveloper_build_in_harmonyos_ci_o.org/..._1.0.0`），shim/PYTHONHOME/rpath 随环境漂移；另外 conan python 是 `--prefix=/` 构建、嵌入使用时需要显式 stdlib 路径（SCons 的 `env['ENV']` 白名单不含 PYTHONHOME）。

**修复**（`conanfile.py`，最小而稳）：
- `build_requirements()` 增 `tool_requires("python/3.12.9")`（ohpcd 已发布 OHOS 签名二进制：`bin/python3`、`include/python3.12/Python.h`、`lib/libpython3.12.so(.1.0)`、`lib/python3.12/`；CI 直接下载，无需重建；E543 模式）；
- `generate()` 构建期 CPython 有序解析：① conan python 包 package_folder（`self.dependencies.build["python"]`）→ ② `HNP_PUBLIC_HOME/python.org/python_*` → ③ 当前解释器（修正 sysconfig 探测）；每个候选必须同时具备 `include/python3.12/Python.h` + `lib/libpython3.12.so*` + stdlib + 可运行解释器，否则跳过；全部失败则 `self.fail` 列出候选（杜绝静默回退）；
- 选定前缀贯穿：`python3-config` shim、`PYTHON_CONFIG`、`PYTHONHOME`、`LINKFLAGS_EXTRA` 的 `-Wl,-rpath,<libdir>`、`LD_LIBRARY_PATH`（append）、`PYTHONPATH`（stdlib + lib-dynload + `_scons_env`，修复 gem5py 嵌入工具 `No module named 'zlib'`）、`build()` 显式 `"<prefix>/bin/python3" -m SCons …`（经 `_ohos_shims/build_python.json` 传递，不再依赖 worker 的 `python3`）；
- `_patch_scons_posix_shell()`：pip 安装后把 posix.py 的 `env['SHELL']='sh'` 替换为 `'/system/bin/sh'`（幂等 + 失败即报错 + 清 `__pycache__`）；python3-config 与 cc shim 的 shebang 同步改 `/system/bin/sh`；
- `test_package/test.sh` 加固（不属于 recipe revision）：`readelf` 增加绝对路径回退、`TMPDIR` 不可写时回退 `$HOME/tmp`；
- 既有 5 补丁/兼容头/zlib/SHELL/TMPDIR 逻辑保持不变。

**本地验证**：
- 候选解析单测：conan python ACCEPT（3.12.9）／hnp python ACCEPT（3.12.8）／伪造“无头”前缀 REJECT／“有头无 libpython”前缀 REJECT；
- shell 机理对照复现（受限 PATH 无 sh）：修复前 `LINK_OK=0 HEADER_OK=0`（config.log `FileNotFoundError: 'sh'`）→ 修复后 `LINK_OK=1 HEADER_OK=1`；
- gem5py 嵌入解释器复现：无 stdlib PYTHONPATH 时 `ModuleNotFoundError: No module named 'zlib'`（首次 W3 实测失败点）；加 `<prefix>/lib/python3.12:(lib-dynload)` 后真实 gem5py 成功生成 marshal 输出；
- 全量 W3：`finish gem5 25.1.0.1 built`（W3 使用独立 revision、全量重建 73 分钟；配置期 `Python.h yes`、`Python version 3.12.9`、`-Wl,--as-needed yes`；test_package 真机 SE 冒烟 4/4 断言通过）→ `.ci-result.json exit_code=0`（log_sha256 `cc9721ad9d11732eb0e1547d2ad9b390786b8d635a324c62304e9cefce8112f7`）。
