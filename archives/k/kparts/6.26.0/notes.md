# kparts 6.26.0 — HarmonyOS PC 适配说明

## 1. 交付物

| 项目 | 内容 |
|------|------|
| 上游 | KDE Frameworks 6 — kparts 6.26.0（`https://download.kde.org/stable/frameworks/6.26/kparts-6.26.0.tar.xz`，sha256 `049c2cf048b4cbbffe0bea9357bd9ab53b8be672ba509b2bb058f764d21b3f5b`） |
| 产物 | `libKF6Parts.so.6.26.0`（ELF64 AArch64，含 DT_SONAME `libKF6Parts.so.6` 与 `.so`/`.so.6` 版本化软链）、KF6Parts 头文件 17 个、`KF6PartsConfig.cmake` |
| 配方 | `conanfile.py`、`conandata.yml`、`manifest.yaml`、`patches/0001`、`patches/0002`、`patches/0003`、`test_package/`（含 `MANIFEST.yml`） |
| 适配路径 | 路径 A（基础适配） |

## 2. 依赖选型（关键决策，含被否决路线的实测依据）

ohpcd 制品仓现状（`conan list -r ohpcd` 实测）：

- **kio/6.26.0 是 `KIOCORE_ONLY` 构建**（无 KIOWidgets 目标、无 `KUriFilter` 头、`include/KF6/KIO/` 只剩 `kio_version.h`）；**含 KIOWidgets 的全栈包只有 kio/6.14.0**。
- KF6 6.26 系列里已发布的组件：kconfig/kcoreaddons/ki18n/kservice/kwidgetsaddons/kxmlgui/kjobwidgets/kio(仅 core) 等；**kconfigwidgets/6.26.0 未发布**（最新 6.18.0），kbookmarks 也只有 6.14.0/6.18.0。

kparts 6.26 的 `src/navigationextension.cpp` 仍**真实调用 KIOWidgets** 的 `KUriFilter::self()` / `KUriFilterData`，`src/CMakeLists.txt` 仍链接 `KF6::KIOWidgets`。三条路线：

| 路线 | 做法 | 结果 |
|------|------|------|
| A | KF6 6.26 全栈 + kio/6.26.0（KIOCORE_ONLY） | ❌ 不可行：kparts 需要的 `kio/filecopyjob.h`、`KUriFilter` 头与 `KF6::KIOWidgets` 目标在 KIOCORE_ONLY 包中都不存在（6.18.0 配方已实测编译失败，本轮复查 kio/6.26.0 配方确认仍为 KIOCORE_ONLY） |
| B | KF6 6.26 系列 + kio/6.14.0（`override=True`） | ❌ **本轮实测**：`conan graph info` 直接返回 `error: conflict`——kparts 要 `kcoreaddons/6.26.0`，而 `kconfigwidgets/6.26.0` 未发布、被解析到 `kconfigwidgets/6.18.0`（要求 `kcoreaddons/6.18.0`），图根本无法解析（rc=1）。6.18.0 配方记录的另一阻塞仍然成立：即便绕过该冲突，kio 也会被强制从源码重建，其 `kioworkers/trash/trashimpl.cpp` 依赖 `<solid/block.h>`，已发布 solid 包只安装 `include/KF6/Solid/Solid/block.h`（大小写不匹配） |
| C（采用） | **整图使用已发布的 KF6 6.14.0 系列**（qtbase/6.11.1 + kconfig/kcoreaddons/ki18n/kservice/kwidgetsaddons/kxmlgui/kjobwidgets/kio 6.14.0，`tool_requires ecm/6.26.0`）+ 仅放宽本库 `KF_DEP_VERSION` | ✅ `conan graph info` 实测 0 冲突；`conan create` 实测**依赖 0 源码重建**：主构建阶段 24 个 KF6/KIO/ECM 相关包从 ohpcd 下载已发布二进制，qtbase/libxml2/zlib/bzip2/gettext/openssl 直接命中本地缓存；`Calling build()` 只出现 `kparts/6.26.0` 与 `(test package)` 两处 |

KF6 在同一大版本内保持 API/ABI 兼容，kparts 6.26 使用的全部 KF6/KIO API 在 6.14.0 中均存在（实测编译与测试全通过）。

## 3. 补丁说明

| 补丁 | 内容 | 原因 |
|------|------|------|
| `patches/0001-lower-cmake-and-kf-dep-version.patch` | 顶层 `CMakeLists.txt` 两处版本门限：① `cmake_minimum_required(VERSION 3.29)` → `3.22`；② `set(KF_DEP_VERSION "6.26.0")` → `"6.14.0"`（均附注释） | ① OpenHarmony SDK build-tools 自带 CMake 为 **3.28.2**（本轮实测 `/root/ohpc/sdk/ohos-6.0/native/build-tools/cmake/bin/cmake --version`），上游 3.29 门限会让 configure 硬失败；该门限只是发布脚本默认值，代码未用 3.29 专有命令。② 本库依赖版本门限须与 ohpcd 实际发布的 6.14.0 系列一致，否则 `find_package(KF6 6.26.0 REQUIRED)` 找不到 KIOWidgets |
| `patches/0002-lowercase-kio-includes-readonlypart.patch` | `src/readonlypart.cpp`：`<KIO/FileCopyJob>`→`<kio/filecopyjob.h>`、`<KIO/StatJob>`→`<kio/statjob.h>` | kio/6.14.0 把 KIO 头安装在 `include/KF6/KIOCore/kio/`（全小写）。OHPC CI 构建机文件系统大小写不敏感，但本地/其它环境（ext4）大小写敏感 → 不改写则构建不可移植。声明完全相同，无行为变化 |
| `patches/0003-lowercase-kio-includes-readwritepart.patch` | `src/readwritepart.cpp`：`<KIO/FileCopyJob>`→`<kio/filecopyjob.h>` | 同上 |

三处补丁均为 `patch_type: portability`，不改变库的任何对外行为。

## 4. 构建与测试要点

- `KF_IGNORE_PLATFORM_CHECK=TRUE`：OHOS 不在 KDE 平台白名单内。
- `BUILD_TESTING=ON`：上游 `autotests/` 原样构建，`build()` 内经 `ctest --output-on-failure --no-tests=error` 真实执行；GUI 用例以 `QT_QPA_PLATFORM=offscreen` 运行。
- **上游 6.26 新增的 `tests/` 目录**（`kpartstest`、`normalktmtest`、`partviewer`、`terminal_test`）是交互式手工测试程序（`QApplication` 常驻主循环，无 QTest 断言、无 `add_test` 注册；上游用 `ecm_mark_as_test` 只做"仅在 BUILD_TESTING 时构建"的门禁，不注册进 ctest）。本轮这 4 个程序**照常编译并通过链接**，但不计入上游用例数（`ctest -N` 注册数 = 2）。
- `CMAKE_CXX_STANDARD=20`：KF6 头文件使用 C++20 特性，而 `ohos-aarch64` profile 固定 cppstd=17。
- `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG=-Wl,-soname,`：CMake 无 `Platform/HarmonyOS` 模块，需显式注入，产物才有 DT_SONAME 与版本化软链（kio/kfilemetadata/baloo 先例）。实测 `readelf -d`：`Library soname: [libKF6Parts.so.6]`，全部 `NEEDED` 为裸库名。
- `ECM_MODULE_PATH` 与 `conan_cmakedeps_paths.cmake`：CMakeDeps 生成的 `ECMConfig.cmake` 不传 `ECM_MODULE_PATH`；qtbase 使用 `cmake_find_mode=none`，需手动补 `CMAKE_PREFIX_PATH`。
- **运行库闭环**：已发布 KF6 包的 `DT_NEEDED` 有两种 musl 无法自行解析的形态——① 绝对烙印路径（发布机 conan 缓存 `/storage/Users/currentUser/.cache/conan2/p/<hash>/p/lib/…`）；② 相对路径（如 `../../bin/libKF6ConfigCore.so`，musl 对含 `/` 的 `DT_NEEDED` 按进程 CWD 解析，`LD_LIBRARY_PATH` 无效）。OHOS 内核对 ELF 做代码签名校验，改写副本会被拒绝，故配方用**软链接**补齐（软链不改变目标文件内容，签名保持有效；平台知识库 PR #9573 先例）。实现见 `conanfile.py::_prepare_runtime_closure()`。本轮实测：上游 ctest 阶段与 test_package 阶段分别自动生成所需软链（test_package 日志 `runtime closure: 8 symlink(s) created`）。
- 编译告警（上游代码，非本配方引入，如实记录）：`readonlypart.cpp:181`、`readwritepart.cpp:209`、`readwritepart.cpp:247` 共 3 处 `-Wunused-result`（nodiscard 返回值被忽略）。

## 5. 实测结果（真实数据）

环境：WSL2 Ubuntu 22.04 + OpenHarmony 6.0 SDK（CMake 3.28.2）+ `ohos-qemu-aarch64`，profile `ohos-aarch64-run` / `-pr:b default`，时间 2026-10-15 14:01:36 → 14:03:24（`conan create` 全程 1 分 48 秒）。

| 项目 | 命令 | 结果 |
|------|------|------|
| 端到端构建 | `conan create archives/k/kparts/6.26.0 -pr:h ohos-aarch64-run -pr:b default -c tools.build.cross_building:can_run=True --build=missing` | ✅ `Package '5522206cb3817ff7a8e3ab80ba84eef59742b858' created`（CONAN_RC=0；依赖 0 重建） |
| 上游测试 | `ctest --test-dir <build> --output-on-failure --no-tests=error`（qemu） | ✅ **100% tests passed, 0 tests failed out of 2** |
| 上游 QTest 明细 | `ctest -V` | ✅ `parttest`：**Totals: 12 passed, 0 failed**（772ms）；`partloadertest`：**Totals: 8 passed, 0 failed**（196ms）；合计 **20/20** |
| 消费者端到端 | test_package `test_kparts`（qemu） | ✅ `RESULT: kparts 6.26.0 consumer end-to-end: 15/15 checks passed`（1 个场景 / 15 项断言） |
| 产物形态 | `file` / `readelf -h` / `readelf -d` | ✅ `ELF 64-bit LSB shared object, ARM aarch64`；`SONAME: libKF6Parts.so.6`；17 个头文件 + `KF6PartsConfig.cmake` |
| 原生预演（鸿蒙 PC） | `pc\pc.ps1 status` | ❌ **本轮未执行**：`pc.ps1 status` 实测 `SSH(192.168.137.45:8022) = FAIL(rc=255) Connection timed out`（hdc 能看到设备 `450100445634303332018f3e7d2dba00`，但 SSH 用户态不可达；`tools\pc_target.ps1 -Refresh` 全网段探测也未发现可达地址）。按作业书记录为环境缺口，下一轮 PC 恢复后补跑 |
| 真机端到端 | `pc\pc.ps1 run` / 同上 | ❌ **本轮未执行**：同上（PC SSH 不可达）；WSL 侧 qemu 端到端已通过 |

## 6. 已知边界

- 远程 URL 路径（`openRemoteFile` / KIO job）需要 `kioworker` 子进程与 DBus 会话，qemu 沙箱不测试该路径；本次消费者端到端用例基于**本地文件路径**（库内同步分派，`openUrl`→`openFile`→信号→`closeUrl` 全链路真实文件 I/O）。
- kparts 为纯库（无 `bin/` 产物），按 R38 不需要 `commands.json`。
- 运行库软链接只补齐"缺失路径"，幂等；不修改 conan 缓存、不修改依赖包，仅在本库构建树 / 测试 payload 内创建。
- 原生预演与真机证据本轮缺失（PC SSH 不可达），配方尚未在鸿蒙 PC 原生语义下复验；CI 为同源环境，以平台 CI 为准。

## 7. 证据文件

| 文件 | 说明 |
|------|------|
| `outputs/kparts-evidence/local_validate_conan_create.log` | 本地端到端 `conan create` 全量日志（含上游 ctest 与消费者测试输出） |
| `outputs/kparts-evidence/upstream_ctest_verbose.log` | 上游 ctest `-V` 日志（QTest `Totals:` 与逐用例 `PASS :` 明细，rule4 依据） |

> 上述日志为**本地留存**（`outputs/` 不在仓库内、不随 PR 入库）；PR 正文中的每个数字都可在该日志里逐行复现。
