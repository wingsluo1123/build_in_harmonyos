# irony-mode 1.6.1 适配笔记

## 编译环境
- 构建系统: cmake（仅 server/ 子目录）
- 编译日期: 2026-10-09
- 编译器: clang/clang++（系统 SDK，target aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

conan create 全流程（CI ci/conan/build_and_test.sh，profile ohos-aarch64）：

1. `source()`：`get(strip_root=True)` 保留 tarball 布局（`irony.el` 与 `server/` 同级）。
2. `generate()`：CMakeToolchain 注入
   - `BUILD_SHARED_LIBS=OFF`（R26，application 无自有共享库）；
   - `CMAKE_POLICY_VERSION_MINIMUM=3.5`（cache 变量）；
   - `CMAKE_DISABLE_FIND_PACKAGE_Clang=TRUE`（SDK config 包引用缺失静态归档，见问题表 #2）；
   - `LIBCLANG_INCLUDE_DIR` / `LIBCLANG_LIBRARY`（llvm-config --includedir/--libdir 动态查询）；
   - `CLANG_RESOURCE_DIR`（SDK clang `-print-resource-dir`；clang 优先取自 llvm-config
     --prefix 推导的 `<prefix>/bin/clang`——generate 期裸 PATH 查找实测不可靠（CI run2
     WARN `No such file or directory: 'clang'`），另有 `<prefix>/lib/clang/<ver>` 结构兜底）。
3. `build()`：`cmake.configure(build_script_folder="server")` + `cmake.build()`，libclang 定位走上游 fallback `cmake/modules/FindLibClang.cmake`。
4. `package()`：`cmake.install()`（上游 install 规则 `DESTINATION ${CMAKE_INSTALL_BINDIR}`）+
   `binary-sign-tool sign -selfSign 1` 自签 `bin/irony-server`。
5. `package_info()`：`llvm-config --libdir` 动态设置 runenv `LD_LIBRARY_PATH`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 设备 CMake 4.x 拒绝 `cmake_minimum_required(3.0.2...3.27)` | CMake 4 移除了 <3.5 兼容 | `CMAKE_POLICY_VERSION_MINIMUM=3.5`，必须走 cache 变量（`cmake_minimum_required` 先于 project()/toolchain 变量处理，oscpack 先例） |
| 2 | `find_package(Clang)` config 模式配置失败（CI run1 实测）：`LLVMExports.cmake` 报 imported target `LLVMDemangle` 引用的 `lib/libLLVMDemangle.a` 不存在 | 系统 SDK 只发布共享库（libclang.so/libclang-cpp.so/libLLVM.so），ClangConfig/LLVMExports 却导出全部静态库 target，CMake 在 include 时逐个 EXISTS 检查即中断（Scout 预判 config 主路径可行，实测不成立） | `CMAKE_DISABLE_FIND_PACKAGE_Clang=TRUE` 强制走上游 fallback `FindLibClang.cmake`；`LIBCLANG_INCLUDE_DIR`/`LIBCLANG_LIBRARY` 由 llvm-config 动态查询后显式注入（find_path/find_library 跳过搜索，FPHSA 直接过） |
| 3 | CMakeLists 不在源码根而在 server/，且版本号读 `../irony.el` | 上游设计（elisp 与 server 同仓） | `source()` 用 `strip_root=True` 保布局；`cmake.configure(build_script_folder="server")` 指定源目录 |
| 4 | 运行期找不到 libclang.so | 安装后 rpath 被剥离，musl 加载器不搜 SDK libdir | `package_info()` 经 `llvm-config --libdir` 设 runenv `LD_LIBRARY_PATH`（append_path 进 conanrun.sh） |
| 5 | OHOS 上 ELF 未经签名不可执行 | 平台强制校验 .codesign 段 | `package()` 内 `binary-sign-tool sign -selfSign 1`（工具经 `shutil.which` 发现，R33） |
| 6 | OHOS 无 /tmp | musl 环境无 /tmp 挂载 | test_package 导出 `TMPDIR`（上游 `TemporaryFile` 依次探测 TMPDIR/TMP/TEMP/TEMPDIR 后兜底 /tmp） |
| 7 | libclang 运行期找不到 builtin 头（stddef.h 等） | 仅用 libclang 共享库时无法相对自身推导资源目录（上游注释 cfe-dev 2012 经典问题）；run2 首版配方 generate 期裸 PATH 查 `clang` 失败（WARN `No such file or directory: 'clang'`），`CLANG_RESOURCE_DIR` 实际未注入，CMakeCache 无该变量、上游 try_run 探测亦失败（CHECK_CLANG_RESOURCE_DIR_NUM_DIAGNOSTICS=1）；包外 TU 探针实测解析含 `<stddef.h>` 的文件报 `'stddef.h' file not found` | path-update 加固：clang 路径改由 llvm-config `--prefix` 推导（`<prefix>/bin/clang`，llvm-config 同期查询均成功），`-print-resource-dir` 失败再兜底 `<prefix>/lib/clang/<ver>` 结构探测；注入后上游 `check_clang_resource_dir()` 直接短路（其 HINTS 布局/版本后缀枚举最高 9.0.0，本就覆盖不了 15.0.4）；test_package 新增 TU 解析冒烟（负例必须产出诊断防空转，正例必须零诊断）作运行期证据。**run3 实测已验证**：cmake 命令行带 `-DCLANG_RESOURCE_DIR=<prefix>/lib/clang/15.0.4`、全程无 WARN，TU 冒烟正例零诊断、负例按预期产出 "use of undeclared identifier"；包外独立探针（仅 LD_LIBRARY_PATH）解析同一 TU 亦零诊断 |

## 源码修改

无补丁：1.6.1 源码在 OHOS aarch64 + clang 15 下原样编译通过（C++11 代码 + libclang C API，musl 兼容）。

## 依赖版本

- LLVM/Clang (系统 SDK): 15.0.4（libclang.so、clang-c 头、clang 资源目录 `lib/clang/15.0.4/include` 完整；ClangConfig/LLVMExports config 包引用缺失静态归档不可用，见问题表 #2）
- CMake: 设备 4.1.2（经 CMAKE_POLICY_VERSION_MINIMUM=3.5 兼容）
- Conan: OHOS 适配版 2.29.1

## 验证结果

```bash
irony-server --version
# irony-server version 1.6.1        <- 编译期取自 ../irony.el，证明 tarball 布局保持
# clang version 15.0.4 (...)        <- 运行期 clang_getClangVersion()，证明 libclang 动态链接可用

# TU 解析冒烟（test_package/test.sh，经 irony-server 行协议 parse/diagnostics）
# 正例：#include <stddef.h> + size_t → 零诊断（builtin 头经 CLANG_RESOURCE_DIR 找到）
# 负例：未声明符号 → 必须产出 "use of undeclared identifier" 诊断（防空转假通过）
```

CI 五级门禁（L0/L1/L2/L4/L5）见 ci-metadata.json 与 CI 日志。

## 注意事项

- **上游测试门禁**：上游 `server/test/` 只有 3 个 elisp ERT 测试（`make check` = `ctest --output-on-failure`），测的是 Emacs Lisp 前端而非 irony-server；设备无 emacs，`find_program(EMACS_EXECUTABLE)` 失败后上游 WARNING 并 return()（优雅跳过），ctest 为空测试集。irony-server 本身无任何 C++ 上游测试 → 记录 NO_UPSTREAM_TESTS（discovery 证据见 notes 与 run 报告）；test_package 冒烟（--version 两重断言 + TU 解析正/负例）作为替代验证。
- **空测试集陷阱**：勿把"ctest 通过（No tests were found）"当上游测试通过（box2d 假通过先例）。
- **CLANG_RESOURCE_DIR 诚实注记**：run2 首版构建实际未注入该变量（--version 冒烟掩盖了 TU 解析缺陷）；path-update 加固后已验证（run3）：变量成功注入（cmake 命令行 `-DCLANG_RESOURCE_DIR=<prefix>/lib/clang/15.0.4`，无 WARN），test_package TU 冒烟通过（正例零诊断、负例按预期报错），包外独立探针同样通过。
- elisp 前端不入 conan 包：用户侧经 MELPA 安装 irony.el 并指向本包的 irony-server 可执行文件即可（对齐 emacs-clang-complete-async 先例）。
- CI L2 冒烟直接执行包内二进制（无 conanrun 环境）：libclang.so 不在默认加载路径时 L2 显示 warn（非阻塞）；真实运行验证以 test_package（conanrun 环境）为准。
