# E430 — CMakeDeps 下 FindOpenSSL/FindZLIB 模块变量为空，须按 imported target 分支

## 错误特征

```
fatal error: 'openssl/bio.h' file not found          # OPENSSL_INCLUDE_DIR 为空
CMake Error: Target "ZLIB::ZLIB" of type UTILITY may not be linked into another target
```

上游 CMake 用 `find_package(OpenSSL)` + `${OPENSSL_LIBRARIES}` /
`${OPENSSL_INCLUDE_DIR}`、`find_package(ZLIB)` + `ZLIB::ZLIB` 接线，在 conan
CMakeDeps 环境下编译/配置失败。

## 触发条件

- 构建系统: cmake（上游 Find 模块变量风格）
- 阶段: configuration / compilation
- 制品仓包以 imported target 暴露依赖（openssl::openssl、zlib::zlib）

## 根因分析

conan 2 的 CMakeDeps 不执行 CMake 内置 Find 模块的搜索逻辑：
`OPENSSL_LIBRARIES/OPENSSL_INCLUDE_DIR` 为空串；zlib 的导出目标名是
`zlib::zlib`（不是 `ZLIB::ZLIB`）。另外，把 openssl 改成 `PRIVATE` 链接后，
**公共头**（IXSocketOpenSSL.h 内含 `<openssl/*.h>`）的消费者会拿不到 include
路径——PRIVATE 不传播接口头。

## 解决方案

### 推荐方案

上游 CMake 加 imported-target 分支（保留 else 原路径，兼顾非 conan 构建）：

```cmake
if (TARGET openssl::openssl)
  target_link_libraries(ixwebsocket PRIVATE openssl::openssl)
  # 公共头引用 <openssl/*.h>：PRIVATE 链接也要在构建接口里传播头目录
  target_include_directories(ixwebsocket PUBLIC
    $<BUILD_INTERFACE:$<TARGET_PROPERTY:openssl::openssl,INTERFACE_INCLUDE_DIRECTORIES>>)
else()
  add_definitions(${OPENSSL_DEFINITIONS})
  target_include_directories(ixwebsocket PUBLIC $<BUILD_INTERFACE:${OPENSSL_INCLUDE_DIR}>)
  target_link_libraries(ixwebsocket PRIVATE ${OPENSSL_LIBRARIES})
endif()
```

zlib：`ZLIB::ZLIB` → `zlib::zlib`（若需兼容两种环境，同样用 `if (TARGET ...)` 分支）。

### 禁止做法

- ❌ 假设 CMakeDeps 会填充模块变量（它不会跑 Find 模块）
- ❌ 对被公共头引用的依赖只做 PRIVATE 链接而不补 BUILD_INTERFACE 头传播

## 验证

```bash
conan create archives/w/ws/11.4.6 -pr:h ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

ws 11.4.6 适配实录：打补丁后 14 个上游测试全部编译通过，13/14 运行通过。

## 关联条目

- 相关: E429（skip_shared_packages 传递依赖为空）
