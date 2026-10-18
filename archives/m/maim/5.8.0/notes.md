# maim 5.8.0 HarmonyOS 适配笔记

## 构建配置

- 上游版本：v5.8.0（官方 tag `v5.8.0`）
- 构建系统：CMake（`project(maim VERSION 5.8.0 LANGUAGES CXX)`）
- 目标：HarmonyOS/OHOS 6.0、AArch64、Clang 15、libc++
- 产物：单个可执行文件 `bin/maim` + man page（`package_type = "application"`）
- 依赖（全部经 Conan `CMakeDeps` 目标）：

  `libx11/6.4.0`、`libxext/6.4.0`、`libxrender/0.9.12`、`libxfixes/6.1.0`、
  `libxcomposite/0.4.6`、`libxrandr/1.5.5.1`、`libpng/1.6.58.3`、
  `libjpeg-turbo/3.2.0.1`、`libwebp/1.6.0.1`、`slop/7.7`、`glm/1.0.3`、`icu/76.1`

- `MAIM_UNICODE=ON`（上游默认），`CXX_STANDARD=17`（见补丁说明）。
- 源码由官方 GitHub tag 下载，SHA-256 为
  `ecafe01dcbe4246071c58ff36acdcd93d290ed501f67933334b646436650450e`
  （实测下载 42224 字节）。源码包仅保存在仓库外的任务目录，未混入归档。

## W0 依赖检查

12 个直接依赖全部经 `conan install --requires=... -pr:h/-pr:b=ohos-aarch64
-r=ohpcd --build=never` 实测解析并下载到真实 OHOS/armv8 二进制（`--build=never`
下无一需要源码构建）。CI 的 L0i 门禁（`conan download <ref> -r=ohpcd
--only-recipe`）对同一 12 个 ref 逐个报 `[ok] dependency in registry`。

### libxext 版本冲突收敛

`slop/7.7` 的配方 pin `libxext/6.4.0.1`，而 `libxfixes/6.1.0`、
`libxcomposite/0.4.6`、`libxrandr/1.5.5.1` 均 pin `libxext/6.4.0`，直接求解会报
`Version conflict: libxext/6.4.0 / libxext/6.4.0.1`。本配方按 X11 栈的通行做法
（同目录 `gtk2/2.24.33`、`marco/1.26.2`）以 `force=True` 把 `libx11`、`libxext`
收敛到 6.4.0 track。该差异属 patch 级修订（major.minor 同为 6.4），不改变下游
package_id，因此 `libxfixes`/`libxcomposite`/`libxrandr`/`slop` 的已发布二进制
仍按原样复用（实测全部 `Already installed`，无源码重建）。

## 补丁 0001-CMakeLists.txt.patch（构建类，非平台宏）

由 `ohc-run.py refresh-patch --auto` 生成（orig/work 双树 difflib），已用
`patch -p1 --dry-run` 在 pristine tarball 上验证可应用。内容：

1. `cmake_minimum_required( VERSION 3.1.3 )` → `3.15`：CMake 4.x 已移除对
   < 3.5 兼容声明的支持，上游声明会让 configure 直接失败。
2. 依赖改用 Conan `CMakeDeps` 目标（`find_package(<pkg> CONFIG REQUIRED)` +
   `libx11::libx11`、`libxext::libxext`、`libxrender::libxrender`、
   `libxfixes::libxfixes`、`libxcomposite::libxcomposite`、
   `libxrandr::libxrandr`、`libpng::libpng`、
   `libjpeg-turbo::libjpeg-turbo`、`WebP::webp`、`slop::slop`、`glm::glm`、
   `icu::icu`）：上游走 `modules/Find*.cmake` 旧式查找变量，其中
   `FindSLOP.cmake` 强制 `FIND_PACKAGE(GLX REQUIRED)`，而 HarmonyOS PC 不提供
   GLX 显示栈，该模块在设备上无法满足。改为 Conan 目标后头文件/传递依赖/链接
   信息由目标稳定传播，也不再需要 `include_directories()` 变量块。
3. 显式加入 `libxext`：上游 `CMakeLists.txt` 并未 `find_package(XExt)`，而是靠
   `FindSLOP.cmake` 附带的 `X11_LIBRARIES` 与系统 `/usr/include` 提供
   `X11/extensions/XShm.h`、`X11/extensions/shape.h`（`src/x.hpp`、`src/main.cpp`
   直接包含）。Conan 环境下系统头不可依赖，故显式声明 `libxext/6.4.0`。
4. ICU 经 Conan：上游 `find_package(ICU COMPONENTS uc)` 用 CMake 自带模块在系统
   路径查找，Conan 环境下既找不到、又可能在设备上误链系统 ICU（未声明依赖）。
   改为 `find_package(icu CONFIG REQUIRED)` + `icu::icu`，`MAIM_UNICODE` 开关语义
   保留（关掉即不加 `-DCXXOPTS_USE_UNICODE`、不链 ICU）。
5. `CXX_STANDARD` 由 11 提到 17：`src/cxxopts.hpp` 在 `CXXOPTS_USE_UNICODE` 下
   包含 `<unicode/unistr.h>`，而 ICU 76 的头文件使用 `std::enable_if_t` /
   `std::is_convertible_v` 等 C++14/17 设施，在 C++11 下编译失败（实测 20 个
   错误）。OHOS profile 本身要求 `compiler.cppstd=17`，`slop` 静态库同为 C++17
   构建，故提升到 17 与工具链、依赖保持一致；maim 自身代码为 C++11 兼容子集，
   升标准不改变行为。

补丁不含 `__OHOS__` 等平台宏，对非鸿蒙平台透明。

### L4 记录（透明说明）

CI 的 L4 用 `(strcpy|sprintf|gets|strcat)\b` 扫描补丁正文，补丁注释里 CMake 常用
词 “targets” 会命中其中的 `gets\b`。该匹配与危险函数无关，为免在交付物里留下无
意义的“危险函数”告警，注释改写为 “imported Conan libraries”。本补丁不含任何
危险函数。

## R47 语言预检

`ohc-run.py lang-preflight maim 5.8.0 --src <pristine tarball>`：
`task=cpp, detected=cpp`，构建系统 cmake，源文件 6 个（cpp:6，主体 100%）。

## R51 上游测试三步法

### 1. 清点（证据：官方 v5.8.0 tarball 全树）

- `find . -type d -iname 'test*'`：0
- `find . -iname '*test*'`：0
- `grep -rn 'enable_testing|add_test|ctest|BUILD_TEST|include(CTest)'`：0
- 顶层文件仅 `CMakeLists.txt COPYING README.md license.txt maim.1 modules/ src/`

源码声明的上游测试数 **N = 0**。

### 2. 运行

配方 `build()` 在构建后执行 `ctest --test-dir <build> --output-on-failure`。
上游未 `enable_testing()`，CTest 报空套件、退出码 0（本机实测同行为），实际可
运行上游测试数 **N′ = 0**。

### 3. 回填

上游 0/0；未删除、未修改、未跳过任何上游测试，也未用消费者测试冒充上游测试。
新增消费者测试 6 个场景、共 28 条确定性断言（含 1 条鸿蒙特有断言，见下）：

1. `maim --version` 精确输出 `v5.8.0`（源码 `-DMAIM_VERSION="v${PROJECT_VERSION}"`）。
2. `maim --help` 含上游标题与 `--version/--geometry/--hidecursor/--format`。
3. 无 `DISPLAY` 时进入确定性错误路径（退出 1 + `Failed to open X display`）。
4. 显式不可达 `--xdisplay=:663` 的同一错误路径。
5. 未知选项被 cxxopts 解析器拒绝（非零退出）。
6. HarmonyOS 特有：产物为 AArch64 ELF，`DT_NEEDED` 覆盖
   X11/Xext/Xrender/Xfixes/Xcomposite/Xrandr/png/jpeg/webp，且**不含**
   GL/GLX/GLEW（证明未走 GLX 路径）。

断言计数：`test_maim.py` 13 条 + `test_package/conanfile.py` ELF 契约 15 条 = 28。

**鸿蒙特有测试（OHOS-specific）**：`ELF 契约` 中新增一条**平台特有**断言——用 `readelf -S` 检查 ELF 段表，要求恰好出现 **1 个 `.codesign` 段**。该段只由 OHOS 的 `binary-sign-tool` 自签名写入（配方 `package()` 的 `_sign_ohos_binary()`），**通用 Linux ELF 不含此段**，故该断言在非 OHOS 平台必然失败——它是真正的鸿蒙平台特有校验，而非通用 ELF/CLI 契约。

## 已知运行边界

- HarmonyOS PC 没有 X server，交互式截图/区域选择的真实功能无法在设备上验证；
  本适配不把它写成“已实测通过”。消费者测试覆盖公共 CLI 行为、完整二进制加载、
  选项解析与确定性无显示服务路径。
- 产出的 `bin/maim` 与目录内其它 X11 依赖型二进制一致，**不带 RPATH**，运行时
  需要 `LD_LIBRARY_PATH`（即 conanrun 环境）。消费者测试经 `env="conanrun"`
  实际执行二进制并通过；CI 的 L2 冒烟检查不带该环境，故在其报告中为
  非阻断 `warn`（与同目录 `slop/7.7` 的表现同构，未额外注入指向 Conan 缓存的
  绝对 RPATH）。

## 结束标记

maim 5.8.0 配方、补丁、test_package、manifest、commands.json 完成；
conan-verify 与 CI 同构门禁均 PASS。**覆盖范围限定**：conan-verify 的**有效覆盖为
G0–G3**（G4 报“无法找到程序包 ID”→ `--no cache 路径`，**L2/L4/L5 实际被跳过**，
跳过时字段保持 PASS，**不等于二进制已冒烟、安全检查已执行**）；CI 同构
JC/L0/L1/L4/L5 通过、**L2 冒烟为非阻断 warn**（无 RPATH，见上节）。
状态：built（未上传、未提 PR）。
