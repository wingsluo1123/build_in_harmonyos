# hpx 1.11.0 适配笔记

## 基本信息

| 项 | 值 |
|---|---|
| 软件 | HPX — The C++ Standards Library for Parallelism and Concurrency |
| 上游版本 | 1.11.0（tag `v1.11.0`；仓库 `TheHPXProject/hpx`，原 `STEllAR-GROUP/hpx` 已 301 重定向） |
| 源码 tarball | `https://github.com/TheHPXProject/hpx/archive/refs/tags/v1.11.0.tar.gz` |
| sha256 | `01ec47228a2253b41e318bb09c83325a75021eb6ef3262400fbda30ac7389279` |
| 构建系统 | CMake（≥3.18）；Ninja；OHOS SDK clang 15 / libc++ / C++17 |
| 适配路径 | 路径 C（高难度挑战）：aarch64 上下文切换后端重路由 + musl libc 能力缺口桥接 + 官方依赖源注入 |
| 状态 | built（Win 编链验证；W3/CI 见 `.ci-result.json`） |

## 依赖

| 依赖 | 规格 | 说明 |
|---|---|---|
| boost | `1.85.0` | 选型理由：registry 中唯一提供**完整 boost 头文件树**的包（含 HPX 必需的 accumulators/spirit/phoenix/parameter）。1.90.0.4.2/1.91.0.1.3 组件构建缺 `boost/accumulators` 等（实测下载包核对），不可用 |
| hwloc | `2.14.0` | HPX 拓扑发现必需（`HPX_SetupHwloc` 无条件 find_package） |
| libucontext | `1.5.2` | 提供 musl/OHOS 缺失的 ucontext 实现（含 unprefixed 弱符号 getcontext/setcontext/makecontext/swapcontext，PIC 静态库） |
| zlib | `1.3.1.1`（override=True） | 统一版本冲突：hwloc 子树要求 `zlib/1.3.1.1`，boost/1.85.0 要求 `zlib/1.3.1`；按 R37 统一到修复版 1.3.1.1（同上游 1.3.1，ABI 一致，两包已发布二进制均保持有效） |
| asio | `asio-1-21-0`（官方 tag 归档） | HPX 无条件需要 standalone Asio（≥1.12）；registry 无 asio conan 包。经 conandata `deps:` 下载官方 tag tarball 并以 `-DHPX_WITH_FETCH_ASIO=ON -DFETCHCONTENT_SOURCE_DIR_ASIO=<repo root>` 注入（tag 对齐 `HPX_WITH_ASIO_TAG_DEFAULT`，R39 官方源） |

## 适配要点

### 1) Asio 官方源注入（conandata deps + FetchContent 本地源）

`conanfile.py::build()` 先 `_prepare_asio()`（`download()` + `unzip(strip_root=True)` 到
`build_folder/deps/asio/`），再以 configure 变量 `FETCHCONTENT_SOURCE_DIR_ASIO` 注入。
HPX 的 `fetchcontent_makeavailable(asio)` 跳过网络下载，直接使用本地源并把 Asio 头
安装进 hpX 包（`<Asio_ROOT>/asio/include` 布局，与 `HPX_SetupAsio.cmake` 预期一致）。

### 2) 协程上下文切换：ucontext + libucontext（本适配核心）

- OHOS/aarch64 上 HPX 的默认后端 Boost.Context **不可得**（registry boost 包
  显式排除 context/coroutine/fiber；其配方注释：Boost.Context 无 OHOS aarch64 asm）。
- 非 generic 路径在 `__linux__`（OHOS clang 实测定义）下会错误选中 x86 专用实现。
- OHOS musl 的 `<ucontext.h>` 仅定义类型、不声明/实现 ucontext 函数族（20 行 stub）。
- 方案：`HPX_WITH_GENERIC_CONTEXT_COROUTINES=OFF` + `requires("libucontext/1.5.2")` +
  4 个平台补丁（下表）+ 把 libucontext 放到链接尾部（见「构建配置」）。

### 3) Conan 生成配置的目标名适配（不修改 HPX 源码）

conan 工具链强制 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`，HPX 自带的 `FindHwloc.cmake`
不会运行；且 HPX 链接 `Boost::boost` / `Hwloc::hwloc`（大写），而 registry 包的
CMakeDeps 目标为 `Boost::headers` / `hwloc::hwloc`。在 `generate()` 中用
`deps.set_property(..., "cmake_target_aliases", [...])` 生成规范别名
（`Boost::boost` → `Boost::headers`；`Hwloc::hwloc` → `hwloc::hwloc`），不改上游构建文件。

### 3b) Conan 2 traits：公共头文件依赖必须声明传递

HPX 是共享库，其公共头文件包含 boost/hwloc 头（`hpx/config/version.hpp` → `<boost/version.hpp>`；
`hpx/topology/topology.hpp` → `<hwloc.h>`）。Conan 2 默认会把共享库的**静态/头文件依赖**
对下游 skip 掉（cpp_info 被剥空），导致消费者找不到头、CMakeDeps 生成空配置。
修复：`self.requires("boost/1.85.0", transitive_headers=True)`、
`self.requires("hwloc/2.14.0", transitive_headers=True, transitive_libs=True)`
（与 HPX 自身 CMake 的 PUBLIC 链接语义一致）。

### 3c) OHOS 共享库必须签名（`.codesign`）

HarmonyOS 加载器拒绝加载**未签名**的共享库：未签名时运行消费者二进制报
`Error loading shared library libhpx.so.1 / libhpx_core.so`（随后一连串 hpx 符号
`symbol not found`）。`package()` 中对包内 `lib/**/*.so*`（跳过符号链接）执行
`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`
（与 registry boost 配方同款；工具取 `tools.build:compiler_executables` 同目录或
`/data/service/hnp/bin`）。Win 开发机 SDK 无 `binary-sign-tool` → 安全跳过并告警，
权威签名在 PC/CI 构建时完成。实测：签名后消费者测试 7/7 全过（HPX runtime 正常启动）。

### 3d) OHOS 共享库 SONAME/RPATH 链接规则（CI 轨）

CI profile 把 OHOS 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，CMake 无对应平台模块，
通用链接规则**不带 SONAME/RPATH 标志** → 共享库 DT_NEEDED 记录相对路径
（如 `../lib/libhpx_core.so`）导致加载失败且制品不可搬运。`generate()` 在
`settings.os == "OHOS"` 时按 registry boost 配方同款设置
`CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG`、`CMAKE_SHARED_LIBRARY_RUNTIME_*`、
`CMAKE_SHARED_LIBRARY_RPATH_LINK_*_FLAG`（`-Wl,-soname,` / `-Wl,-rpath,` /
`-Wl,-rpath-link,`）与 `CMAKE_BUILD_RPATH_USE_ORIGIN=True`。

### 4) 构建配置（`generate()`）

| 变量 | 值 | 理由 |
|---|---|---|
| `HPX_USE_CMAKE_CXX_STANDARD` | ON | Conan 会在 toolchain 设置 `CMAKE_CXX_STANDARD`（cppstd17）；HPX 默认拒绝手动设置，该上游开关使其接受并传播 |
| `HPX_WITH_MALLOC` | `system` | OHOS 无 tcmalloc；上游文档化的关闭方式 |
| `HPX_WITH_GENERIC_CONTEXT_COROUTINES` | OFF | 见「适配要点 2」 |
| `HPX_WITH_FETCH_ASIO` | ON | 配合本地源注入（见「适配要点 1」） |
| `HPX_WITH_TESTS` / `HPX_WITH_COMPILE_ONLY_TESTS` / `HPX_WITH_FAIL_COMPILE_TESTS` / `HPX_WITH_EXAMPLES` | OFF | 完整上游测试套件（数千 CTest 用例）超出 CI 预算；R51 实测子集在真机单独执行（见 reports/test-report.md） |
| `HPX_WITH_PKGCONFIG` | OFF | HPX 1.11.0 的 pkgconfig 生成在 `file(GENERATE INPUT ...)` 中使用
目标上下文相关生成器表达式（`$<TARGET_PROPERTY:TYPE>`），CMake ≥4（worker 工具链为 CMake 4.x）
下为硬错误（最小复现：`file(GENERATE)` + `$<TARGET_PROPERTY:TYPE>` 报 "may only be used with
binary targets"）。OHOS 消费者经 CMake/Conan 使用 HPX；上游对非 Linux/Apple/MSVC 平台默认即关闭。 |

### 补丁清单（PF5 例外说明）

以下补丁**仅改变 OHOS（aarch64）平台行为**，其他平台行为保持逐字不变（R8 四不准则）；
不含空壳 stub / return 0 绕过，`__OHOS__` 仅作为平台能力分支判据（libc 探针类例外，
用户/主管已批准，PR 正文将写明理由）：

| # | 文件 | 修改内容 | 理由 |
|---|---|---|---|
| 0001 | `libs/core/coroutines/include/hpx/coroutines/detail/context_impl.hpp` | 在 x86 linux 分支之前插入 `#elif defined(__OHOS__) && defined(__aarch64__)`，选择 `context_posix.hpp` 的 `ucontext_context_impl` | OHOS aarch64 无可用 Boost.Context，x86 后端不适用；ucontext 是上游现成的 POSIX 后端 |
| 0002 | `libs/core/coroutines/include/hpx/coroutines/detail/context_posix.hpp` | 在 `<ucontext.h>` 后为 `__OHOS__` 补 4 个函数声明（getcontext/setcontext/makecontext/swapcontext） | OHOS musl 只定义 `ucontext_t` 类型、不声明函数；实现由 libucontext 提供 |
| 0003 | `libs/core/coroutines/src/swapcontext.cpp` | linux x86 单元编译条件加 `!defined(__OHOS__)` | 该 TU 为 x86 汇编包装，aarch64 上无意义且触发上游 `#error` |
| 0004 | `libs/core/coroutines/src/detail/context_posix.cpp` | 同上（与 `context_impl.hpp` 分支保持同步） | `ucontext_context_impl_base::default_stack_size` 的定义必须落在 POSIX 分支，否则链接期缺符号 |

### 构建配置中与宿主工具链相关的处理（仅 Win 交叉轨）

Windows 交叉 profile 使用 DevEco SDK 的 `ohos.toolchain.cmake` 作为 user_toolchain，该文件
会在 cache 中**预定义** `CMAKE_CXX_FLAGS`，使 Conan 的 `CMAKE_*_FLAGS_INIT` 注入失效；
且其传 `--gcc-toolchain=...` 被 clang 报 "argument unused"，与 HPX 特性测试的 `-Werror`
叠加导致 configure 失败。处理：build() 在 Windows 宿主下用 cli_args 以 cache 变量注入
`-Wno-unused-command-line-argument`（CI profile 不使用该 SDK 工具链，不受影响）。

libucontext 必须出现在链接行**末尾**（标准库位置）才能拉取静态归档符号；
经 `cmake.configure(variables={"CMAKE_CXX_STANDARD_LIBRARIES": "-L<uc>/lib -lucontext -lucontext_posix -lm"})`
注入（双轨同构；`-Wl,-z,defs/--no-undefined` 下正确解析 ucontext 符号）。

## W0 依赖勘查（2026-09-28，历史记录：上报与决策）

> 上游 tag 为 `v1.11.0`（仓库已迁移 `STEllAR-GROUP/hpx` → `TheHPXProject/hpx`，GitHub 301）。

### 两个依赖级阻塞（已按用户铁律上报，主管批复路线 A）

1. **Asio（standalone，≥1.12）缺失**
   - HPX `CMakeLists.txt` 无条件 `include(HPX_SetupAsio)`；`HPX_WITH_FETCH_ASIO` 默认 OFF →
     `find_package(Asio 1.12.0 REQUIRED)`；`HPX_WITH_NETWORKING` 关闭也不能绕过。
   - ohpcd 无 asio：全仓 recipe 扫描 0 命中；6 个版本 `conan download --only-recipe` 全部 not found（R35 口径）。
   - 决策：conandata `deps:` 注入官方 tag 归档（先例：interface99 + Metalang99）。
2. **Boost.Context（aarch64 默认 coroutine 后端）不可得**
   - arm64 自动 `HPX_WITH_GENERIC_CONTEXT_COROUTINES=ON` → 需要 Boost.Context/Thread/Chrono。
   - registry boost 包（1.90.0.4.2 / 1.91.0.1.3）配方显式排除 context/coroutine/fiber
     （1.91 配方注释 "Boost.Context has no aarch64 asm for OHOS and fails the build"）。
   - 决策：关闭 generic 后端，走 ucontext + libucontext（见「适配要点 2」）。

## 编译步骤（Win 编链验证轨）

```powershell
# 1) 生成 toolchain + 依赖（json: install/build/Release/generators/conan_toolchain.cmake）
conan install archives/h/hpx/1.11.0 -pr:h=<ohos-aarch64-win> -pr:b=default -of <out>

# 2) 手工探索编译（含 asio FetchContent 本地源注入）
cmake -S <hpx 源码> -B <build> -G Ninja `
  -DCMAKE_TOOLCHAIN_FILE=<out>/build/Release/generators/conan_toolchain.cmake `
  -DCMAKE_BUILD_TYPE=Release `
  -DCMAKE_CXX_FLAGS=-Wno-unused-command-line-argument `
  "-DCMAKE_CXX_STANDARD_LIBRARIES=-L<libucontext>/lib -lucontext -lucontext_posix -lm" `
  -DFETCHCONTENT_SOURCE_DIR_ASIO=<asio 源码根>
cmake --build <build> -j16

# 3) W3 等价验证（CI/HarmonyOS PC 上真正运行 test_package）
conan create archives/h/hpx/1.11.0 -pr:h=... -pr:b=... --build=hpx/*
```

## 验证结果

- Win 手工 CMake 编链验证：见本次执行日志（构建目录 `manual/build`；全量编译 + 链接 `libhpx_core.so` / `libhpx.so`）。
- Win 交叉轨 `conan create`（`-tf=""` 跳过测试阶段；`tools.build:skip_test=True` 不覆盖 test_package）：**RC=0**；
  test_package 在 Win 侧单独验证编译+链接通过（实际运行在 PC W3 完成）。
- HarmonyOS PC W3（`finish`，含 test_package 实跑）：**`exit_code=0`**
  （`integrity_hash=5aeb2caea4f54b47`、`log_sha256=8c3b95d493218533e3bdaf66dbc35ea9bc620637a97c0dd379dd97676c208498`）；
  test_package **7/7 PASS**；R51 上游子集 **18/18**（100%，14.82s）。

## 上游测试（R51 三步法：清点 / 实跑 / 申报）

| 项 | 值 |
|---|---|
| 上游测试体系 | CTest（libs/*/tests/{unit,regressions,performance}） |
| 上游用例清点 | 516 个测试注册目录 / ~1180 条 CTest 注册 / 1303 个测试源文件（完整清点见 reports/test-report.md） |
| 适配后实跑 N′ | 18（与适配直接相关模块子集：coroutines/threading/threading_base/synchronization/lcos_local/futures/async_combinators/init_runtime/runtime_local/schedulers/executors，HarmonyOS PC 实测） |
| 通过率 | **18/18（100%）**（详见 reports/test-report.md；未执行项逐类技术归因） |

## 交付物

| 文件 | 说明 |
|---|---|
| `conanfile.py` / `conandata.yml` | Conan 配方与源声明（含 asio deps） |
| `patches/000{1..4}-*.patch` | 4 个平台补丁（见上表） |
| `test_package/` | 消费者测试（test_hpx.cpp：真实 HPX API + R53 鸿蒙断言） |
| `reports/` | test-report.md（R51/R53）、conan-create 日志等 |

## 注意事项 / 已知限制

1. **协程后端**：OHOS/aarch64 使用 POSIX ucontext（经 libucontext）而非 Boost.Context；
   每次上下文切换会保存/恢复信号掩码（上游注释：比 Boost.Context 慢），功能等价。
   这是平台能力缺口下的上游支持路径，已在 PR 正文申明。
2. **pkgconfig**：不生成 `.pc` 文件（CMake ≥4 与 HPX 1.11 的 pkgconfig 生成不兼容）；
   消费者使用 CMake/Conan。HPX 自身对非 Linux 平台默认关闭该选项。
3. **Boost**：选用 1.85.0（完整头文件树）；不使用 boost 的编译库（HPX 本配置下仅链接 header-only 目标）。
4. Windows 交叉轨的 toolchain 注入细节仅影响开发机验证；CI（HarmonyOS）不使用 DevEco
   `ohos.toolchain.cmake`，相关处理在 CI 上为惰性分支。

---

**编译结束**: 2026-09-28
**最终状态**: built（W3 exit_code=0；test_package 7/7；R51 上游子集 18/18）
