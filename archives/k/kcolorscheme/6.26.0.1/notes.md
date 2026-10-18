# kcolorscheme 6.26.0.1 适配笔记

## 6.26.0.1 修订（2026-10-18）

本修订修复 6.26.0 已发布包的两个缺陷，上游源码、构建逻辑与测试用例均未改动；唯一的
源码级改动是补丁 `0002-ohos-basename-soname-link.patch`（可重定位链接，见下）。

### 缺陷 1：消费者覆盖 qtbase 后源码重建失败（XKB）

qtbase/6.11.1.x 的 `Qt6GuiPrivate` 在配置阶段执行 `find_dependency(XKB)`，其
`FindXKB.cmake` 首步是 `find_package(libxkbcommon CONFIG QUIET)`。kwin 6.7.2 把
qtbase 覆盖到 `6.11.1.2` 时 kcolorscheme 需要从源码重建；原配方未声明 libxkbcommon，
CONFIG 查找失败后回退到系统路径也找不到，配置中止：
`Could NOT find XKB` → `Qt6GuiPrivate_FOUND=FALSE`。

修复：

- **新增直接依赖 `libxkbcommon/1.6.0`**（与 qtbase/6.11.1.x 已要求的传递依赖版本一致，
  不引入版本冲突），`test_package` 同步声明。
- `generate()` 同时设置 `XKB_INCLUDE_DIR` 与 `XKB_LIBRARY`（指向 libxkbcommon 包内
  头文件与库），并把 libxkbcommon 的 CMake/库/头文件目录加入 `conan_cmakedeps_paths.cmake`，
  使 CONFIG 与回退两条路径都可用。

### 缺陷 2：产物缺 DT_SONAME、DT_NEEDED 烧入构建机绝对路径（L5a/L5b/L5c）

OHOS 构建不加载 CMake 的 Platform/HarmonyOS 模块，`CMAKE_SHARED_LIBRARY_SONAME_*`
为空，`libKF6ColorScheme.so` 无 `DT_SONAME`；按绝对缓存路径链接消费的 KF6 组件后，
`DT_NEEDED` 记录构建机路径，包不可重定位。

修复采用 6.28.0 已验证方案（MR !16409，CI 校验通过）：

- **补丁 0002** 把四个实际消费的 KF6 组件（`ConfigCore`/`ConfigGui`/`GuiAddons`/`I18n`）
  按精确文件名 `-l:libKF6*.so` 链接，目录以 `target_link_directories PRIVATE` 附加；
  lld 以命令行原样记录名字，`DT_NEEDED` 只含 basename。
- `KF6::ConfigCore` 同时保留在链接 `INTERFACE`（按名导出，绝不按绝对路径），因为公共头
  包含 `<KSharedConfig>`，且上游安装的 `KF6ColorSchemeConfig.cmake` 已
  `find_dependency(KF6Config)`。
- 离开链接行依赖的 usage requirements 通过遍历 `INTERFACE_LINK_LIBRARIES` 传递闭包复制，
  每次 `get_target_property` 都做 `-NOTFOUND` 哨兵门控（KDE targets 只设
  `IMPORTED_LOCATION_RELEASE`）。
- 平台无 soname flag 时显式传 `-Wl,-soname,libKF6ColorScheme.so`（`/storage` 禁 symlink，
  版本化 `.so` 符号链不可用）。
- **依赖版本**：`kconfig/6.26.0.1`（已发布的 SONAME 修复版）；`kguiaddons` 与 `ki18n`
  在 ohpcd 没有已发布的 `6.26.0.1`（配方在主线但从未上传），保持已发布的 `6.26.0`，
  由补丁 0002 的 basename 链接消除其无 SONAME 的影响。
- `package()` 对每个安装 ELF 先 `llvm-objcopy --remove-section .codesign` 再
  `binary-sign-tool -selfSign 1` 重签，避免 CMake 安装改写 RUNPATH 后签名失效
  （6.18.0.3 先例）。

## 适配范围

本适配基于 KDE 官方 `kcolorscheme-6.26.0.tar.xz`，面向 HarmonyOS PC
aarch64、clang 15、libc++ 和 C++17。

## W0/W0b 核验

- `qtbase/6.11.1`、`ecm/6.26.0`、`kconfig/6.26.0.1`、`kguiaddons/6.26.0`、
  `ki18n/6.26.0` 和 `libxkbcommon/1.6.0` 均可从 `ohpcd` 下载 recipe 与二进制。
- 已核对历史归档 `archives/k/kcolorscheme/6.18.0`；其 CMake、ECM 路径及无头
  运行环境仍适用于 6.26.0。
- 6.26.0 将最低 Qt 版本提高到 6.9.0；当前 `qtbase/6.11.1` 满足要求，
  并提供 Qt 6.10 以后构建所需的 `Qt6GuiPrivate`。

## 上游测试清点（R51）

| 检查项 | 数量 | 证据 |
| --- | ---: | --- |
| `autotests/` 测试源文件 | 1 | `autotests/kcolorschemetest.cpp` |
| CTest 注册项 | 1 | `ecm_add_test(kcolorschemetest.cpp ...)` |
| 测试数据文件 | 1 | `autotests/kcolorschemetest.colors` |

注册的 `kcolorschemetest` 覆盖颜色方案构造基准、7 类颜色集的背景/前景/
装饰色读取，以及配置对比度读取。配方设置 `BUILD_TESTING=ON`，不删减或
改写该测试，并使用 `ctest --no-tests=error` 确保测试未注册时直接失败。

## HarmonyOS 适配

- `KF_IGNORE_PLATFORM_CHECK=TRUE` 允许 KDE Frameworks 在 OHOS 配置上构建。
- `KF_SKIP_PO_PROCESSING=ON` 跳过翻译目录处理，不影响 `KF6::ColorScheme`
  核心库和内置 Breeze 配色资源。
- 显式加入 ECM、Qt6、KConfig、KGuiAddons、KI18n 和 libxkbcommon 的 CMake、
  库及头文件搜索路径，兼容这些 Conan 包自带的 CMake 配置。
- 上游 CTest 使用 `QT_QPA_PLATFORM=offscreen`、隔离的 HOME/XDG 目录运行，
  不依赖 Wayland、X11 或桌面会话。
- 补丁 0002 为纯构建可移植性补丁，无 `__OHOS__` 等平台宏、无空壳分支；
  `KColorScheme` 的颜色读取、`KColorUtils` 调用和资源加载均保留上游真实实现。

## 消费者测试

`test_package` 通过上游导出的 `KF6::ColorScheme` 目标链接，构造 active /
inactive 两套 `KColorScheme`，验证背景、前景、装饰色均有效，并检查对比度
位于合法范围，共 5 个测试用例；逐例输出 `TEST PASS/FAIL`，末行
`TEST SUMMARY: N passed, M failed`，任一失败进程退出码 1。

## 本地验证边界

- 官方源码 SHA256 已核验：
  `74149a0379bd8bf6590d3c1f7f8c503665e0f3adafc2adbd44fc6bb764c969f1`。
- R39 镜像回退：download.kde.org 在 CN 网络 302 到 mirrors.bfsu.edu.cn，该镜像
  TLS 证书在真机网络校验失败；`conandata.yml` 按「官方源 + mirror.nju.edu.cn +
  mirrors.aliyun.com」列出回退，两个镜像均已下载并与官方 tarball 逐字节比对
  （51636 bytes，sha256 一致）。mirrors.ustc.edu.cn 同样 302 到 bfsu，故不列入。
- 补丁 0002 的上下文已对照 6.26.0 源码 `src/CMakeLists.txt` 核对，并在真机
  源码树上做 `patch --dry-run` 适用性预检。
- 最终通过率以 HarmonyOS worker 实际运行的上游 CTest 与消费者测试为准，收尾时
  据实回填 `manifest.yaml`。
