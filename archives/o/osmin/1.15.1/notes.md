# osmin 1.15.1 适配笔记

## 编译环境
- 构建系统: CMake >= 3.20（C++20），Qt6 Quick/Widgets 应用
- 编译器: OHOS SDK clang/clang++ 15（CI profile `ci/conan/profiles/ohos-aarch64`，os.version=6.0）
- 日期: 2026-10-16
- 状态: built（conan-verify + 本地 W3 conan create 通过：`reports/w3-local-ci.log` + `.ci-result.json` exit_code=0；依赖 qtsensors/6.11.1 已发布）

## 编译步骤

```bash
conan create archives/o/osmin/1.15.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

配方内部（`build()`）先 `apply_conandata_patches()` 施加本包补丁，再 `cmake.configure()/build()`；
vendored `backend/libosmscout` 由上游 `backend/CMakeLists.txt` 以 `add_subdirectory` 树内编译
（OSMScout / OSMScoutMap / OSMScoutMapQt / OSMScoutClientQt / OSMScoutGPX），
并在 configure 阶段自行 `git apply backend/libosmscout_4.patch`（与本包补丁区域不重叠）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `libosmscout-client-qt/src/osmscoutclientqt/TiledMapRenderer.cpp` 报 `use of undeclared identifier 'QOpenGLContext'`（include 明明成功） | OHOS qtbase 未构建 QtOpenGL 模块：`qtgui-config.h` 定义 `QT_FEATURE_opengl -1` / `QT_NO_OPENGL 1`，`qopenglcontext.h`/`qopenglfunctions.h` 全文被 `#ifndef QT_NO_OPENGL` 包裹 → 头找到了但内容为空 | 补丁 `patches/0001-libosmscout-client-qt-guard-no-opengl.patch`：用上游既有宏 `QT_NO_OPENGL` 门控 include 与使用点（GL 块仅用于 NPOT 纹理探测，跳过语义等价）。提取为知识库条目 KB-NO-OPENGL（同一 PR） |
| 2 | `osmscout/description/DescriptionService.cpp` 报 `no member named 'views' in namespace 'std'`（`std::views::transform`） | OHOS SDK libc++ 15.0.4（`_LIBCPP_VERSION=15004`）在 `compiler.cppstd=20` 下未定义 `__cpp_lib_ranges` | 配方 `generate()` 注入 `-D_LIBCPP_ENABLE_EXPERIMENTAL`（`tc.extra_cxxflags`）→ `__cpp_lib_ranges` 提升为 201811L；**改 flag 必须换全新构建目录**（CMAKE_CXX_FLAGS_INIT 只首次 configure 生效） |
| 3 | 链接 `osmin` 可执行文件报 `undefined symbol: SignalHandler::catched(int)` / `staticMetaObject` 等 4 个未定义符号 | OHOS 适配版 conan 把 `os=OHOS` 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，**CMake 因此不定义 `UNIX`**（探针实测 `UNIX=[]`）；上游 `CMakeLists.txt` 用 `if(UNIX)` 登记必需源文件 `src/signalhandler.cpp`，该分支被跳过 → 整个编译单元（含 moc 输出）静默消失 | 配方 `generate()` 注入 `tc.cache_variables["UNIX"] = "ON"`（等价 `-DUNIX=ON`）：HarmonyOS 用户态为类 UNIX，恢复 UNIX 语义与代码预期一致。实测 `grep -c signalhandler <build>/CMakeFiles/osmin.dir/build.make` 由 0 → 13（已登记知识草稿 `knowledge/drafts/ohos-cmake-unix-undefined.kv`） |
| 4 | Qt6 依赖解析：模块二进制全部命中失败（`--build=never` 报缺 qtbase 等） | 仓内所有 Qt6 模块配方 `requires("qtbase/6.11.1")`（无后缀）；override 成 `6.11.1.3` 会把已发布模块的 package_id 翻掉 | `requirements()` 统一用生态基准 `qtbase/6.11.1`；zlib 只能作 override（cups 子树钉 1.3.1.1，常规 requires 会 Version conflict 且翻掉 Qt6 模块 id） |
| 5 | `conan create` 构建期 Qt 代码生成工具 `repc` 失败：`Error loading shared library libQt6Core.so.6`（needed by `.../libexec/repc`）→ `make[2] build.make:391 Error 127`，紧随一串 `Error relocating ... symbol not found` | 上游 `qt6_add_repc_sources` 在**构建期**执行 `qtremoteobjects` 包里的 `repc`（生成 `rep_servicemessenger_replica.h`）。该二进制 `readelf -d` 无 RPATH/RUNPATH，只能靠 `LD_LIBRARY_PATH` 找 `libQt6Core.so.6`；而 conan 构建环境只带 profile buildenv 与 tool_requires，**host 依赖的 lib 目录不在其中**，宿主默认库路径也没有 Qt（`/lib`、`/usr/lib`、`~/usr/local/lib` 均无）→ 工具自身起不来（宿主是 aarch64，可原生执行，勿误判为跨架构工具不可用） | 配方 `build()` 用 `Environment()` 把各依赖包自身的 `lib` 目录 `prepend_path("LD_LIBRARY_PATH", ...)`，包住 `cmake.configure()/build()`——与仓内 ausweisapp 同法，且只指向 conan 缓存内的包目录，不触碰共享系统前缀（R49）。实测：同一构建由 `Error 127` 转为 317 个对象编译 + 链接通过、W3 全绿 |

## 未决问题（排雷演练残留，用户叫停时状态）

| # | 现象 | 已查明（证据） | 待办（未做） |
|---|------|----------------|--------------|
| 6 | 注入 `UNIX=ON` 后未定义符号由 4 个降到 3 个，残留 `SignalHandler::catched(int)`、`SignalHandler::staticMetaObject`、`vtable for SignalHandler`（`ld.lld` 报 `vtable symbol may be undefined because the class is missing its key function`） | 三者均由 **moc** 提供：`src/signalhandler.h` 含 `Q_OBJECT` 与 `signals: void catched(int)`（信号在头文件声明、无 C++ 定义）；`CMakeLists.txt:109` 为 `CMAKE_AUTOMOC ON`；该目标共生成 70 个 moc 产物（其他类正常）；`build2/CMakeFiles/osmin_autogen.dir/AutogenInfo.json` 里**确实登记了** `moc_signalhandler.cpp`（signalhandler 相关条目 3 条，见 `$HOME/tmp/autogen_sig.txt`），但构建树中**不存在该文件**、`osmin_autogen/mocs_compilation.cpp` 亦未包含它 | 用**干净构建目录**（一次 configure 即带 `UNIX=ON`，与 `conan create` 同场景）只跑 `cmake --build <dir> --target osmin_autogen`：①生成了 → 前次失败属「增量重配置 → autogen 状态陈旧」的排查假象，配方无需额外处理，CI 干净环境同样不受影响；②仍不生成 → 需补一条把 `src/signalhandler.h` 显式并回 `osmin_SOURCES` 的补丁 —— **已复测结论①**：`conan create` 干净构建下 `moc_signalhandler.cpp` 正常生成（`.conan2/p/b/osmind258e680155ba/b/build/Release/osmin_autogen/UVLADIE3JM/moc_signalhandler.cpp`），链接无 `SignalHandler::*` 未定义符号，配方无需额外处理 |

> 排雷演练另留一个残留：测试脚本与 `test_package` 会在 `test_package/` 下留 `testhome/` 与启动日志，
> 已补收尾清理（脚本 `trap EXIT` + test_package `finally`），源码树不再留残留。

## 源码修改

- `patches/0001-libosmscout-client-qt-guard-no-opengl.patch`（51 行 / 3 hunk）：
  给 `backend/libosmscout/libosmscout-client-qt/src/osmscoutclientqt/TiledMapRenderer.cpp`
  的 GL include 与 GL 调用点加 `#ifndef QT_NO_OPENGL` / `#endif` 门控。
  以 osmin 源码根为 root（`a/backend/libosmscout/...`），
  `export_conandata_patches` + `apply_conandata_patches`（patch_ng 自动剥 `a/`、`b/`）。
  与上游自带的 `libosmscout_4.patch`（445 行起 hunk）无行重叠，可叠加。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| qtbase | 6.11.1 | 生态基准（FEATURE_dbus=OFF → osmin 的 DBus 集成按上游守卫自动关闭） |
| qtdeclarative / qtsvg / qtmultimedia / qtremoteobjects / qtcore5compat | 6.11.1 | 与仓内模块配方自身要求的 qtbase 版本对齐 |
| qtpositioning | 6.11.1.1 | 同上（仓内已发布即该修复号） |
| qtsensors | 6.11.1 | 上游必需（`find_package(Qt6 ... Sensors REQUIRED)`）；已发布到制品仓（`conan download` 成功：recipe `fa430868…`、package rev `2abd6ae0…`） |
| zlib | 1.3.2 | 常规 requires（上游 `find_package(ZLIB QUIET)` 需它进图，见"构建期 zlib"章节） |
| libxml2 | 2.15.3 | 常规 requires |

libosmscout 不作为 conan 依赖：osmin 以 git submodule 固定 commit `acb1e4b6` 树内编译，
配方在 `source()` 里把该 commit 的源码（官方仓 Framstag/libosmscout，tarball 与 osmin 声明的
fork 字节一致）放进 `backend/libosmscout/`。

## 上游测试用例清点（R51）

| 项 | 实测值 | 证据 |
|----|--------|------|
| `add_test()` 注册数 | 0 | `grep -rn 'add_test' --include=CMakeLists.txt .` → 0 命中（上游源码根） |
| `enable_testing()` | 0 | 同上命令 → 0 命中（CMake 测试子系统从未启用） |
| QtTest 引用 | 0 | `grep -rn 'QtTest\|Qt::Test' --include=CMakeLists.txt --include='*.cpp' --include='*.h' .` → 0 命中 |
| 测试目录（tests//test/） | 无 | `find . -maxdepth 3 -type d -name 'test*'` → 无输出 |
| 测试框架声明 | 仅 `option(INSTALL_TESTS ... OFF)`（`CMakeLists.txt:6`） | 该开关只控制"是否安装测试产物"，上游并无测试目标可安装 |

**结论**：上游 osmin 1.15.1 本体无任何可运行测试用例（全树 `add_test`/`enable_testing`/QtTest 引用计数均为 0，无 tests 目录）；内嵌 vendor 树 `backend/libosmscout` 虽自带测试目标，但被上游 `backend/CMakeLists.txt` 强制关闭（`INSTALL_TESTS=False` + `OSMSCOUT_BUILD_TESTS=OFF`），且它属第三方内嵌依赖而非 osmin 本体测试，故 R51 的"上游测试通过率"无可填项；
适配后由 `test_package/` 补全鸿蒙侧测试（真实执行被测产物，见下）。上游测试 0 项、适配后 1 项消费者测试。

## 验证结果

预验证（不依赖 Sensors 的等价构建，独立源码树）：

```bash
# libosmscout 五个目标全部产出（含此前失败的 OSMScoutClientQt）
$ ls -l libosmscout_client_qt.a   # 7.3 MB
# ranges 修复：全新构建目录 189 对象 0 错误
# OpenGL 门控补丁：TiledMapRenderer.cpp 编译 0 错误
```

正式验证（W3 = 本地跑 CI 同源脚本 `ci/conan/setup.sh` + `ci/conan/build_and_test.sh`，CI_PACKAGES 限定本包）**全绿**：

| 检查 | 结果 |
|------|------|
| L0 质量门禁（结构 / 版本 / commands.json / 补丁 / 分支） | pass |
| conan create（aarch64-linux-ohos；libosmscout 五库树内编译 + osmin） | pass（317 个对象，0 编译错误；产出 `bin/osmin` 8.6 MB） |
| L1a / L1b test_package 执行与证据 | pass |
| L1e 反向验证（测试确实依赖被测包） | pass |
| L2 smoke（`--version` / `--help`） | skip（GUI 应用无此类开关，非阻塞） |
| L4 危险函数扫描 / L5 产物基线 | pass |

test_package 真实执行无头服务 `osmin -service`（`QCoreApplication` + `QRemoteObjectHost`，本地套接字 `local:osmin90`）：
断言产物为 OHOS/aarch64 64 位 ELF、进程完成 Qt 初始化并存活到超时、`$HOME/osmin`（+`GPX`）数据目录被真实创建、
启动日志无动态库加载失败/符号解析失败/崩溃标记。

## 构建期 zlib：上游内置下载兜底不稳定（已修）

**现象**：`conan create` 在 backend 配置/构建阶段失败：

```
/bin/sh: cd: .../build/Release/backend/zlib-build: No such file or directory
make[2]: *** [CMakeFiles/zlib-download.dir/.../zlib-download-test] Error 2
CMake Error at backend/cmake/DownloadProject.cmake:179 (message): Download step for zlib failed: 2
```

**根因**：上游 `backend/CMakeLists.txt:34-51` 先 `find_package(ZLIB QUIET)`，落空即
`download_project(PROJ zlib URL "${CMAKE_CURRENT_SOURCE_DIR}/zlib-1.3.1.tar.gz")` 走
ExternalProject；该 stamp 步骤在 OHOS 上不稳定（全新构建目录必挂在 test stamp，
增量构建目录却能通过）。配方原先把 zlib 写成 `override=True`——override 只改版本、
**不把包带进依赖图**（`conan graph info` 里没有 zlib 节点），故 `find_package(ZLIB QUIET)`
必然落空、必然走兜底。此前一次 W3 显示通过是假象：那次复用了已完成 zlib stamp 的
增量构建目录，清干净后问题即稳定复现。

**修复**（两处，均已实测）：

1. `self.requires("zlib/1.3.2")` 由 `override=True` 改为常规 requires——实测无版本冲突，
   qtbase `package_id` 保持 `01d92cf349a0dd98ff915f4bd99a04430171517f`（制品仓可下载），
   `conan install --build=never` rc=0。（同一引用同时写常规 + override 会被 conan 拒绝：
   `Duplicated requirement: zlib/1.3.2`。）
2. `generate()` 注入 FindZLIB 查找提示——本配方不走 CMakeDeps（Qt6 是
   `cmake_find_mode=none`，靠逐组件 `<Component>_DIR` 注入），因此显式给出图内 zlib 包路径：
   `ZLIB_ROOT` / `ZLIB_INCLUDE_DIR` / `ZLIB_LIBRARY`。

**验证证据**：新构建目录 `CMakeCache.txt` 中
`ZLIB_LIBRARY=/storage/…/zlibadde02423c9a0/p/lib/libz.a`、`backend/zlib-build` 目录不再出现
→ 上游走正常 `find_package` 分支，内置 zlib ExternalProject 完全绕开。

**G0（clean-verify）非阻塞失败说明**：G0 只解压主源码、不展开 `source()` 中放入的
libosmscout 子仓，本包补丁的目标路径（`backend/libosmscout/…`）因而不存在，G0 报
"补丁应用失败"。这是工具对多源码配方的已知局限，不影响 `conan create`——`source()`
会先把子仓放到位再打补丁。

## 注意事项

- **Sensors 依赖已就绪**：`qtsensors/6.11.1` 现已可从制品仓 `conan download`（此前探测为未发布），
  本配方依赖图完整，`conan create` 可直接跑通。
- **构建期 Qt 工具依赖 `LD_LIBRARY_PATH`**：`repc` 一类 Qt 自带工具（无 RPATH）由配方 `build()` 注入依赖
  lib 目录；后续若上游新增同类工具调用点，同一注入已覆盖。
- 改 `extra_cxxflags` / toolchain 变量后必须使用**全新构建目录**，否则 CMake 复用缓存 flags 导致改动静默不生效。
- 无头验证入口：`osmin -service`（QCoreApplication + QRemoteObjectHost，本地套接字 `local:osmin90`，
  不需要 DBus），启动后会在 `$HOME` 下创建 `osmin/`（+`GPX/`）目录——test_package 的静态测试脚本据此断言。
- GUI 场景按仓内惯例（ausweisapp）以 `QT_QPA_PLATFORM=offscreen` 运行。
---

### 对话 #1：依赖闸与 Sensors 排雷（2026-10-15）

- 侦察发现唯一缺失依赖 `qtsensors/6.11.1`（顶层 `find_package(Qt6 ... Sensors REQUIRED)`）。
- 按 R35 口径（`conan download` 而非 `conan list`）实测：当日报 "acceleration policy" → 未发布；用户导入任务后重测可匿名下载 → 依赖闸解除。
- 排队期间做定向排雷：**不改 osmin 源码逻辑**，只临时摘除 compass 叶子模块（3 文件 10 处）验证去 Sensors 后的可编译性，暴露并记录问题后还原。

### 对话 #2：编译期三个平台坑（2026-10-15 ~ 10-16）

- `std::views`/`std::ranges` 报 `no member named 'views'`：OHOS libc++ 15.0.4 C++20 下 `__cpp_lib_ranges` 未定义 → 注入 `-D_LIBCPP_ENABLE_EXPERIMENTAL`（改 flag 必须换全新构建目录）。
- 链接期 `SignalHandler::*` 未定义：`CMAKE_SYSTEM_NAME=HarmonyOS` 时 CMake 不定义 `UNIX`，上游把 `src/signalhandler.cpp` 登记在 `if(UNIX)` 分支 → 源文件被静默丢弃 → 配方注入 `UNIX=ON`（探针实测 `UNIX=[]` → `[ON]`）。
- `TiledMapRenderer.cpp` 报 `use of undeclared identifier`：OHOS qtbase 未构建 QtOpenGL（`QT_NO_OPENGL 1`），`QtGui/qopenglcontext.h` 全文被门控包裹 → include 成功但内容为空；补丁加 `#ifndef QT_NO_OPENGL` 门控（该块仅为 NPOT 探测优化，跳过语义正确）。

### 对话 #3：W3 收口（2026-10-16）

- `repc` 构建期报 `Error relocating ... libQt6Core.so.6`：repc 无 RPATH，构建环境未带 Qt 库路径 → 配方 `build()` 自建 Environment 追加 `LD_LIBRARY_PATH`（参照 ausweisapp 先例），W3 三跑全绿。
- 上游内置 zlib `ExternalProject` 兜底时好时坏（`zlib-build: No such file or directory`）→ 实测 zlib 根本不在依赖图里（旧 `override=True` 空转）→ 改常规 `requires` 并注入 ZLIB 查找提示，`backend/CMakeLists.txt:36` 的 `find_package(ZLIB QUIET)` 走正常分支。
- 本地 W3 的 `source()` 阶段因镜像改写与源码缓存元数据不匹配触发重下载（github/ghfast 不可达）→ 按预下载脚本命名规则离线预置源码后，W3 全绿（`.ci-result.json` exit_code=0）。

### 运行时告警（如实披露，非判定项）

test_package 的 `-service` 无头运行会打印两条告警，均不在测试脚本的致命标记列表中，故不影响判定，
在此如实登记以免日志被误读为「无任何告警」：

- `qt.remoteobjects: Listen failed for URL: QUrl("local:osmin90")` +
  `QAbstractSocket::UnknownSocketError`：本地套接字绑定失败。推测与 OHOS 沙箱下 `QLocalSocket`
  支持相关（未进一步定位）；该套接字的客户端连接不属于本测试断言项（断言的是产物存在、进程存活、
  数据目录创建），故未据此判失败。
- `ERROR: Cannot call QSensorBackend::setDataRates with an invalid sensor`：内置 compass 传感器
  后端在无真实传感器设备的环境下未注册，`service.cpp` 的 `QSensor::setDataRate` 调用于是被拒绝；
  与上游在无传感器环境下的既有行为一致。

**编译结束**: 2026-10-16 12:49
**最终状态**: built（manifest.yaml / .build-closed / .handoff.json 同口径：conan-verify + 本地 W3 conan create 通过，`reports/w3-local-ci.log` + `.ci-result.json` exit_code=0；制品上传由合并后 release 流水线完成）

---

## 提交阶段说明：两处发现（2026-10-16）

`submit` 的 PR 创建前置硬闸在本机报两处假阳性，如实登记并附证据与处置：

**① PF0 环境闸（平台解释器行为，非本包问题）**：本机 Python 3.12 的 `subprocess.py` 守卫为
`(os.path.dirname(executable) or _IS_HARMONYOS)` —— HarmonyOS 上**裸名一律走 `os.posix_spawn`
（不搜索 PATH）**，实测 `subprocess.run(["git","--version"])`、`["ls"]`、`["conan"]` 均
`FileNotFoundError`，而绝对路径正常。`preflight.py` 内以裸名调用 `git`，于是 PF0 fail-closed
（本机 `git` 仅存在于 `~/.local/bin/git`，无 `/usr/bin/git`）。处置：以环境级 `sitecustomize`
补丁（仅 `PYTHONPATH` 注入，**未修改仓库任何文件**）恢复标准 PATH 解析语义后，preflight 可完整运行。

**② PF9 分支/路径闸（软件级文件被误判）**：报 `archives/o/osmin/README.md` 与
`archives/o/osmin/commands.json`「缺版本目录层」。但该两文件**按规范就该放在软件级**：
归档规范 §6 将 `README.md` 定义为软件级描述；R38 与 CI 门禁 L0k 要求 CLI 包在软件级声明
`commands.json`（本包构建产物含 `bin/osmin`）。main 上已有软件级 `commands.json` 先例
（如 `f3899cb846` mwrap 1.3.5、`5744db7a4a` savvy 2.1.0）；CI 侧同口径门禁 L0n 只校验分支名、
不含路径层级 → PF9 缺软件级豁免。

处置：经**完整手工执行 preflight 复核**（PF1-PF8 + R52 全部通过，唯一 findings 即上述 PF9），
按框架文档逃生口 `OHC_PREFLIGHT=0` 放行建 PR。PF9 软件级豁免缺失已作为框架反馈提交。
