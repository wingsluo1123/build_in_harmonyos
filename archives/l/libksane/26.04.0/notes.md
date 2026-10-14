# libksane 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake（KDE ECM 工程，project(KSane)）
- 编译日期: 2026-10-04
- 编译器: clang/clang++ 15.0.4（OHOS SDK，os=OHOS / arch=armv8）
- 状态: built（conan-verify G0-G4 全通过）

## 编译步骤

```bash
conan create archives/l/libksane/26.04.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

配方关键点：
- `KF_IGNORE_PLATFORM_CHECK=TRUE`：绕过 KDE 平台白名单（OHOS 不在列表）
- `KF_SKIP_PO_PROCESSING=ON`：跳过翻译目录生成
- `BUILD_TESTING=ON`：启用 CTest（上游 autotests 未注册用例，见下）
- `CMAKE_SHARED_LIBRARY_SONAME_*_FLAG`：CMake 无 HarmonyOS platform module，手动置 SONAME 使 libKSaneWidgets6.so 带 DT_SONAME（ksanecore 先例）
- 依赖注入：qtbase/6.11.1 + ki18n/6.18.0 + kwidgetsaddons/6.18.0 + ktextwidgets/6.18.0 + kwallet/6.18.0 + ksanecore/26.04.0 + tool_requires ecm/6.26.0
- `conan_cmakedeps_paths.cmake`：依赖均 `cmake_find_mode=none`，需手动把各依赖 lib/cmake 加入 CMAKE_PREFIX_PATH
- `KSANE_DEP_LIB_DIRS`：E537 可重定位链接（见下）

## 依赖版本选择（W0 制品仓探测结论）

| 依赖 | 制品仓可用版本 | 采用 |
|------|---------------|------|
| qtbase | 6.11.1 / 6.11.1.1~.3 / 6.12.0-beta3 | 6.11.1 |
| ki18n | 6.14.0 / 6.18.0(.1/.2) / 6.26.0 | 6.18.0 |
| kwidgetsaddons | 6.14.0 / 6.18.0(.1) / 6.26.0(.1) | 6.18.0 |
| ktextwidgets | **仅 6.14.0 / 6.18.0**（无 6.26.0） | 6.18.0 |
| kwallet | **仅 6.18.0** | 6.18.0 |
| ksanecore | 26.04.0（要求 ki18n/6.26.0） | 26.04.0 + ki18n override → 6.18.0 |
| ecm | 6.20.0 / 6.26.0 / 7.0.7 | 6.26.0 |

版本线决策：ktextwidgets 与 kwallet 只有 6.18.0 制品，而 ksanecore/26.04.0 要求 ki18n/6.26.0，二者在同一依赖图中冲突。
采用 **KF6 6.18.0 单版本线**，对 ki18n / kwidgetsaddons 使用 `override=True` 把 ksanecore 的 ki18n 降到 6.18.0；
ksanecore 因此无对应 binary，由 `--build=missing` 源码重建（其源码 URL/补丁均已在制品仓配方内，构建通过）。
若反向选 6.26.0 线，则需重建 ktextwidgets + kcompletion + kwallet（且 qtbase 需切 6.11.1.3，触发 libpng/1.6.58 vs 1.6.58.3 冲突），重建面更大，故不取。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接后 DT_NEEDED 记录 Conan cache 绝对路径（CI L5/E537） | 制品仓 KF6 库（ki18n/kwidgetsaddons/ktextwidgets/kwallet）产物**无 DT_SONAME**，CMake 按 IMPORTED_LOCATION 绝对路径链接，ld 把机器私有路径写进 DT_NEEDED | 补丁 0001：对 KF6 导入目标打 `IMPORTED_SONAME` 并清 `IMPORTED_NO_SONAME(_RELEASE)`；补丁 0002：`target_link_directories(${KSANE_DEP_LIB_DIRS})` + 裸 `-lKF6<Name>` 链接（其 include 目录以 SYSTEM PRIVATE 保留）。修复后 DT_NEEDED 只含 basename（ksanecore 26.04.0 先例） |
| 2 | test_package 运行报 `Error loading shared library ../../bin/libKF6ConfigCore.so (needed by .../libKF6ConfigGui.so)` | 制品仓 kconfig/6.18.0 的 libKF6ConfigGui.so 带**构建树相对** DT_NEEDED（`../../bin/libKF6ConfigCore.so`），加载器按进程 CWD 解析，包内不存在该目录 | test_package 构造 link farm（`run-farm/bin`、`run-farm/lib` 软链全部依赖 .so），并在 `run-farm/x/y` 下以 CWD 运行测试，使 `../../bin/...` 命中 farm（lokalize 26.04.0 / alligator 26.04.0 先例） |
| 3 | test_package 指定 cwd 后 `./test_libksane: inaccessible or not found` | `cpp.build.bindirs[0]` 为相对路径 | 拼接 `self.build_folder` 得到绝对路径后再执行 |
| 4 | ECM/KDEInstallDirs configure 期运行 qtbase 宿主工具报 libc++ 重定位错误 | 沙箱 LD_LIBRARY_PATH 中不兼容 libc++_shared.so 遮蔽兼容版本 | build/test 环境 prepend `LD_LIBRARY_PATH=/system/lib64`（ksanecore/kio 6.26.0 先例，E657 草稿） |
| 5 | 端到端消费者用例无法枚举/打开任何 SANE 设备（`scanimage -L` 空、`sane_open` 返回 INVAL） | 制品仓 sane-backends/1.2.1 的 `libsane-dll.so` 把后端搜索路径编译为 `/lib/sane`（configure 前缀为 "/"），而 OHOS 的 `/lib` → 只读 `/system/lib`，该目录不存在 → dll 加载器加载不了任何后端。属**依赖包运行期缺陷**，本 PR 未修改依赖包 | test_package 以 `LD_PRELOAD=<sane>/lib/sane/libsane-test.so.1` 直接驱动 SANE 官方 `test` 虚拟后端（后端本身即完整 libsane 实现，导出 sane_init/sane_open/sane_read），并设 `SANE_CONFIG_DIR` 指向复制的 `test.conf`。仅测试环境生效，不改产物、不写系统目录 |
| 6 | 测试首跑报 `Error loading shared library libtiff.so.6 (needed by libsane-test.so.1)` 等一串缺库 | `Environment.append("LD_LIBRARY_PATH", [列表])` 对列表用**空格**而非 `os.pathsep` 拼接，导致整串变成一个无效路径项（此前靠 conanrun 兜住，故未暴露；引入 LD_PRELOAD 后暴露） | 全部改用 path 语义 API：`env.append_path("LD_LIBRARY_PATH", [...])`、`env.append_path("QT_PLUGIN_PATH", [...])` |
| 7 | `deviceVendor()/deviceModel()` 在端到端用例中为空 | libksane/ksanecore 仅在设备列表刷新后（`devicesListUpdated()`，经交互式设备对话框路径触发）填充厂商/型号；KSaneWidget 未暴露 headless 的设备枚举入口 | 测试改为打印信息不作断言；设备身份由设备名 + 27 个真实 SANE 选项名佐证 |

## 源码修改（补丁）

- `patches/0001-CMakeLists.txt.patch`：顶层 `CMakeLists.txt` 在依赖段之后对 `KF6::I18n/WidgetsAddons/TextWidgets/Wallet` 打 `IMPORTED_SONAME=libKF6<Name>.so` 并清 `IMPORTED_NO_SONAME`/`IMPORTED_NO_SONAME_RELEASE`
- `patches/0002-src-CMakeLists.txt.patch`：`src/CMakeLists.txt` 用 `target_link_directories(KSaneWidgets PRIVATE ${KSANE_DEP_LIB_DIRS})` + 裸 `-lKF6I18n/-lKF6WidgetsAddons/-lKF6TextWidgets/-lKF6Wallet` 链接（替代 `KF6::<Name>` target），并把这些目标的 include 目录以 SYSTEM PRIVATE 保留

根因：上述 KF6 依赖产物无 DT_SONAME，若按 IMPORTED_LOCATION 绝对路径链接，ld 会把 Conan cache 绝对路径写入 DT_NEEDED（不可迁移）；修复后 ld 只记录 basename。

## 上游测试清点（R51 三步法）

1. **清点**：`autotests/CMakeLists.txt` 只定义 `ksane_tests()` 宏，宏调用被注释（`#ksane_tests(ksanetest)`），仓库内也没有 `ksanetest.cpp`；`tests/CMakeLists.txt` 的 `viewertest` 目标默认关闭（`COMPILE_VIEWER_TESTAPP` 默认 OFF），且其 `target_link_libraries` 引用的 `KSaneWidget` 目标在上游不存在（实际目标名是 `KSaneWidgets`），无法启用。→ **上游 CTest 注册数 = 0**
2. **实际运行**：`build()` 末尾执行 `ctest --test-dir <build> --output-on-failure`，日志显示 "No tests were found!!!"（注册数 0，退出码 0）
3. **回填**：PR 模板按"上游无测试、适配后补全"场景填写，功能断言由 test_package 承担

## 验证结果

```bash
# conan-verify（ohc-run.py）：G0-G4 全部 PASS，L2/L4/L5 跳过（纯库包，无 cache 路径）
# 上游测试：0 用例（见上）
# 自研 test_package 1：14 断言全部通过（无设备时公共 API 行为）
# 自研 test_package 2（端到端消费者用例）：14 断言全部通过
#   宿主应用打开 SANE 官方 test 虚拟扫描仪 -> 27 个真实选项 -> 写分辨率 100dpi
#   -> 完整扫描 -> 收到 314x393 图像（与 80x100mm@100dpi 一致）并落盘 PNG -> 关闭设备
ALL TESTS PASSED (0 assertion(s) failed)   # 两个用例均通过（合计 28 断言）
```

产物：`libKSaneWidgets6.so.6`（含 DT_SONAME，NEEDED 全部为 basename）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方 |
| conandata.yml | 源码 URL + sha256（b2d4db16...301d77）+ 2 个补丁 |
| manifest.yaml | 版本级 manifest |
| patches/0001,0002 | E537 可重定位链接补丁 |
| test_package/ | 消费者测试（CMakeLists.txt + test.cpp + conanfile.py + MANIFEST.yml） |
| notes.md | 本文件 |

## 注意事项

- libksane 位于依赖链 `skanlite → libksane → ksanecore` 的中间层；ksanecore/26.04.0 已发布（制品仓）
- 依赖图因版本线选择会**从源码重建 ksanecore**（ki18n override 到 6.18.0），CI `--build=missing` 同样适用
- 制品仓 KF6 6.26 线不完整（ktextwidgets/kwallet 缺 6.26.0），后续依赖 ktextwidgets 的包需注意同一约束
- kconfig/6.18.0 的 libKF6ConfigGui.so 相对 DT_NEEDED 属**上游制品缺陷**，本 PR 通过测试环境 link farm 规避，未改依赖包
- `reports/`、`test_package/build/` 等为 gitignore 覆盖的验证产物，不入库

## 对话记录

### 对话 #1（2026-10-04）

- 任务：适配 libksane 26.04.0 至 HarmonyOS PC (arm64)（分支 feat/libksane-26.04.0）
- 语言预检：detected=cpp（CMakeLists/manifest + 20 个 cpp 源文件），通过
- W0：qtbase/ki18n/kwidgetsaddons/ktextwidgets/kwallet/ksanecore/ecm 依赖均已发布；ksanecore 为已适配的上游依赖
- 版本线：KF6 6.18.0 单线（ktextwidgets/kwallet 制品限制），ksanecore 源码重建
- 编译：conan create 干净构建成功；conan-verify G0-G4 全 PASS
- 测试：上游 0 用例；自研 test_package 28 断言全通过（含端到端消费者用例：真实打开 SANE 虚拟扫描仪并取图 314x393）
- 知识：E537（relocatable SONAME 链接）与 E657（/system/lib64 libc++ 前置）为完全复用；无新增草稿

### 对话 #2（2026-10-04，PC 审查规则 12 整改）

- 背景：PR #14611 审查不通过 —— rule12「鸿蒙特有测试 N=0 < 1」，要求至少一个「跑通功能/流程的端到端消费者用例」（纯断言不算）
- 排查：尝试以 SANE 官方 test 虚拟后端构建真实扫描流程，发现制品仓 sane-backends/1.2.1 运行期缺陷（后端搜索路径编译为 /lib/sane，OHOS 不存在）
- 规避：test 环境 `LD_PRELOAD` 官方 test 后端 + `SANE_CONFIG_DIR`；同时修掉 `Environment.append` 用空格拼接 LD_LIBRARY_PATH/QT_PLUGIN_PATH 的隐蔽缺陷（改用 append_path）
- 结果：新增 `test_package/test_scan_flow.cpp`（14 断言），端到端流程真实跑通并产出 314x393 PNG；合计 28 断言全通过
---

**编译结束**: 2026-10-11 18:31
**最终状态**: built
