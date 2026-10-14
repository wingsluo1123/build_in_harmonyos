# DRAFT — libzeep / libc++15 ranges binary_search 运行期误判

- **ID**: DRAFT-libzeep-libcxx15-ranges-binary-search-misjudge
- **分类**: libcxx | toolchain | clang | cxx20 | compat | ranges | serialization | html
- **触发**: libzeep 8.4.1 HarmonyOS PC 适配（archives/l/libzeep/8.4.1）
- **类似条目**: DRAFT-ohos-libcxx15-missing-cpp20-ranges-algorithms（互补：缺失类 → polyfill）

## 问题（error signature）

OHOS clang15/libc++15 在 `-D_LIBCPP_ENABLE_EXPERIMENTAL` 下，
`std::ranges::binary_search` **存在但运行期结果错误**：对不在表内的元素返回 `true`。

最小复现（bs_probe.cpp，`clang++ -std=c++2b -D_LIBCPP_ENABLE_EXPERIMENTAL`）：

| 查询 | std::ranges::binary_search | std::binary_search |
|---|---|---|
| "html"（不在 kEmptyHTMLElements） | **1（误判）** | 0（正确） |
| "br"（在表内） | 1 | 1 |

## 后果链（真实故障）

```
zeem is_empty_element("html") 误判 true
→ element::write 走 `(fmt.html and is_empty_element)` 自闭合分支
→ 输出 <html .../>（68 字节），全部子节点丢失
→ libzeep 登录表单缺 <input name="_csrf">
→ 上游 http-test server_with_security_1 失败（GET /login 仅回 340 字节）
```

**关键诊断信号**：编译完全正常，但功能测试失败 + HTTP 响应体明显截断
（登录页源码 ~1.5KB，实际响应 340 字节）——这类"静默数据丢失"要优先怀疑
ranges 查找类算法的运行期误判，而不是业务逻辑。

## 根因（root cause）

OHOS SDK clang 15.0.4 配套 libc++（LLVM 15）的实验性 ranges 实现（
`_LIBCPP_ENABLE_EXPERIMENTAL`）中 `std::ranges::binary_search` 结果不可信；
经典迭代器 `std::binary_search` 在同工具链上结果正确。

## 修复（rec_approach）

将查找改为经典迭代器算法，语义等价、结果正确：

```cpp
// 之前（误判）
return std::ranges::binary_search(kEmptyHTMLElements, el);
// 之后（正确）
return std::binary_search(kEmptyHTMLElements.begin(), kEmptyHTMLElements.end(), el);
```

数据表与调用处逻辑保持不变，仅更换算法调用形式。

## 验证（verification）

- bs_probe 最小复现：ranges=1/br=1 vs std=0/br=1（结果正确性比对）。
- 修复后 libzeep 上游 ctest **13/13 通过**（含 http-test 4.23s）。
- 鸿蒙专项测试 ohos_test（真实 HTTP daemon 往返）通过。
- conan create + test_package + consumer_app 全部通过。

## 适用范围与反例

- 适用：OHOS clang15/libc++15 + `_LIBCPP_ENABLE_EXPERIMENTAL` 下所有依赖
  `std::ranges::binary_search` / `lower_bound` 结果正确性的代码；尤其 HTML/XML
  序列化、空元素表驱动判断（zeem/zeep 系库）。
- 反例：非 OHOS 工具链（libc++ 16+ 或 libstdc++）ranges 查找正常，不应机械替换；
  若 ranges 调用本身编译失败（"no member named"）则属既有"缺失类"条目，
  应走 polyfill 方案，与本条目不同。

## 关系

- similar_to: DRAFT-ohos-libcxx15-missing-cpp20-ranges-algorithms
- caused_by: OHOS libc++15 `_LIBCPP_ENABLE_EXPERIMENTAL` ranges 实现缺陷
- last_updated: 2026-10-04