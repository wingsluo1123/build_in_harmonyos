# OHOS libc++ 的 `<format>` 不完整：`_LIBCPP_ENABLE_EXPERIMENTAL`、缺 `std::format_error` 符号、无 chrono formatter

## 现象

在 OHOS SDK（clang 15 配套 libc++，`libcxx-ohos` 变体）上编译使用 C++20
`<format>`/`<ranges>` 的代码，依次遇到三类错误：

1. **头文件层面不可见**（未定义 `_LIBCPP_ENABLE_EXPERIMENTAL`）：
   ```
   error: no member named 'format' in namespace 'std'
   error: no member named 'views' in namespace 'std'
   ```
   根因：`<__config>` 在未定义 `_LIBCPP_ENABLE_EXPERIMENTAL` 且未
   `_LIBCPP_BUILDING_LIBRARY` 时，会定义
   `_LIBCPP_HAS_NO_INCOMPLETE_FORMAT` 与 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES`，
   于是 `<format>`/`<ranges>` 的内容被整体关掉。

2. **链接层面缺符号**（已定义 `_LIBCPP_ENABLE_EXPERIMENTAL`）：
   ```
   ld.lld: error: undefined reference due to --no-allow-shlib-undefined:
       vtable for std::__n1::format_error
       typeinfo for std::__n1::format_error
       std::__n1::format_error::~format_error()
   ```
   根因：`std::format_error` 的析构函数在头里只声明
   （`virtual ~format_error() noexcept;`），是类的 key function；vtable/typeinfo
   由库发射。而 OHOS 预编译的 `libc++.so` 未带 experimental 特性，不导出这些
   符号（`llvm-nm -D libc++.so | grep format` 为 0）。

3. **chrono formatter 缺失**（前两步解决后）：
   ```
   error: no member named 'parse' in
       'std::formatter<std::chrono::time_point<std::chrono::system_clock, ...>>'
   ```
   根因：该 libc++ 的 `<format>` 未实现 chrono formatter，
   `std::formatter<time_point>` 被 delete。

## 修复

```cmake
# ① 打开 experimental（Conan: tc.extra_cxxflags.append(...)）
add_compile_options(-D_LIBCPP_ENABLE_EXPERIMENTAL)
```

```cpp
// ② 在编译进共享库的 TU 内补 std::format_error 关键函数
#include <format>
namespace std {
format_error::~format_error() noexcept {
}
} // namespace std
```

```cpp
// ③ chrono 格式化改 strftime
-  std::format_to(std::back_inserter(buffer), "{0:%F} {0:%T}", std::chrono::system_clock::now());
+  const std::time_t now = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
+  std::tm tm{};
+  gmtime_r(&now, &tm);
+  char ts[32];
+  std::strftime(ts, sizeof(ts), "%Y-%m-%d %H:%M:%S", &tm);
+  buffer += ts;
```

## 与既有条目的边界

- `DRAFT-E5xx-ohos-libcpp-missing-ranges-algorithms`（kholidays 6.28.0）讲的是
  **ranges 算法重载缺失**（`std::ranges::none_of` 不存在 → 用迭代器对版本替换），
  与本条子族不同：本条讲 `<format>` 的三层问题（宏门控 / 库符号缺失 / chrono
  formatter 缺失），修法层位是「编译宏 + 库内补符号 + 输出方式替换」。
- 两条共享同一根因（裁剪版 libc++ 的 `_LIBCPP_HAS_NO_INCOMPLETE_*`），但触发点、
  错误文本、处方均不同，可作为相邻子族分别沉淀。

## 证据

- valhalla 3.8.2（任务 11598）：`valhalla/midgard/util.h` 用 `std::views::transform`
  （enumerate），`valhalla/midgard/logging.h` 用 `std::format_string/std::format`，
  `src/midgard/logging.cc` 用 `std::format_to` 格式化 `system_clock::now()`。
- 最小复现：`clang++ -std=gnu++20 -stdlib=libc++ -D_LIBCPP_ENABLE_EXPERIMENTAL`
  编译含 `std::format` 的程序，补 `~format_error` 定义后可链接运行。
- `llvm-nm -D <sdk>/lib/aarch64-linux-ohos/libc++.so | grep -c format` → 0。
