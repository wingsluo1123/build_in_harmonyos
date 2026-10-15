# mnxdom

## 简介
mnxdom（MNX Document Object Model）是 [MNX 音乐交换格式](https://w3c.github.io/mnx/)（JSON）的
文档对象模型，用 C++17 实现，要求 C++17 及以上标准。

- 基于 nlohmann_json，每个 MNX 类都是「根 JSON 文档 + json_pointer」的轻量包装，拷贝成本极低
- 提供结构化访问，无需手写字符串键
- 提供两层校验：基于 MNX JSON schema 的结构校验 + 语义校验
- 除 nlohmann 之外没有自己的类序列化层

## OHOS 适配
- CMake 库项目，产出库目标 `mnxdom`，安装头文件到 `include/mnxdom/`，并附带 `lib/pkgconfig/mnxdom.pc`
- 上游 CMakeLists 默认用 `FetchContent` 联网下载 nlohmann_json / json-schema-validator / googletest；
  适配时：nlohmann_json 与 googletest 改用 ohpcd 制品仓预编译包，json-schema-validator 改用随配方
  下发的官方源码（见下方「依赖」），构建期无需联网
- mnxdom 对依赖的 CMake 目标名有白名单判断（`GTest::gtest_main`、`nlohmann_json_schema_validator`），
  需按依赖分别做目标接线，详见版本级 `notes.md`
- MNX JSON schema 以 `mnx-schema.xxd` 内嵌进库，`validation::schemaValidate()` 运行时不读外部文件
- 上游测试套件（GoogleTest，`tests/`）在 `conan create` 的 `build()` 阶段通过 `cmake.test()` 全量运行

## 依赖
- 编译依赖：clang 15 / cmake
- 运行依赖：libc++（静态链接 libmnxdom.a）
- 第三方：`nlohmann_json/3.12.0`（ohpcd 已发布预编译包）
- **内嵌依赖**：`json-schema-validator@40af3ec3`（上游钉住的 commit，官方源码随本配方一起下发并
  静态编译进本包，非制品仓的 2.1.0——2.1.0 在 MNX schema 的根 `$id` 被子 schema 继承时会抛
  `already inserted`，使上游测试全挂；依赖库的适配与发布属于另一个 PR）
- 测试期依赖：`gtest/1.17.0`

## 使用（Conan 消费端）
```python
# conanfile.py
def requirements(self):
    self.requires("mnxdom/3.0.1")
    # mnxdom 的公共头会 #include <nlohmann/json.hpp>，且 CMakeDeps 不会为
    # 「无组件」的依赖自动生成 find_dependency，消费端需显式声明该 header-only 依赖。
    self.requires("nlohmann_json/3.12.0")
```
```cmake
# CMakeLists.txt
find_package(mnxdom CONFIG REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)
target_link_libraries(my_app PRIVATE mnxdom::mnxdom nlohmann_json::nlohmann_json)
```
```cpp
#include <mnxdom/mnxdom.h>

mnx::Document doc;                       // 从零构建，必需子节点自动补全
doc.global().measures().append().set_id("m1");
if (!mnx::validation::schemaValidate(doc)) { /* 处理校验失败 */ }
doc.save("out.json", 4);
```

## 功能验证
```bash
PREFIX=$(conan cache path mnxdom/3.0.1:<package_id>)
ls -la $PREFIX/lib/libmnxdom.a $PREFIX/include/mnxdom/mnxdom.h
# 消费者冒烟测试（test_package 中真实调用 API）
conan test archives/m/mnxdom/3.0.1/test_package mnxdom/3.0.1@ohpcd/stable
```

## 参考
- 源码：https://github.com/mnx-works/mnxdom
- 版本：3.0.1（tag `v3.0.1`，commit 488aa8757ec602c20ff8cf599a2c6857339d8e93）
- 文档：https://rpatters1.github.io/mnxdom/
- 许可证：MIT
