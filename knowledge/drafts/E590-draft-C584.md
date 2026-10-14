# E590: C++17 结构化绑定不能在 lambda 捕获列表中使用（Clang 15 严格报错）

## 错误特征
- 编译期：`'xml_element' in capture list does not name a variable` 或 `reference to local binding 'x' declared in enclosing function`
- 触发条件：在 `for (const auto & [a, b] : container)` 结构化绑定作用域内写 lambda `[&b](...) { ... }`

## 触发条件
- C++17 标准（CMAKE_CXX_STANDARD 17），Clang 15 严格模式
- scram 0.16.2 的 `src/initializer.cc:628`：`for (const auto & [ tbd_element, xml_element ] : tbd_) { std::visit([this, &xml_element](...), ...) }`

## 根因
C++17 标准不允许 lambda 捕获列表直接引用结构化绑定变量（结构化绑定不是真正的变量，无独立存储；C++20 才放开此限制）。Clang 15 严格按标准报错，GCC 部分版本仅警告或允许。

## 解决方案
在结构化绑定作用域内先声明一个局部引用变量，lambda 捕获该局部引用：

```cpp
for (const auto & [ tbd_element, xml_element ] : tbd_) {
  const xml::Element& xml_element_ref = xml_element;  // 局部引用
  std::visit([this, &xml_element_ref](auto* tbd_construct) { ... }, tbd_element);
}
```

## 验证证据
- 命令：修改 `src/initializer.cc:628` 后重新编译
- 结果：scram 0.16.2 编译成功；上游测试 `scram_tests` 68/68 通过（525 assertions）；conan-verify G0-G4 + L2/L4/L5 全部 PASS
- 补丁：`archives/s/scram/0.16.2/patches/0003-src-initializer.cc.patch`

## 适用边界
- 所有在 Clang 15 + C++17 模式下、于结构化绑定作用域内写 lambda 捕获的 C++ 项目
- 解决方案（局部引用中转）对 C++17/C++20 均有效

## 不适用边界
- C++20 及以上（标准已放开结构化绑定捕获）；编译器非严格模式（GCC 默认可能只警告）
