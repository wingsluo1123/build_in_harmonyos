# DRAFT-xeus-5.0：test_package 消费者须显式持有公开头依赖，并兼容被测包双 CMake 目标名

> Contributor: pc3-5 | Status: Draft | Updated: 2026-10-09
> Source: xeus 5.0.0 适配任务（OHOS aarch64，task xeus-5.0.0-r01-pc3-5-20261009T094604Z）
> 关联先例: E216（CMakeDeps 组件 include 传播失效）

## 背景

xeus 5.0.0 `conan create` 的 test_package 阶段编译失败：

```text
test_consumer.cpp:7:10: fatal error: 'nlohmann/json.hpp' file not found
  # include "nlohmann/json.hpp"
```

同时 `find_package(xeus)` 暴露的目标既有 `xeus::xeus`（conan CMakeDeps 命名空间目标）
也有 `xeus`/`xeus-static`（上游 xeusConfig 安装导出，见 xeusConfig.cmake.in），
test_package 链接目标二选一会导致另一边失败。

## 错误特征

- conan create 主体构建成功，test_package 编译期报公开头依赖缺失；
- "no target" 类错误随 find_package 目标名（命名空间 vs 无命名空间）切换而互换。

## 根因

1. 被测库公开头直接 include 第三方头（xeus 的 xjson.hpp/xhelper.hpp 均 include
   `<nlohmann/json.hpp>`）；CMakeDeps 对"被测试包"只注入其自身 include，头部依赖
   的 include 目录需由 test_package 显式 requires 才能注入编译命令行。
2. 上游 CMake 安装导出的是无命名空间目标（`xeus` / `xeus-static`），而 conan CMakeDeps
   生成命名空间目标（`xeus::xeus`）——consumer 必须按环境选择正确目标名。

## 修复

```python
# test_package/conanfile.py
def requirements(self):
    self.requires(self.tested_reference_str)
    self.requires("nlohmann_json/3.12.0")   # 公开头 include 的依赖，显式持有
    self.requires("uuid/2.40.1")
```

```cmake
# test_package/CMakeLists.txt —— 目标名兼容选择
if (TARGET xeus::xeus)
    set(XEUS_LINK_TARGET xeus::xeus)
elseif (TARGET xeus)
    set(XEUS_LINK_TARGET xeus)
elseif (TARGET xeus-static)
    set(XEUS_LINK_TARGET xeus-static)
endif ()
target_link_libraries(test_xeus PRIVATE ${XEUS_LINK_TARGET})
```

## 验证

- 修复前: conan create test_package 编译失败（nlohmann/json.hpp not found）；
- 修复后: `conan create archives/x/xeus/5.0.0 -pr=default -tf test_package` exit 0，
  100% tests passed（2/2：消费者 + 鸿蒙专项）；
- 上游 51 用例 51/51 通过（独立于本草案）。

## 适用边界

- 适用: 公开头含第三方 include 的库；CMake 导出无命名空间目标的库；
- 反例: header-only 且公开头无第三方 include 的库不触发；
- 与 E216 区分: E216 是依赖组件 INTERFACE include 失效需 GLOB 兜底；本条是
  test_package 显式 requires + 目标名兼容，互为补充。

## 查重差异

- 正式条目 E216/E221: 同 CMakeDeps 域但机制不同（组件传播 vs 显式 requires/目标名）→ 新增差异成立；
- 草稿 DRAFT-13532-getdns（prefer-config vs find-module）: 不同场景；
- 无同名草稿 → 建本 DRAFT。