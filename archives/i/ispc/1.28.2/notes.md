# ispc 1.28.2 适配笔记（HarmonyOS PC / aarch64 真机原生构建）

> 状态：设备验证完成（见 §6 实测统计）。计数口径与逐条归因见 `reports/test-report.md`（`reports/` 被
> `.gitignore` 忽略，不入 PR）。

## 1. 上游与版本

- 上游：https://github.com/ispc/ispc ｜ tag `v1.28.2` = commit `5bf8fb90b34122b55813d3198fb45c42478d51ca`
- 归档：`https://github.com/ispc/ispc/archive/refs/tags/v1.28.2.tar.gz`
  sha256 `0b7d1d73afa93c015814b99c97b88fa45bce822d7904e8fc4a95666ba8e3fb92`（20021526 字节，设备实测）
- 许可证 BSD-3-Clause；构建系统 CMake + Ninja（Release）

## 2. 依赖：`llvm-project/20.1.8`（裸 ref，本机 conan 缓存）

ISPC 1.28.2 的硬依赖面（源码实证）：

1. **Clang 前端库**：`CMakeLists.txt:411` `set(CLANG_LIBRARY_LIST clangFrontend clangBasic clangEdit
   clangLex clangSupport clangASTMatchers)`，`CMakeLists.txt:813-826` 用
   `find_library(<lib>Path NAMES libclangX.a clang-cpp HINTS ${LLVM_LIBRARY_DIRS})` 定位；
   `src/preprocessor.cpp`、`src/module.cpp`、`src/binary_composite.cpp` 直接 `#include <clang/...>`。
2. **LLVM 版本 18.1–21.1**（`src/ispc_version.h` 的 `LATEST_SUPPORTED_LLVM` / `#error` 守卫）。
3. **后端齐备**：`llvm-config --targets-built` 必须同时含 **AArch64、ARM、X86**（详见 §3.1）。
4. **工具与 llvm-config 同目录**：`cmake/FindLLVM.cmake:28-56` 用
   `find_program(... NO_DEFAULT_PATH PATHS ${LLVM_TOOLS_BINARY_DIR})` 找 `clang`/`clang++`/`llvm-as`/
   `FileCheck`，并 `find_program(LLVM_CONFIG_EXECUTABLE)`。依赖包 `package_type=library` ⇒ `bindirs`
   不进 PATH ⇒ 必须显式 `-DLLVM_CONFIG_EXECUTABLE=<pkg>/bin/llvm-config`。

实测本机依赖包（`conan list 'llvm-project/*'` 命中裸 ref 与 `@ohpcd/stable` 两个 ref）：

| 读数 | 值 |
|---|---|
| `llvm-config --version` | `20.1.8` |
| `llvm-config --targets-built` | `AArch64 ARM X86` |
| `bin/` | `clang`/`clang++`/`llvm-config`/`llvm-as`/`FileCheck` 齐备 |
| `lib/` | `libclangFrontend.a`…6 个 clang 组件 + `libclang-cpp.so` + `libLLVM.so.20.1`（SONAME `libLLVM.so.20.1`） |
| `lib/cmake/` | `llvm/LLVMConfig.cmake` + `clang/ClangConfig.cmake` |

> 该依赖是 2026-10-10 编排方按用户指令导入平台的独立依赖任务产物（`llvm-project 20.1.8`，
> rawId 15037，`feat/llvm-project-20.1.8`，单独 PR）。**截至本 PR 尚未合入/发布到远端 ohpcd**，
> 故远端 CI 面解析不到该依赖；本机验证走 conan 缓存。

## 3. 适配点（4 项配置 + 1 个补丁）

### 3.1 目标面由 `llvm-config --targets-built` 自适应（不硬编码）

`generate()` 断言依赖后端必须同时含 `AArch64`/`ARM`/`X86`（缺一即 fail fast 并给出原因）；
`build()` 按实际 targets 置 `X86_ENABLED`/`ARM_ENABLED`：

- **AArch64**：本平台主机架构目标；
- **ARM**：`cmake/FindLLVM.cmake:147-151` 只在 `--targets-built` 同时含 AArch64 与 ARM 时才置
  `LLVM_SUPPORTS_ARM=ON`；否则 `ARM_ENABLED` 默认 OFF，而 aarch64 宿主上 `X86_HOST=OFF` ⇒
  `CMakeLists.txt:357` 直接 `FATAL_ERROR "Either X86, ARM, WASM or XE targets need to be enabled."`；
- **X86**：上游 lit 有 **167 个** `REQUIRES: X86_ENABLED` 用例（在 aarch64 主机上只做 codegen、
  不执行 x86 机器码），缺后端即被 lit 判 UNSUPPORTED，通过率结构性达不到 90%。

⇒ **本包不含任何「AArch64-only LLVM」补丁**：该约束在最终依赖形态（AArch64;ARM;X86）下不存在，
为不存在的条件改上游源码不可取（前一版骨架里的 `patches/0001-aarch64-only-llvm.patch` 已删除）。

### 3.2 补丁 `patches/0001-host-libcxx-verbose-abort-noexcept.patch`（1 处条件）

- **症状**：`src/util.cpp:50:11: error: exception specification in declaration does not match previous
  declaration`（编译期，第一处编译错误）。
- **根因**：ISPC 自定义 `std::__libcpp_verbose_abort` 时按 **ISPC_LLVM_VERSION >= 20** 决定是否加
  `noexcept`，隐含假设「宿主 libc++ 与所链接 LLVM 同版本」。OHOS 上 LLVM 是 20.1.8，而宿主
  libc++ 是 SDK 的 **15.0.4**：
  - libc++ 20.1.8（`libcxx/include/__verbose_abort`）：`... void __libcpp_verbose_abort(const char*, ...)
    _LIBCPP_VERBOSE_ABORT_NOEXCEPT;`（`_NOEXCEPT` ⇒ noexcept，`_LIBCPP_VERSION 200100`）
  - libc++ 19.1.7 同文件：无 `noexcept`（实测下载核对）
  - OHOS SDK libc++ 15.0.4（`_LIBCPP_VERSION 15004`）：`_LIBCPP_NORETURN _LIBCPP_OVERRIDABLE_FUNC_VIS
    _LIBCPP_ATTRIBUTE_FORMAT(...) void __libcpp_verbose_abort(const char *__format, ...);`（无 noexcept）
- **改法**：把该条件由 `ISPC_LLVM_VERSION >= ISPC_LLVM_20_0` 改为 `_LIBCPP_VERSION >= 200000`
  （跟随**宿主** libc++ 的声明），并加注释说明原因。只此一处，不改任何运行期行为。
- **验证**：`patch -p1 --dry-run` rc=0；应用后与手工修改树逐字节一致；改后该文件编译通过。

### 3.3 链接选项：关闭 `ISPC_STATIC_LINK`（否则 `ispc` 一启动即 `std::bad_cast`）

- **症状**：构建产物 `bin/ispc` 连 `--version` 都跑不起来：
  `libc++abi: terminating due to uncaught exception of type std::bad_cast`。
- **最小复现**（设备实测，3 行 iostream 程序）：
  | 命令 | NEEDED | 结果 |
  |---|---|---|
  | `clang++ t.cpp -lLLVM-20` | `libLLVM.so.20.1` + `libc++_shared.so` | ✅ 正常 |
  | `clang++ t.cpp -static-libstdc++ -lLLVM-20` | `libLLVM.so.20.1`（无 libc++_shared） | ❌ rc=134 `std::bad_cast` |
  | `clang++ t.cpp -static-libstdc++` | 无 libc++_shared | ✅（静态 libc++ 自洽） |
  ⇒ 根因：可执行文件**静态链入 libc++**，而依赖包 `libLLVM.so.20.1` 动态链接 `libc++_shared.so`
  ⇒ 同一进程两份 libc++（同名 `std::__n1` ABI 命名空间），首个 iostream/locale 使用即 bad_cast。
- **来源**：`ISPC_PREPARE_PACKAGE=ON` 会把 `ISPC_STATIC_LINK` 默认置 ON（`CMakeLists.txt:292-296`），
  于是 `CMakeLists.txt:794-799` 追加 `-static-libgcc -static-libstdc++`；在 OHOS 的 clang 上
  `-static-libstdc++` 对 libc++ 同样生效（设备默认是动态 `libc++_shared.so`）。
- **改法**：配方显式传 `-DISPC_STATIC_LINK=OFF -DISPC_STATIC_STDCXX_LINK=OFF`（`ISPC_STATIC_LINK`
  在 ISPC 源码里**只**用于加这两个链接选项，无其它语义）。产物 `bin/ispc` 的 NEEDED 变为
  `libLLVM.so.20.1` + `libc++_shared.so` + `libc.so`（`libc++_shared.so` 由 `/system/lib64` 解析）。
  （CI 红修复后 `ISPC_PREPARE_PACKAGE=OFF` ⇒ 该默认本就为 OFF，这两个显式开关成为冗余防御，
  保留不动以维持最小 diff 与显式意图。）

### 3.4 builtins-c++ 位码静默为空 ⇒ `undefined symbol: __do_print`（上游构建缺陷 + 配方绕行）

- **症状**：func-tests 21 个用例链接期失败：
  `ld.lld: error: undefined symbol: __do_print`（21 个 print/asin 用例）。
- **根因（上游缺陷，双重）**：
  1. `cmake/GenerateBuiltins.cmake:260` 编译 `builtins/builtins-c-cpu.cpp` 时写死
     `-isystem/usr/${debian_triple}/include`（Debian/Ubuntu multiarch 交叉 sysroot）。OHOS 上该路径
     不存在 ⇒ `clang++` 报 `builtins-c-cpu.cpp:42:10: fatal error: 'unistd.h' file not found`。
  2. 该自定义命令是**管道**：`clang++ … -o - | llvm-as -o out.bc`，shell 只取最后一个命令的退出码
     ⇒ clang++ 的失败被**静默吞掉**，`llvm-as` 对空输入产出**空模块**。
- **实测证据**：修复前 4 个 `share/ispc/builtins_cpp_*.bc` 均为 **1304 字节**（空模块）；
  `llvm-nm`（依赖包 LLVM 20 版本）读不到任何符号；改用修复后的命令重编得 ~140 KB LLVM IR、
  `__do_print` 定义数 = 1。
- **改法（不改上游源码）**：把 `CLANGPP_EXECUTABLE` 指向配方生成的薄包装脚本，令其补上**宿主
  clang 自己问询出来的 C 头目录**（`clang -E -x c -v` 的 `#include <...>` 搜索列表，剔除
  clang resource-dir，按 `-isystem` 注入，保持系统头语义）。`CLANGPP_EXECUTABLE` 只被
  `GenerateBuiltins.cmake` 的 dispatch 与 builtins-c++ 两处编译使用；`find_program` 对已缓存值不
  覆盖，故 `-DCLANGPP_EXECUTABLE=` 生效（实测 `build.ninja` 6 处引用包装脚本）。
- **回归护栏**：`build()` 在编译后硬校验 `share/ispc/builtins_cpp_*.bc` 均 ≥ 8 KiB，否则
  `ConanException`（把这个「空模块」失败模式变成显式失败，不再拖到下游链接期）。

### 3.5 lit 的 `%{cc}`/`%{cxx}` 被依赖包的裸 `clang` 遮蔽

- **症状**：lit 22 个 FAIL 中 20 个是 `'stdio.h' file not found` / `'iostream' file not found` /
  `ld.lld: error: unable to find library -lc`。
- **根因**：`tests/CMakeLists.txt:12-17` 依次追加
  `--path=${CMAKE_RUNTIME_OUTPUT_DIRECTORY}`（=`<build>/bin`）与 `--path=${LLVM_TOOLS_BINARY_DIR}`
  （=依赖包 `bin/`）；lit 把它们**按序前置**到测试 PATH（`utils/lit/lit/LitConfig.py:33` +
  `TestingConfig.py`：`PATH = os.pathsep.join(litConfig.path + [os.environ['PATH']])`）。
  依赖包 `bin/` 自带一套 `clang`/`clang++`（target `aarch64-unknown-linux-ohos`，不带 sysroot），
  于是 lit 里所有 `clang`/`clang++` 步骤拿到它而非设备工具链。
- **改法（不改上游测试）**：`_run_upstream_tests()` 在 `<build>/bin`（lit PATH 中排在依赖包 bin
  **之前**）写入 `clang`/`clang++` 两个薄包装脚本，指向设备工具链
  `/data/service/hnp/bin/{clang,clang++}`。只覆盖这两个名字；`FileCheck`/`llvm-as` 仍按依赖包 bin
  解析（保持与所链接 LLVM 20 同版本）。
- **效果**：1415.ispc 单例复跑（compile→link→run→FileCheck）四项 rc=0。

### 3.6 其他平台适配（与本仓 llvm/clang 同族）

- 设备 `uname -s = HarmonyOS`，CMake 无 `Platform/HarmonyOS.cmake` ⇒ `build()` 生成
  `include(Platform/Linux)` 的 stub 挂到 `CMAKE_MODULE_PATH`；不设 `CMAKE_SYSTEM_NAME`（保持 native，
  使构建期需要运行的生成步骤原生化）。
- `package()` 后用 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`
  重签 `bin/` 与 `lib/*.so`（OHOS 要求）。
- 构建期需要 `flex>=2.6`、`bison>=3.0`、`m4`、`python3`（lit）、`ninja`：设备 HNP 工具链自带。
- **CI 红修复（build#89756，2026-10-13）**：`ISPC_PREPARE_PACKAGE` 由 ON 改为 **OFF**。
  上游 ON 发布路径（CMakeLists.txt:1181-1209）注册 `ExternalProject_Add(ispc_web)`——**构建期**
  `git clone https://github.com/ispc/ispc.github.com.git`（仅把文档站 HTML 拷进安装树）。本机
  （设备）可达 github 故首轮通过；CI worker 不可达（r3 build#89756 在 901/932 步
  `ispc_web-download` 报 `Failed to connect to github.com port 443`，重试 3 次后 CMake Error
  `Failed to clone repository` ⇒ ninja 停止）。置 OFF 后该 ExternalProject 根本不注册，构建完全
  离线。随之失去的静态随包文件（LICENSE.txt/third-party-programs.txt/docs/ReleaseNotes.txt/
  contrib/、examples/ 排除 xpu）全部是源码树内文件，由 `package()` 的
  `_package_upstream_static_files()` 从源码目录拷齐（产物等价）；唯一不再随包的是 web HTML
  （faq.html/ispc.html/perfguide.html/css/）——ispc.github.io 网站内容，不参与编译/链接/运行，
  test_package 与下游消费均不引用。另：OFF 时上游会安装 `bin/check_isa`（ON 时不安装），
  旧包不含它，`package()` 内移除以保持产物面等价。
- **CI 红修复（build#91471，2026-10-14）：test_package 的 C++ 编译器必须按绝对路径解析**。
  旧 `test_package/conanfile.py` 用 `os.environ.get("CXX", "/data/service/hnp/bin/clang++")`。
  CI worker 上环境变量 `CXX` 是**裸名** `clang++`（worker env dump 无 CXX，注入点在其后），
  而 `test()` 的 `self.run(..., env="conanrun")` 会把依赖包 `llvm-project` 的 `bin/`
  **前置**进 PATH（conan `runenv_from_cpp_info`: `_prepend_path("PATH", cpp_info.bindirs)`），
  其中的 clang++ 是 LLVM 20 工具链、无 OHOS sysroot、无 libc++ 头搜索路径 ⇒ 裸名必被它遮蔽，
  报 `fatal error: 'cmath' file not found`（r4 逐字签名；本机「依赖 bin 前置 + CXX 裸名」
  两行复现同款报错）。修复：`_resolve_cxx()` 按
  `tools.build:compiler_executables["cpp"]`（profile 注入的绝对路径）→ `CXX`（仅当绝对路径
  且存在）→ 设备绝对路径 `/data/service/hnp/bin/clang++` 取第一个可用的**绝对路径**，
  拒绝裸名走 PATH，全部不可用即 `ConanException` fail fast。本地此前能过只是因为 CXX 未设置时
  旧代码恰好落到默认绝对路径——确定性不能依赖环境运气。

## 4. 消费方式（LLVM_DIR / Clang_DIR 均由依赖包提供）

- `FindLLVM.cmake` **不调用 `find_package(LLVM)`/`find_package(Clang)`**：它先 `find_program(
  LLVM_CONFIG_EXECUTABLE ...)`，再由 `llvm-config` 推导 `LLVM_LIBRARY_DIRS`/`LLVM_TOOLS_BINARY_DIR`；
  clang 组件库经 `find_library(... HINTS ${LLVM_LIBRARY_DIRS})` 命中。
- 配方显式传 `-DLLVM_CONFIG_EXECUTABLE=<pkg>/bin/llvm-config`、`-DLLVM_DIR=<pkg>/lib/cmake/llvm`
  （后者只被 FindLLVM.cmake 打印/记录，用于在 configure 日志中显示依赖来源）。
  **不传 `-DClang_DIR`**：实测 CMake 会警告 `Manually-specified variables were not used by the
  project: Clang_DIR`（ISPC 不消费它）。
- 实测 configure 读数（`CMakeCache.txt`）：6 个 clang 组件全部解析到
  `<pkg>/lib/libclang*.a`，`CLANG_EXECUTABLE`/`CLANGPP_EXECUTABLE`/`LLVM_AS_EXECUTABLE`/
  `FILE_CHECK_EXECUTABLE` 全部落在 `<pkg>/bin`。

## 5. 测试口径与取数（AGENTS §3.5）

- `TOTAL = PASS + FAIL + SKIP + NOT_RUN`；lit 的 `Unsupported` 与 `Expectedly Failed` 计入 **SKIP**，
  **不写 PASS**；`test_package` 消费者用例与鸿蒙特有测试**分栏、不计入上游分母**；断言数只披露不并入。
- **N（上游总数）= 2223** = lit 647（639 `.ispc` + 5 `.ll` + 3 `.cpp`）+ func-tests 1576
  （`tests/func-tests/*.ispc`）；候选数法最大值，逐项归因见 `reports/test-report.md`。
- 复算命令（设备可直接执行，证据目录 `$HOME/tmp/ispc-1.28.2/`）：
  ```sh
  # 静态清点（逐用例 requires/targets/两种后端配置下的归类）
  python3 $HOME/tmp/ispc-1.28.2/testlists/classify.py <ispc-src> $HOME/tmp/ispc-1.28.2/testlists
  # 跑两套上游测试 + 解析四分项（<work-dir> 内 lit.log / run_tests.log）
  sh     $HOME/tmp/ispc-1.28.2/testlists/run_upstream_tests.sh <build-dir> <ispc-src> <work-dir> 4
  python3 $HOME/tmp/ispc-1.28.2/testlists/parse_results.py <work-dir>
  ```
- 配方内真实运行：`build()` 的 `with_upstream_tests`（默认 ON）依次跑
  `cmake --build <build> --target check-all` 与
  `cd <src> && ISPC_HOME=<build>/bin python3 scripts/run_tests.py -t neon-i32x4 -a aarch64 -o O2
  -c clang++ -j N --non-interactive --time --fail_db tests/fail_db.txt`
  （**必须从源码根运行**：`get_test_files()` 用 `./tests/func-tests/*ispc` 相对 CWD 取用例，
  在别处运行会得到空列表并 `ValueError: max() iterable argument is empty`），日志落
  `ISPC_TEST_EVIDENCE_DIR`（未设置则落 build folder），并把四分项与通过率打印到构建日志。
- **口径注意（CI 实测，build#91471）**：`run_tests.py` 汇总行 `N / M tests PASSED` 的分母
  `M = len(results)`（`print_result`，run_tests.py:1142）是**回流结果数**而非用例总数；
  结果经 `multiprocessing.Queue` 回流，主进程在 `test_queue.join()` 后用
  `while not qret.empty()` 排空（run_tests.py:1278）——`empty()` 对「feeder 线程尚未 flush
  的在飞结果」返回 True，慢盘 worker 上会吞掉部分结果（worker 侧 `qret.put()` 先于
  `queue.task_done()`，run_tests.py:832-836，故 join() 返回即用例**全部已执行**，丢的只是
  计数回执）。r4 CI 实测丢 383 条（1576-1193=383=379 PASS+4 SKIP，FAIL 0 未受染），
  故 CI 日志显示 `1188/1193`（94.24%）而设备轮为 `1567/1576`（99.43%）——**用例集合与
  执行数两侧相同（1576），仅回执回收数不同**；N=2223 静态清点口径不受影响，
  CI 侧分母收缩不构成「申报↔实物不一致」（申报以静态清点 + 设备轮全量日志为准）。

## 6. 实测统计（设备真机，2026-10-11）

命令与日志：`build()` 内真实运行两套上游测试（`with_upstream_tests` 默认 ON），最终设备轮
（`conan create` 干净缓存）日志落 `$TASK_DIR/w3-evidence-clean/{lit.log,run_tests.log}`，
`conan create` 全量输出落 `reports/conan-create.log`。

| 套件 | TOTAL | PASS | FAIL | SKIP | NOT_RUN | 通过率 |
|---|---|---|---|---|---|---|
| lit（`check-all`） | 647 | 546 | 3 | 98 | 0 | 84.39% |
| func-tests（`run_tests.py`） | 1576 | 1567 | 0 | 9 | 0 | 99.43% |
| **上游合计** | **2223** | **2113** | **3** | **107** | **0** | **95.05%** |

- lit 的 SKIP 98 = `Unsupported` 94 + `Expectedly Failed` 4（后者为上游自带的 XFAIL 用例）；
  func-tests 的 SKIP 9 = 上游测试文件内 `// rule: skip on ...` 自声明（`clock` 因 `arch=aarch64`、
  `transcendentals-sincos*`/`transcendentals-10-0` 因 `OS=*`、`xe-task-*` 因 `arch=*`）。
- **lit 的 94 个 Unsupported 里有 8 个是「宿主 OS 判定」造成**：`tests/lit-tests/lit.cfg:193` 用
  `platform.system() == "Linux"` 决定 `LINUX_HOST` 特性，而 `conan create` 的 buildenv PATH 选中的是
  OHOS Python（`/storage/Users/currentUser/usr/local/bin/python3.12`，`platform.system()` =
  `HarmonyOS`）⇒ 8 个 `REQUIRES: … LINUX_HOST` 用例（`2866`/`arm_linux`/`arm_dotprod`/
  `debug_type_dwarf_2`/`ffunction-sections`/`fminnm_vminnm_arm`/`ftz_daz_flags_arm`/
  `generic-target-arm`）判 UNSUPPORTED。同一配方换用 harmonybrew python3.13
  （`platform.system()` = `Linux`）复跑则这 8 个**全部 PASS**（本机实测 554/647）。两种口径都
  ≥90%，本包统一采用**最终设备轮**（conan create）的日志口径 = 546/647。
- **3 个 FAIL 全部是上游测试的 host=x86 假设**，非适配缺陷（逐条证据见 `reports/test-report.md`）：
  1. `math-lib-value.ispc`：`REQUIRES: X86_ENABLED`，但 RUN 行用 `--target=host`；aarch64 宿主上
     ISPC 直接报 `Error: SVML math library is supported for x86 targets only.`（该 guard 应为
     `X86_HOST`）。
  2. `2780-1.ispc`：用 `--target=avx512skx-x8` 生成头文件后交给宿主 C 编译器编译，aarch64 clang
     对 `<xmmintrin.h>` 报 `"This header is only meant to be used on x86 and x64 architecture"`。
  3. `3571.ispc`：`--target=avx2-i32x8` 生成 x86 目标文件后用宿主 clang 链接执行 ⇒
     `ld.lld: error: … .o is incompatible with aarch64linux`（RUN 行还带 `-lstdc++`，OHOS 只有 libc++）。
- 鸿蒙分栏（**不计入上游分母**）：`test_package` 1 个消费者用例（`conan create` 自动执行）——
  `ispc --version` 冒烟 → `neon-i32x4` codegen → `--target=host` 生成 asm → `clang++` 链接并执行，
  含 `add_arrays` 逐元素 64 项 + `dot_product` 容差比较，**全部通过**（断言 66 项）；
  实测输出 `ispc probe ok: add_arrays(64) + dot_product = 43680.000000`。



## 7. 补丁与配置改动清单

| # | 类型 | 位置 | 作用 |
|---|---|---|---|
| 1 | 补丁 | `patches/0001-host-libcxx-verbose-abort-noexcept.patch` | `noexcept` 规格跟随宿主 libc++ 版本（§3.2） |
| 2 | 配置 | `-DISPC_STATIC_LINK=OFF -DISPC_STATIC_STDCXX_LINK=OFF` | 避免静态 libc++ 与 `libLLVM.so` 的动态 libc++ 冲突（§3.3） |
| 3 | 配置 | `-DCLANGPP_EXECUTABLE=<wrapper>` | 给 builtins-c++ 编译补宿主 C 头目录，避免空位码（§3.4） |
| 4 | 构建期产物 | `<build>/bin/{clang,clang++}` 包装脚本 | lit 的 `%{cc}`/`%{cxx}` 用设备工具链（§3.5） |
| 5 | 配置 | `-DX86_ENABLED`/`-DARM_ENABLED` 由 `--targets-built` 自适应 + `generate()` 断言 | 目标面与依赖形态一致（§3.1） |
| 6 | 配置 | `-DLLVM_CONFIG_EXECUTABLE` / `-DLLVM_DIR` | 依赖包 bindirs 不进 PATH 时的定位（§4） |

**未修改任何上游测试用例**（`tests/**` 零改动；补丁只作用于 `src/util.cpp`）。
