# DRAFT: OHOS libc++15 ranges 算法被宏隐藏 + C++23 contains 缺失 + std::format 无运行库符号（durak 2.1.1 实证）

## 现象（三类独立符号缺失，可组合出现）

1. **C1 — ranges 算法被宏守卫隐藏**：durak `game.hxx` 编译报
   `error: no member named 'find_if'/'count_if'/'transform'/'binary_search'/'copy_if'/'find' in namespace 'std::ranges'`（20 errors）。实现头 `__algorithm/ranges_*.h` 实际存在，但被 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES` 宏守卫。
2. **C2 — C++23 `std::ranges::contains` 完全缺失**：`no member named 'contains' in namespace 'std::ranges'`（game.hxx 两处），即使解锁 experimental 仍缺（libc++ 15 无 `__algorithm/ranges_contains.h`）。
3. **C3 — `std::format` 运行库符号缺失**：`ld.lld: error: undefined symbol: vtable for std::__n1::format_error`、`std::__n1::__throw_format_error`（print.hxx 使用 std::format 时链接失败）。

## 根因

- C1: OHOS SDK 26 配套 libc++ 15.0.4 `__config` 默认定义 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES`，C++20 ranges 算法被宏隐藏（实现文件在，仅不可见）。
- C2: `contains` 是 C++23 特性，libc++ 15 头文件未实现。
- C3: `<format>` 头声明可用（解锁后），但运行时库 `libc++.so` 未编译 format 部分（INCOMPLETE_FORMAT），头声明 → 运行库缺符号 → 链接失败。

## 修复（durak 2.1.1 实证）

- C1: 编译标志 `-D_LIBCPP_ENABLE_EXPERIMENTAL` 解锁 incomplete ranges，**无需改源码**；conan 配方 `generate()` 注入 `CMAKE_CXX_FLAGS`，并须经 `cpp_info.defines` 传导给消费者（`package_info.defines = ["_LIBCPP_ENABLE_EXPERIMENTAL"]`）。
- C2: 改写为 C++20 等价 `std::ranges::find(r, v) != std::ranges::end(r)`（`patches/0002-durak-game.hxx.patch`）。
- C3: 改写为 ostream 流式输出 `os << "Card: {" << v << " , " << name << "}"`（`patches/0004-durak-print.hxx.patch`），输出格式与上游一致。

## 验证

- 上游测试 25/25（63 断言）全过；消费者 test_package 1/1 通过；鸿蒙专项 15/15 [PASS]。
- conan-verify G0-G4/L2/L4/L5 全过；W3 本地 CI 模拟通过（L0i 依赖可用性恢复后）。

## 适用条件与反例

- **适用**: OHOS SDK 26 (clang 15 / libc++ 15) 上适配使用 C++20/23 ranges 算法或 `<format>` 的库。
- **反例**: clang 16+/libc++ 16+（ranges 完整、format 可用）不适用；GCC/libstdc++ 不适用（无此宏）。C1 方案只解决"实现存在但被宏隐藏"，不适用于实现头真的缺失的场景。

## 边界

- C1 与 DRAFT-E5xx-ohos-libcpp-missing-ranges-algorithms 触发域重叠（同 `std::ranges` 编译失败），但根因不同（宏守卫 vs 裁剪缺失）、方案不同（编译标志 vs 源码改写），**新增差异成立**。
- C2（C++23 特性回退）与 C3（运行库缺符号）无既有条目覆盖。
