# fcitx5 5.1.14 适配笔记

## 背景

- `fcitx5` 是输入法框架核心库（Fcitx5Core / Fcitx5Config / Fcitx5Utils 三个库 + addon 模块 + 上游测试），独立官方仓库 `https://github.com/fcitx/fcitx5`，tag `5.1.14`。
- 官方 tag 源码：`https://github.com/fcitx/fcitx5/archive/refs/tags/5.1.14.tar.gz`，执行端实际下载并核验 SHA-256 = `c81bbf0156d083e4c7e7817e658122c33a8c1e585962467f251bc9614bdfee47`。
- 依赖链（W0 门禁实测全部已发布）：`extra-cmake-modules/6.29.0`（tool_requires，构建期 ECM）、`libuv/1.52.1`（EVENT_LOOP_BACKEND=libuv 事件循环）、`gettext/0.22.5.1`（libintl）。
- 同源组件 `fcitx5-utils 5.1.13`（仅 Fcitx5Utils 库）已于 2026-09-22 交付（archives/f/fcitx5-utils/5.1.13）；本任务为 fcitx5 全库（Core/Config/Utils + 模块）。

## 构建方案（CMake 顶层直接构建）

- 上游 CMake 顶层设计为整体构建；OHOS PC 无 X11/Wayland/DBus/Enchant/Emoji/Keyboard 系统服务，配置时全部禁用（`-DENABLE_X11=Off -DENABLE_WAYLAND=Off -DENABLE_DBUS=Off -DENABLE_ENCHANT=Off -DENABLE_EMOJI=Off -DENABLE_KEYBOARD=Off -DENABLE_LIBUUID=Off -DENABLE_SERVER=Off -DUSE_SYSTEMD=Off -DEVENT_LOOP_BACKEND=libuv -DBUILD_SPELL_DICT=Off`）。
- `ENABLE_SERVER=Off`：以嵌入式库形态交付（上游文档注释明示 "disable this option if you want to use fcitx as an embedded library"）。
- 上游测试（test/ 目录 38 个注册可执行）在 Step2 实机全部编译并实际运行通过（38/38，双口径台账见下）。

## 上游测试台账（双口径）

- **source_declared_total**：test/CMakeLists.txt 声明全部独立可执行测试目标 **48** 个（FCITX_UTILS_TEST 25 + FCITX_CONFIG_TEST 2[dbus 条件] + FCITX_CORE_TEST 10 + 独立 add_executable 11[emoji/spell/xkb 等条件项]），其中 DBus/emoji/enchant/xkb/xim 条件项在当前 OHOS 配置（DBus/Emoji/Enchant/Keyboard/X11 关闭）下按上游条件未实例化，不计入当前配置可执行集合。
- **configured_executable_total**：当前 OHOS 配置实际注册的可执行用例 **38** 个（`ctest -N` 全量枚举）。
- **executed_passed_total**：38/38 全部实际运行通过（`ctest -j1 --output-on-failure`，cwd=build-step2）。
- 统计口径：**38/38 (100%)**；全量声明口径 `38/48` 中未实例化的 10 项均因上游显式条件宏（ENABLE_DBUS/ENABLE_EMOJI/ENABLE_ENCHANT/ENABLE_KEYBOARD/ENABLE_X11）在当前配置关闭而互斥排除，非失败、非跳过运行。
- 逐项映射（源码声明 → 构建目标 → ctest 注册 → 实际执行）见测试执行日志（Step2 ctest 输出，38/38 PASSED）。

## OHOS 平台适配（13 个补丁，全部为等价改写，先例见 fcitx5-utils 5.1.13 / ada-url / bitcoin）

1. **OHOS 裁剪 libc++15 缺 C++20 设施**（实测编译确认）：
   - `<format>` / `__cpp_lib_format` 缺失 → i18n.h 多参数 translate 模板增加无 `<format>` 兼容实现（vformatCompat 支持 `{N}`、`{N:X}`、`{}` 占位符）；eventloopinterface/log/misc/semver/spell-custom-dict/unicode.cpp 的 std::format → ostringstream / 字符串拼接 / strftime 等价输出。
   - `std::ranges` 算法（transform/copy/equal/lower_bound）与 `std::views` 缺失 → 标准算法（迭代器版）+ 显式循环；standardpaths_p_unix.cpp 的 `std::unordered_set<filesystem::path>`（依赖缺失 hash<fs::path>）→ `std::set` 去重（operator<，语义等价）。
   - icontheme.cpp `files | std::views::reverse` → rbegin/rend 循环；VariantOverload 增加显式推导指引（CTAD）。
2. **CMake 4.1 构建行为**：spell 模块 add_custom_command 用 ALIAS 目标 `Fcitx5::comp-spell-dict` 不展开为可执行路径 → 改用 `$<TARGET_FILE:comp-spell-dict>` 真实目标；`BUILD_SPELL_DICT=Off`（en_dict 数据下载源超时，非核心功能）。
3. **测试兼容**：teststandardpaths_unix.cpp `std::ranges::equal` → `std::equal`（四迭代器，绑定实际 directories() 结果避免临时对象迭代器）。

## 关键平台知识（详见知识候选台账与草稿）

- OHOS 加载器拒绝加载 RUNPATH 指向 conan 缓存目录的库（dlopen 报 `Permission denied`，本机实测）；配方保持 conan 默认 `CMAKE_SKIP_RPATH=1`（库不带 RUNPATH），消费者/下游通过 conanrun 环境（LD_LIBRARY_PATH）解析 libFcitx5* 与 libuv.so.1。
- OHOS sysroot `libintl.h` 是空壳（无声明），必须依赖 gettext 包真实 libintl；po/ 翻译 `.mo` 生成需系统 msgfmt（/data/service/hnp/bin/msgfmt）并注入 `GETTEXTDATADIR` 定位 ITS 规则。
- `EVENT_LOOP_BACKEND=libuv`：event_none 后端 createDefaultEventLoop 返回 nullptr，核心测试（testevent/testinputcontext/testinstance/testunicode/testquickphrase）会抛 "No available event loop implementation"；libuv（sysroot/制品仓）提供真实事件循环。
- `CMAKE_SYSTEM_NAME=OHOS` 必须显式声明：CMake 不认识 HarmonyOS 平台（无 platform module），不声明时 ecm_setup_version 生成的 SOVERSION 不应用于库输出（无 `-Wl,-soname`、输出不带版本后缀），消费者运行时报 "Error loading shared library ../../../bin/..."。
- `ecm_setup_version` 需 ECM 模块；顶层 `include(ECMUninstallTarget)` 需要 `ecm_uninstall.cmake.in`（extra-cmake-modules 6.29.0 含该文件，6.19.0 缺），故 tool_requires 用 6.29.0（fcitx5-utils 5.1.13 因 wrapper 不含该 include 才可用 6.19.0）。
- 上游测试运行依赖：38 个测试目标在 Step2 用 libuv 后端 + LD_LIBRARY_PATH=build 输出 bin 实际运行通过（本机 aarch64 OHOS 原生可执行）。

## 消费者验证（R34，非空壳）

- `test_package/test_fcitx5.cpp`：find_package(fcitx5) + 链接 Fcitx5::Core/Config/Utils + 调用 SemanticVersion::parse / Key 字符串构造 / stringutils::trim 公开 API 并断言（5.1.14 / Control+Alt+E / trim），本机运行 PASSED。
- `test_package/test_fcitx5_ohos.cpp`（鸿蒙专项测试）：StandardPaths OHOS 路径查询（userDirectory/directories 非空断言）+ environ 环境变量往返 + 公开 API 断言，本机运行 PASSED。
- 消费者用例与上游测试、鸿蒙专项测试分别计数，不重复充数。

## 知识路径决定（new_draft，路径 B，【知识库扩展】）

完整台账：`reports/knowledge-candidate-ledger.md`（8 个候选，逐项真实错误/根因/修复/验证/适用边界 + 四范围查重 + 七轴汇总表）。

- 候选 1（OHOS libc++15 C++20 设施缺失）/ 候选 2（sysroot libintl.h 空壳）/ 候选 3（msgfmt ITS rules）/ 候选 4（CMake 4.1 add_custom_command ALIAS 不展开）/ 候选 6（CMAKE_SYSTEM_NAME=OHOS 致 SOVERSION 不应用）：等价命中既有条目（DRAFT-E5xx-ohos-libcpp-missing-ranges-algorithms、DRAFT-ohos-libcxx15-format-ranges-capability-gap、DRAFT-ohos-libcxx-missing-std-views、DRAFT-dawn-…-libcxx15-cpp20-compat-ensemble、DRAFT-13410-trueprint-libintl-stub-header、E608-draft-8E00、E431-draft-A482、DRAFT-cmake-harmonyos-system-name-soname）→ **reuse_existing（路径 A 语义）**，不建草稿。
- 候选 5（OHOS 加载器拒绝 RUNPATH 指向 conan 缓存目录 → CMAKE_SKIP_RPATH=ON + conanrun）/ 候选 7（include(ECMUninstallTarget) 需 ecm_uninstall.cmake.in → ECM 6.29.0）/ 候选 8（EVENT_LOOP_BACKEND=libuv，event_none 返回 nullptr）：未命中或部分覆盖且存在新增差异、已验证、可跨库复用 → **new_draft（路径 B）**，已建同 stem 的 .md/.kv 草稿并通过 graph validate（knowledge/drafts/DRAFT-fcitx5-ohos-skip-rpath-conanrun.*、DRAFT-fcitx5-ecm-uninstall-target-ecm-6290.*、DRAFT-fcitx5-event-loop-backend-libuv.*）。
- 整体 `knowledge_decision: new_draft`：3 个新草稿与 fcitx5 归档进入同一 PR。
