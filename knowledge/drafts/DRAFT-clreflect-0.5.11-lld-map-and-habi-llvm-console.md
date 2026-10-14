# DRAFT — clReflect 0.5.11 OHOS 适配：lld map 解析 + SDK LLVM `__h` ABI 消费闭环

- contributor: pc1-2
- 日期: 2026-10-04
- 软件: clreflect 0.5.11（Celtoys/clReflect — C++ 运行时反射库）
- 状态: UNMATCHED（待人工审核提升为 E-entry）
- 对应文件: `DRAFT-clreflect-0.5.11-lld-map-and-habi-llvm-console.kv`

## 问题

OHOS PC 上适配 ClangTool-based 工具/库（clReflectScan 一族）与反射调用测试时，遇到四类平台陷阱：

1. **SDK LLVM monolith ABI 命名空间不一致**：OHOS SDK 预编译 `libclang-cpp.so`/`libLLVM-15.so`
   以 libc++ ABI 内联命名空间 `std::__h` 构建；设备对外头（libcxx-ohos）与 `libc++_shared.so`
   为 `std::__n1`。经 clang C++ API（ClangTool/tooling 模板实例化）消费 monolith 时符号 ABI
   全不匹配（`reference to unresolved using declaration` / 链接期 undefined `std::__h` 符号）。
   需自定义 `__config_site` 强制 `_LIBCPP_ABI_NAMESPACE __h` 编译消费方 TU；对外发布的静态库
   可保持默认 `__n1` 供普通消费者链接。

2. **lld map 格式 ≠ GNU ld map 格式**：OHOS 工具链默认 lld，`-Wl,-Map` 输出为固定列宽
   `VMA LMA Size Align Out In Symbol` 布局，符号已 demangle；GNU ld 的 map 首行是
   `Archive member included because of file (symbol)`，符号需 `abi::__cxa_demangle`。
   按 GNU 格式解析的工具（clReflectExport MapFileParser）报 `Unknown format of gcc map file!`，
   函数地址丢失 → 运行时 `CallFunction` 断言崩溃。

3. **GetLoadAddress()=0 → 函数地址重定位失效**：OHOS 上 `dlopen(0)+dlsym("_start")` 返回 0，
   RebaseFunctions 无法把 map VMA 相对地址换算为运行时绝对地址；依赖 map 函数地址的测试二进制
   必须非 PIE 链接（`-fPIC` + `-no-pie`），使 map VMA == 运行时绝对地址。

4. **跨平台 C++ 库内联 x86 汇编在 aarch64 不合法**：`asm("int $0x3")` 断言需改为
   `__builtin_trap()`（x86 分支保留原汇编）。

另含上游 tag 缺陷：clReflectScan 的 CMakeLists 引用 tag 中不存在的 `ClangFrontend.cpp`。

## 根因

- OHOS SDK LLVM monolith `__h` ABI 设计（与设备默认 `__n1` 分叉）。
- OHOS 默认 lld 链接器（与 GNU ld 的 map 输出契约不同）。
- OHOS 运行库符号解析通道（dlopen/dlsym）对主程序 `_start` 不可用。

## 方案（四件套闭环）

| # | 动作 | 落点 |
|---|------|------|
| a | 自定义 `__config_site` 强制 `_LIBCPP_ABI_NAMESPACE __h`，仅注入 LLVM 消费目标；scan 用 ABI 专用核心库副本，对外库保持 `__n1` | conanfile.py `generate()` + clReflectScan/CMakeLists.txt |
| b | 解析工具增加 lld map 分支（列解析 VMA + 直接消费 demangled 符号，跳过 `$x.0`/`obj:(.text)` 行） | clReflectExport/MapFileParser.cpp |
| c | 函数地址相关测试二进制 `-fPIC`+`-no-pie` 链接（与 `-Wl,-Map` 合并进同一 LINK_FLAGS） | clReflectTest/CMakeLists.txt |
| d | `cmake_minimum_required` ≥3.5（CMake 4.x 移除 <3.5，同 E103） | 顶层 CMakeLists.txt |

## 验证

- conan create 全流程通过；上游 clReflectTest exit 0，36 PASS / 0 FAILED；
- test_package 消费方（链接 `__n1` 静态库 + `clcpp::internal::HashNameString`）PASS；
- map 解析后函数地址正确写入 cppbin（clReflectTest 构造函数/析构函数可调用）。

## 适用边界 / 反例

- 适用：ClangTool C++ API 消费 SDK LLVM monolith 的库；解析 `-Wl,-Map` 输出的工具；
  依赖 map 函数地址的反射调用测试。
- 反例：纯 C API（libclang.h）无 ABI 覆盖需求；静态链接 LLVM 源码的构建无 lld map 差异；
  header-only / 无函数地址场景无需非 PIE。

## 关系

- similar_to: E218（LLVM monolith 消费）、DRAFT-ohos-sdk-llvm-h-abi-iostream-shim（`__h` ABI）
- caused_by: OHOS SDK LLVM monolith `__h` ABI 设计 + lld 默认链接器
- conflicts_with: 无
