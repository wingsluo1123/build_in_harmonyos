# inotify 4.25.9.0 适配笔记

## 编译环境
- 构建系统: makefile（conanfile.py 手写极简 Makefile 直接编译；上游 Autotools 链需 aclocal，CI/真机缺失不可用）
- 编译日期: 2026-10-14
- 编译器: clang/clang++
- 状态: built（待真机预检回填实测计数）

## 编译步骤

1. `conanfile.py source()` 从官方 GitHub tag 包获取源码（strip_root=True）。
2. `conanfile.py build()` 手写 `config.h`（OHOS 实测：sys/inotify.h 可用，sys/fanotify.h 不可用）与 `inotify.h`/`fanotify.h` shim（前者转含 `<sys/inotify.h>`，后者 `#undef LINUX_FANOTIFY` 并回退 bundled `fanotify-dfid-name.h`），未注入 `#ifdef __OHOS__`。
3. 手写极简 Makefile 到 build_folder：编译 `libinotifytools.a`（inotifytools/redblack/stats）与 `inotifywait`/`inotifywatch`，`make -f <build>/Makefile -j1 all`（R9 单作业）。
4. 构建上游单元 `libinotifytools/src/test`（test.cpp 直编直链）并运行；逐个按各自 shebang（bash/sh）运行 14 个 sharness 集成脚本；按各用例退出码计数产出 `HMBS_UPSTREAM_TEST_RESULT`（注册总数 15 = 1 unit + 14 .t）。
5. `make -f <build>/Makefile install PREFIX=staging` 后 copy 到 package_folder；test_package 以 CMake 构建 `test_inotify` 并运行 6 项 CHECK-OK，外加 `inotifywait` create 事件功能驱动 1 项，产出 `HMBS_TEST_PACKAGE_RESULT`（共 7 项）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `autoreconf -fi` 缺 aclocal，autotools 链死路 | CI/真机无 automake 套件，上游亦无预生成 configure | 手写极简 Makefile + config.h 直接编译（与 inotify-tools/4.25.9.0 同源验证过的方案同构） |
| 2 | 上游 `#include "inotifytools/inotify.h"` 构建树缺失 | 该头由 configure 按 sys/inotify.h 探测生成 | 手写 shim 转含 `<sys/inotify.h>`（OHOS sysroot 实有） |
| 3 | 上游 fanotify 路径引用 `fanotify_init`/`fanotify_mark` | OHOS 未实现该 syscall wrapper，`LINUX_FANOTIFY` 分支会编入不可用调用 | 手写 `fanotify.h` shim `#undef LINUX_FANOTIFY` 并含 bundled fallback；`config.h` 不定义 `HAVE_SYS_FANOTIFY_H` |
| 4 | 上游测试 `/tmp` 硬编码与 watch `/` 权限 | 真机 `/tmp` 只读、根目录 watch 受限（与 inotify-tools 历史 notes 同类） | 不修改上游测试；失败按 rule4 以 `ohos_feature`/`test_failure` gaps 如实上报，计数来自真实退出码 |
| 5 | 真机 `make: /data/service/hnp/bin/clang++: No such file or directory`（Error 127） | 配方无条件信任 `tools.build:compiler_executables` 绝对路径，真机该目录已失效 | 新增 `_is_runnable/_pick/_resolve_tools`：绝对路径须通过 `--version` 试运行才采用，否则按 `CC/CXX/AR` 环境、`clang/clang++/gcc/g++`、`llvm-ar/ar` 回退，并导出环境变量双保险；make 优先 `HMBS_MAKE`/`user.hmbs:make_path` |
| 6 | 真机 `package()` 的 `install -d` 报 Error 64（EX_USAGE） | 手写 Makefile 用了多参 `install -d/-m`，HMBS install shim 只接受单文件两参调用，且 `HMBS_CAP_CHMOD=0` 使 `install -m` 不可用 | install 目标改用 `mkdir -p` + `cp -f`，不再调用 `install(1)` |
| 7 | 真机单元测试构建 `[UNIT-BUILD-ERROR] Error 1` | 手写 `config.h` 误定义 `HAVE_MCHECK_H 1`，而 `test.cpp` 在此宏下 `#include <mcheck.h>`（glibc 专有，OHOS sysroot 缺失）；主库从不包含它故编译通过 | `config.h` 不再定义 `HAVE_MCHECK_H`；单元编译改走 subprocess 捕获，诊断写入日志与证据 |
| 8 | 两个上游 `.t`（cookie/null）为 `#!/bin/bash` 且用 `[[ ]]`，在真机 `SHELL=/bin/sh` 下被强制以 sh 执行必败 | harness 未尊重上游 shebang | 按文件首行 shebang 选择解释器（bash 存在则用 bash，否则记录并沿用默认 shell）；计数仍只看退出码，证据优先取 `not ok/failed/error` 行 |
| 9 | 真机 test_package 的 CMake configure 用 `CMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++` 报缺失 | `CMakeToolchain` 把 `tools.build:compiler_executables` 绝对路径烘焙进 `conan_toolchain.cmake`，真机该路径已 stale（与 libnl3 经验同类） | test_package 改用显式 `CMakeToolchain(self).generate()`，落盘后把不可运行的编译器路径替换为试运行通过者并导出 `CC/CXX` 双保险（经验 1 的直接应用） |
| 10 | 上游单元 watch `/` 报 `EACCES`、`mkdir /tmp/...` 失败；dir 系 `.t` 含 `cp log /tmp/` | 预检沙箱限制：`/tmp` 不可写（HMBS 为此注入独立 TMPDIR）、根目录 watch 被拒、无 bash | 不改上游测试；harness 以在机探针（/tmp 写探针、which bash）+ 用例输出/内容自动归类 `environment`，其余保留 `test_failure`，计数仍唯一来自退出码 |
| 11 | 真机 test_package `CMake Generate step failed: links to inotify::inotifytools but target was not found` | `package_info()` 仅设 `libs=["inotifytools"]` 未声明 CMake 目标名，CMakeDeps 默认目标为 `inotify::inotify`，与 `test_package/CMakeLists.txt` 的 `inotify::inotifytools` 不一致 | `package_info()` 增 `cmake_file_name=inotify`、`cmake_target_name=inotify::inotifytools`（+ `pkg_config_name`），使 `find_package(inotify)` 提供测试链接的目标；不改 CMakeLists 链接名 |
| 12 | 两个 `--no-dereference` symlink 用例以泛化 `test_failure` 上报缺具体技术原因 | 一为 watch 链接后 touch 目标期望超时 exit 2，一为 `touch -h` 链接本身期望 exit 0，在机以相反期望同时失败，指向内核/HMFS symlink 事件语义差异而非配方 | harness 将 `no-dereference` 失败单列 `ohos_feature` gap，写明 `touch test` vs `touch -h test-symlink` 与期望 exit 2 vs 0 及在机输出证据；不改上游测试、不伪造通过 |

## 源码修改

- 无 patches（`conandata.yml patches: []`）：fanotify 禁用与 config 探测替代均在 `conanfile.py build()` 内手写文件完成，未改上游源码、未引入平台宏。

## 依赖版本

- 无外部依赖（仅 libc/libc++）。

## 验证结果

- 待真机预检回填：`conan create` 日志中的 `HMBS_UPSTREAM_TEST_RESULT`（15 注册项）与 `HMBS_TEST_PACKAGE_RESULT`（7 项）实测计数。
- 本地未运行 conan（按任务守则，W3 改为真机执行；除 rsync/ssh 外不在本机运行 conan）。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libinotifytools.a | 静态库 |
| bin/inotifywait, bin/inotifywatch | 命令行工具 |
| include/inotifytools/ | 公共头 |

## 注意事项

- 包名 `inotify` 取自任务要求路径 `archives/i/inotify/4.25.9.0`；上游仓库为 `inotify-tools/inotify-tools`（同源另有 `inotify-tools/4.25.9.0` 归档，本包为任务指定的独立包名实现，构建逻辑同构并补齐 rule4 机器证据标记）。
- OHOS 支持 inotify 核心（init/add_watch/next_event），fanotify 不可用。
- 真机与命令属内部基建，本笔记记录的真机细节不写入 PR 正文；正文统一写「在 HarmonyOS aarch64 环境实测」。
