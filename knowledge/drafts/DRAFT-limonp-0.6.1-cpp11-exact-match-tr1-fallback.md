# DRAFT: 老代码 `#elif(__cplusplus == 201103L)` 精确匹配 ⇒ C++17 掉进 tr1 fallback 编译失败

- **ID**: DRAFT-limonp-0.6.1-cpp11-exact-match-tr1-fallback
- **来源**: limonp 0.6.1（yanyiwu/limonp）OHOS 适配，G2 conan create 复现
- **日期**: 2026-10-04
- **作者**: 2301_76770579
- **关联归档**: archives/l/limonp/0.6.1（patch 0002 StdExtension.hpp、0003 StringUtil.hpp）

## 问题

limonp 0.6.1（2016 年）的 `include/limonp/StdExtension.hpp` 用阶梯分支选择
标准库容器实现：

```cpp
#ifdef __APPLE__
#include <unordered_map>
#include <unordered_set>
#elif(__cplusplus == 201103L)      // ← 精确相等！
#include <unordered_map>
#include <unordered_set>
#elif defined _MSC_VER
#include <unordered_map>
#include <unordered_set>
#else
#include <tr1/unordered_map>        // ← C++17 下掉到这里
#include <tr1/unordered_set>
namespace std {
using std::tr1::unordered_map;
using std::tr1::unordered_set;
}
#endif
```

OHOS 平台全部库固定 `cppstd=17`（`__cplusplus == 201703L`），`== 201103L`
精确相等为假 ⇒ 走 `#else` 的 `<tr1/unordered_map>` 分支。libc++（LLVM 的
C++ 标准库实现，OHOS 默认）**从没有 tr1 目录**，编译报：

```
fatal error: 'tr1/unordered_map' file not found
#include <tr1/unordered_map>
```

同一文件/同库的 `StringUtil.hpp` 还用了 C++17 已移除的
`std::not1(std::ptr_fun(IsSpace))` 与 `std::bind2nd(std::equal_to<char>(), x)`，
在 libc++ 下同样报 `no member named 'ptr_fun'` / `no member named 'bind2nd'`。

## 根因

2000-2016 年代的 C++ 代码用 `__cplusplus == 201103L`（精确相等）判断"是否
C++11"是当时常见写法（C++11 刚发布时这样写没问题）。但 C++14/17/20 下精确
相等恒假，代码落入更老（tr1/boost）fallback 分支。这类阶梯还经常把
`std::ptr_fun` / `std::bind2nd` / `std::not1` 等 C++17 移除的仿函数适配器
一起编进来。

## 方案

最小 patch，不动构建系统：

1. `#elif(__cplusplus == 201103L)` → `#elif(__cplusplus >= 201103L)`：
   C++11/14/17/20 全部走 `<unordered_map>/<unordered_set>` 现代分支。
2. `std::not1(std::ptr_fun<unsigned, bool>(IsSpace))` →
   `[](unsigned c){ return !IsSpace(c); }`（lambda）。
3. `std::not1(std::bind2nd(std::equal_to<char>(), x))` →
   `[x](char c){ return c != x; }`（lambda）。

## 验证

- `clang++ -std=c++17 -I include -fsyntax-only`（修复前：`tr1/unordered_map
  file not found`；修复后：通过）
- `conan create` 干净构建 + `ctest -V`：3/3 ctest、35/35 gtest 全部通过
- 消费者测试（test_package，5 组断言，含 GBK 字节对打包鸿蒙特有断言）ALL PASS

## 适用范围

- 任何 2000-2016 年代、用 `__cplusplus == 201103L` 精确匹配做标准库分支的
  C/C++ 库，在 C++17/20（OHOS 默认 17）构建时命中。
- 同族：`std::ptr_fun/bind2nd/not1` 在 C++17 移除（见
  DRAFT-coinor-vol-1.5.4-std-bind2nd-removed-cpp17）。
- 反例/边界：C++11 精确相等在真 C++11 构建下不会触发；纯 tr1 时代代码若
  整个库只编 C++03 也不触发（但 OHOS 不可能）。

## 查重

- 正式知识（graph/E*.kv、index.tsv）：`201103L` / `tr1/unordered_map` /
  `__cplusplus` 关键字扫描**未命中**（E130 是 nullptr_t/libcxx 标准变更，
  E218/E224/E293 是 register 等关键字移除，均为同族但不同触发面）。
- 图谱 doc/：未命中。
- 草稿（drafts/）：DRAFT-coinor-vol（bind2nd/ptr_fun 移除）覆盖仿函数适配器
  部分；DRAFT-kytea（boost/tr1 未找到）覆盖 boost 特定路径。精确匹配陷阱
  本身无草稿覆盖 → **新增差异成立**。
- 关系：similar_to = E218/E224/E293、DRAFT-coinor-vol、DRAFT-kytea。
