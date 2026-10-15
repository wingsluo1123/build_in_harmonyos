# samarium 1.0.0 OpenHarmony PC 适配笔记

上游：<https://github.com/strangeQuark1041/samarium>，tag `v1.0.0`
（C++20 二维物理仿真库；CMake 构建；测试框架 Boost.UT）
源码 tarball sha256：`943de75803f492f78c5d55fe43be298fbb66156cc22946a3c6cc6b0634efc2e2`（88496 字节，`tar tf | wc -l` = 151）

## 适配范围（`status: partial`）

交付 **math / physics / geometry / graphics（非 SFML 部分）/ util** 全部核心模块：

- 公共头 45 个 `.hpp`（`core.hpp`、`math.hpp`、`physics.hpp`、`geometry.hpp`、`graphics.hpp`、`util.hpp` 与 umbrella `samarium.hpp`）；
- `lib/libsamarium.so`（无版本化 soname，`DT_SONAME = libsamarium.so`）。

**`app` 与 `gui` 两个模块不交付**，原因是硬依赖 SFML 的 **Window + Graphics**：

- `src/samarium/app/App.{hpp,cpp}` → `SFML/Graphics/RenderWindow.hpp`、`SFML/Window/Event.hpp`、`SFML/Window/VideoMode.hpp`；
- `src/samarium/gui/{Keyboard.hpp,Mouse.cpp,Mouse.hpp,sfml.hpp}` → `SFML/Window/Keyboard.hpp`、`SFML/Window/Mouse.hpp`、`SFML/Graphics/RenderWindow.hpp`。

本制品仓只有 `archives/s/sfml/2.6.1.1`，其 `manifest.yaml` 是 `status: partial`，只交付
`System` / `Network`，并把 `SFML/Window`、`SFML/Graphics`、`SFML/Audio` 的头文件目录与
`sfml-window.pc`、`sfml-graphics.pc` **裁掉**（理由：OHOS CI 不具备 X11/DRM/UDev 窗口后端）。
上游想要的 `sfml/2.5.1`（含 Window/Graphics）在制品仓不存在，因此：

- 配方**不依赖 sfml**，`requires` 只留 `fmt/8.1.1` + `range-v3/0.12.0`（两者制品仓都有）；
- 裁剪 `src/samarium/CMakeLists.txt` 里的 `samarium/app/App.cpp`、`samarium/gui/Keyboard.cpp`、
  `samarium/gui/Mouse.cpp` 三个编译单元（补丁 0003）；
- 同时裁掉对应公共头，并去掉 umbrella `samarium.hpp` 里的 `#include "app.hpp"` /
  `#include "gui.hpp"`，保证**安装头集合的包含闭包自洽**（`test_layout.py` 逐头检查）。

> 竖切范围与 sfml 自身的 partial 边界一致：**凡是需要窗口/OpenGL 上下文的能力都不在本次交付内**，
> 但物理引擎核心（质点、质点系统、弹簧、圆碰撞、噪声、随机、图像/网格/轨迹数据结构）全部可用。

## 构建方式

- 构建系统：CMake（上游 `CMakeLists.txt` + `src/CMakeLists.txt` + `test/CMakeLists.txt`）。
- 依赖接线：conan 2 `CMakeDeps` + `CMakeToolchain`；上游 conan 1 的 `conan_install.cmake`
  （configure 阶段 `conan install -if`）与 `conanbuildinfo` 分支被补丁 0002 移除，改为
  `find_package(fmt CONFIG REQUIRED)` / `find_package(range-v3 CONFIG REQUIRED)`。
- 共享库：`-DBUILD_SHARED_LIBS=ON`；`CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` +
  `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG/CXX_FLAG=-Wl,-soname,`（OHOS 不在 CMake 已知平台表里，
  不补这两项会缺 `DT_SONAME`，且版本化符号链接在 HMDFS 上不可靠；先例 `archives/h/hidapi/0.15.0`）。
- OHOS 打包阶段对交付的 `.so` 逐个签名：`llvm-objcopy --remove-section .codesign` →
  `binary-sign-tool sign -inFile X -outFile X.signed -selfSign 1` → `os.replace` → `chmod 0755`，
  然后**重新读一遍 `.codesign` 段**作为判据（不用 `os.access(X_OK)`）。

## 补丁说明（5 个，全部为上游可提交形态）

1. `0001-cmake-remove-host-only-march-flag.patch`（portability）
   `cmake/compiler_options.cmake` 的 `COMMON_OPTIONS` 里有 `-march=x86-64`，对所有目标生效；
   交叉编译到 aarch64 时 clang 直接报 `unknown target CPU 'x86-64'`。删除该行（宿主专属优化项）。
   上游代码里 `-Werror` 相关行本身已被注释掉，`OPTIONS_AS_ERRORS` 默认 OFF，无 werror 问题。
2. `0002-cmake-consume-installed-cmake-packages.patch`（portability）
   - 顶层 `CMakeLists.txt`：去掉 `include(conan_install)`；
   - `src/CMakeLists.txt`：去掉 `option(SAMARIUM_USE_CONAN)`/`conanbuildinfo` 分支，改为
     `find_package(fmt CONFIG REQUIRED)` + `find_package(range-v3 CONFIG REQUIRED)` 并
     `target_link_libraries(samarium PUBLIC fmt::fmt range-v3::range-v3)`（公共头需要这两者的
     头文件 ⇒ 必须 PUBLIC 传播）；同时删除共享库的 `CXX_VISIBILITY_PRESET hidden` /
     `VISIBILITY_INLINES_HIDDEN YES` —— 源码中没有任何 visibility 标注，开着它们导出的符号
     几乎为零、消费者必然链接失败，而且会放大 OHOS libc++ 跨 DSO typeinfo 只比指针的问题；
   - `test/CMakeLists.txt`：去掉 `find_package(SFML ...)` 与 `sfml-graphics` 链接；去掉 7 个
     SFML 绘图示例目标（`examples/*.cpp` 均用 `App`/SFML 渲染，本包不构建）。
3. `0003-disable-sfml-dependent-app-gui-modules.patch`（portability）
   `src/samarium/CMakeLists.txt` 去掉 3 个 SFML 编译单元；`samarium.hpp` 去掉 `app.hpp`/`gui.hpp`。
4. `0004-test-run-registered-boost-ut-suites.patch`（test）
   上游 `test/tests/main.cpp` 是 `int main() {}` —— `Vector2.cpp`/`concepts.cpp` 里的两个
   `boost::ut::suite` 只在静态初始化时注册，从不调用 `cfg<>.run()`。
   **实测**：空 main 构建出的 `samarium_tests` 执行 0 条断言、ctest 记 1/1 Passed（空套件假通过，
   同仓库知识库 `DRAFT-box2d-2.4.1-ctest-empty-suite-false-pass`）；补上
   `int main() { return boost::ut::cfg<>.run() ? 1 : 0; }` 后输出
   `All tests passed (49 asserts in 4 tests)`。补丁只补"让用例真跑"的入口，用例集与断言一条未改。
5. `0005-grid-fix-out-of-range-member-access.patch`（bugfix）
   `graphics/Grid.hpp` 的 `at(size_t)` 两个重载里检查的是 `this->m_size`，而 `Grid<T>` 没有这个
   成员（应为 `this->data.size()`）。GCC 13+ 的 `-Wtemplate-body` 在**模板体**阶段直接判错
   （`error: 'class sm::Grid<T>' has no member named 'm_size'`），clang 因为 `this->` 的延迟查找
   在未实例化时不报——所以上游 CI 没暴露。交付的公共头必须能编译，故修正为合法成员访问（语义等价）。

## 测试

### 上游测试（真跑，`build()` 内硬门禁）

`ctest --test-dir <build_folder> -V --output-on-failure`：

```
1: Test command: <build>/test/samarium_tests
1: All tests passed (49 asserts in 4 tests)
1/1 Test #1: SamariumTests ....................   Passed    0.00 sec
100% tests passed, 0 tests failed out of 1
```

- 口径：上游 `test/` 下 3 个源文件（`tests/Vector2.cpp`、`tests/concepts.cpp`、`tests/main.cpp`）
  + 1 个 CTest 目标 `samarium_tests`；Boost.UT 实测 **4 个 test case（含 10 个 should 子用例）、
  49 条 expect 断言**（31 条来自 `Vector2.cpp`，18 条来自 `concepts.cpp`），**49/49 通过**。
- CI 的 host/build profile 同为 `ohos-aarch64` ⇒ 原生构建，测试二进制在 worker 直接执行
  （构建树里的 ELF 不受"安装态 ELF 不可 execve"限制）；`cross_building()`/`can_run()` 为假时
  配方会显式打印告警而不是静默跳过。
- L1c 门禁：构建日志里含 `ctest` 字面量。

### 消费者用例（39 项，外部可核对真值）

`test_package/test_package.cpp`：只 `#include "samarium/samarium.hpp"`、只链接 `samarium::samarium`
（`fmt`/`range-v3` 由包传递），检查项全部来自**独立于库实现**的真值：

- 显式欧拉的**离散闭式解** `y_N = y0 + v0·t + ½·g·t·(t+dt)` 与解析解 `y = y0 + v0t − ½gt²`
  （dt = 1/512 s、3 s、容差 1e-9；与解析解之差 ≤ ½|g|t·dt = 0.0287 m）；
- 抛体射程 `v²sin2θ/g`、最大高度 `v²sin²θ/(2g)`（含一阶离散化项 `v·sinθ·dt/2`）、飞行时间 `2v·sinθ/g`；
- 弹性碰撞等质量正碰交换速度 + 非重叠不变量（圆心距 = r1+r2）+ 无碰撞不产生伪冲量；
- 胡克定律 `F = k·x`（自然长度 0 力、拉伸 1 m 时 `a = k·x/m`、牛顿第三定律）；
- 平面几何：勾股、`πr²`、矩形面积、线段交点为 (0,0)、`atan2`、`to_degrees(π)`；
- `Trail` 滑动窗口不变量；PCG 均匀分布的值域/期望（20000 样本，容差 0.02）/同种子可复现。

实测：`消费者用例结果：39 项检查，0 项失败`。

### 交付形态自检（30 项 M）

`test_package/test_layout.py`（纯 Python 解析 ELF，不依赖 readelf/objdump/nm）：

库本体（`lib/` 仅 `libsamarium.so`、ELF64/ET_DYN/架构与 `settings.arch` 一致、`DT_SONAME`、
无 `DT_RPATH/RUNPATH`、`DT_NEEDED` 含 C/C++ 运行时、`.codesign` 段〔OHOS〕）、公共头契约
（关键头清单、45 个 `.hpp`、包含闭包、umbrella 不引用未交付模块、app/gui 头已裁净）、
包内纯净性（无测试源/示例/构建中间产物、无隐藏文件、顶层条目仅 include/lib/licenses、
conanmanifest）、许可原文（MIT 全文 + 上游版权人）、CMake 契约（`samarium::samarium` 目标、
`find_dependency(fmt/range-v3)`、组件依赖表、`-std=c++20` 传播、include 由
`${PACKAGE_FOLDER}/include` 派生）、pkg-config 契约（组件 `.pc` 的 `-lsamarium` 与 Requires 链、
聚合 `.pc`、`pkg-config --cflags --libs samarium` 真调用）、消费者二进制 `DT_NEEDED` 含
`libsamarium`、包内 `core/version.hpp` 与包版本一致。

实测（x86_64 Linux）：`29 项通过，0 项失败，1 项跳过`（跳过的 `.codesign` 段检查只在
OHOS 构建时执行 —— 本机没有 `binary-sign-tool`，脚本显式打印平台限制，不静默放过）。
OHOS 侧 30 项全部执行。

## OHOS CI 首轮实证（2026-10-02，CI 已修）

首轮 CI 在 `build()` 里跑 ctest 时失败，主包编译/打包全部成功，失败点是**运行测试二进制**：

```
1: Error loading shared library libsamarium.so: (needed by .../build/Release/test/samarium_tests)
1: Error loading shared library libfmt.so.8: (needed by .../build/Release/test/samarium_tests)
```

根因：**OHOS 不在 CMake 的已知平台表里 ⇒ CMake 不给可执行文件写 RPATH/RUNPATH**
（同一原因也导致需要 `CMAKE_SHARED_LIBRARY_SONAME_*_FLAG` 兜底），所以构建树里的
`test/samarium_tests` 既找不到同构建树的 `src/libsamarium.so`，也找不到依赖包的 `libfmt.so.8`
（本机 x86_64 上 CMake 会写 RUNPATH，所以本地跑得通、CI 上才暴露 —— 这类"宿主可过、OHOS 必挂"
的差异只能在 CI 上发现）。修法：ctest 调用显式带上
`LD_LIBRARY_PATH="<build_folder>/src:<fmt 包 libdir>:$LD_LIBRARY_PATH"`
（仓库同类先例：`libtrng/4.28` 的 ctest、`castxml/0.7.0` 的 `Environment()`）。
`test_package` 侧的 `LD_LIBRARY_PATH` **不是**这一轮的问题（见下节）。

## OHOS CI 第二轮实证（2026-10-10，build #79896）——`test_package` 里的加载失败

首轮修完之后 CI 走到了 `test_package`，在**运行消费者二进制**时失败：

```
samarium/1.0.0 (test package): RUN: "./test_samarium"
Error loading shared library libsamarium.so: (needed by ./test_samarium)
Error relocating ./test_samarium: _ZN2sm14ParticleSystem11apply_forceENS_9Vector2_tIdEE: symbol not found
…（同一批 sm:: 符号全部 symbol not found）
ERROR: samarium/1.0.0 (test package): Error in test() method, line 57
	ConanException: Error 127 while executing
```

**先排除"找不到"**：本机用同一份 `test_package/conanfile.py` 跑 `conan create`，读
VirtualRunEnv 生成的 `test_package/build/*/generators/conanrunenv-release-*.sh`：

```
export LD_LIBRARY_PATH="…/p/b/samarc92de757b0011/p/lib:…/p/b/fmt0c76b4de3d257/p/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
```

⇒ conanrun **确实**把**被测包自己的 `<pkg>/lib`** 放进了搜索路径，所以 CI 那条报错
是「库在搜索路径上、加载器仍拒绝」（知识库 `E135`/`E517` 与 pangomm #66215 同形：
后者实测「libcairomm-1.0.so.1 在搜索路径上、是完好 ELF，加载器仍报 Error loading
shared library」），不是路径问题。

**处置**（`E517` 推荐做法 + 本仓 `pangomm/2.46.5` 已在 CI 上跑通的成熟模式）：
`test_package/conanfile.py::_run_consumer()` 里

1. 显式拼 `LD_LIBRARY_PATH`：conan 各依赖（含被测包）libdir（顶层聚合 + 每个组件）
   + SDK 的 `llvm/lib/aarch64-linux-ohos`（**只进搜索路径，绝不复制/重签 SDK 的
   libc++/libomp** —— pangomm #66255 实证签错会毁掉整个工具链）；
2. 把 **conan 依赖**（含被测包自己的 `libsamarium.so`）的 `.so` 复制到任务私有
   `rt-signed/`，逐个 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool
   sign -selfSign 1 -inFile X -outFile X.signed` + `os.replace` + `chmod 0755`，
   重签失败的副本**立即删除**（回退原件），并把它排在搜索路径最前；
3. 先用**交付态**路径真跑一次消费者（`subprocess`，`check=False`）：交付态能跑就用
   交付态，跑不动才切到 `rt-signed/` 副本 —— 两条路径都是**真执行**，且日志里留下
   `[runtime-diag]` 命中目录 / rc / stdout / stderr，下一轮 CI 若仍失败能一眼分清
   「找不到 / 签名被拒 / 真跑不动」。

`test_layout.py` 侧不变（仍对**交付包本体**断言 `.codesign` 段、`DT_SONAME`、
`DT_NEEDED`、包内无残留等）。

本机复跑（x86_64，非 OHOS 分支）：`conan create . …` → `rc=0`，
`[runtime-diag] 交付态可直接执行 ⇒ 官方用例走交付态路径`，
上游 CTest `1/1 Passed`（49 条断言真跑），消费者用例 39/39，交付形态自检
**29 通过 / 0 失败 / 1 跳过**，`[runtime-diag] libsamarium.so 在交付态搜索路径上
命中 1 个目录`。`grep -qE "self\.run.*(echo|print|true)" test_package/conanfile.py`
= 0 命中（CI 的 L1d 假测试门禁）。

## 验证状态

本机（x86_64 Linux，conan 2.29.1 + GCC 15.2，**没有 OHOS NDK**）用同一份源码 + 配方同款选项
跑通了整条链路：

```
conan create archives/s/samarium/1.0.0 -pr:h=default -pr:b=default -o 'fmt/*:shared=True' --build=missing
  → 主包 build/package 通过 → test_package 编译链接通过
  → 消费者用例 39/39 通过 → 交付形态自检 29 通过 / 0 失败 / 1 跳过（平台限制）
```

本机 `conan create` 用的是 conancenter 的 fmt/range-v3 制品（本机没有 cnb.cool 制品仓远端），
OHOS 侧由 CI 用制品仓里的 `fmt/8.1.1`、`range-v3/0.12.0` 构建；`fmt` 在 OHOS 是共享库
（本地实测 `-o fmt/*:shared=True` 时 `libsamarium.so` 的 `DT_NEEDED` 含 `libfmt.so.8`，
消费者可执行文件由 CMake 自动带上 RUNPATH，动态加载正常）。

OHOS（clang 15 / aarch64）的构建、上游 CTest 执行、消费者可执行与签名由平台 CI
（`ci/conan/build_and_test.sh`）完成；本 PR 正文只声明 CI 实际覆盖到的 head。

## 遗留风险 / 已知限制

1. `app`、`gui` 模块（基于 SFML 的窗口应用与输入）本次不交付：需要先把 SFML 的 Window/Graphics
   移植到 OHOS（无 X11/DRM/UDev 后端），属于另一个依赖包任务；本包在 `manifest.yaml` 的
   `modules_disabled` 里写明理由，不做"能力已提供"的虚假声明。
2. 本机无 OHOS 工具链 ⇒ 签名步骤、`.codesign` 段检查、AArch64 架构检查只能由 CI 实测；
   本机验证覆盖了同一份 recipe 逻辑（`--expect-ohos` 之外的全部分支）。
3. 上游 7 个 `examples/*.cpp` 依赖 SFML 渲染，未纳入构建与测试；它们不是上游测试用例
   （`test/` 目录下的 Boost.UT 套件才是，已 100% 执行）。
4. `fmt/8.1.1` 是上游 `conanfile.py` 声明的版本（制品仓有，故严格对齐上游口径）。
