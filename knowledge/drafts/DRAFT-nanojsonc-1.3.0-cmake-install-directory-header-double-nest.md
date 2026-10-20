# DRAFT-nanojsonc-1.3.0-cmake-install-directory-header-double-nest

> 与 `DRAFT-nanojsonc-1.3.0-cmake-install-directory-header-double-nest.kv` 成对（同 stem）
> 状态: draft | 来源: nanojsonc 1.3.0 适配 (2026-10-19, pc3-2)

## 问题

上游 CMake 工程用 `install(DIRECTORY ${CMAKE_SOURCE_DIR}/include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/${PROJECT_NAME})` 安装公共头。当源码树 `include/` 下本身已带 `<lib>/` 子目录（如 `include/nanojsonc/parser.h`）时，DIRECTORY 安装会把整个 `include/` 内容装进 `include/<lib>/`，落盘为 **`include/nanojsonc/nanojsonc/parser.h`（双嵌套）**。同一工程的 `target_include_directories` 的 `INSTALL_INTERFACE=${CMAKE_INSTALL_INCLUDEDIR}` 与 `install(EXPORT)` 的 `INCLUDES DESTINATION include` 都指向 `include/` 根，二者不一致。Conan 打包后消费者 `#include <nanojsonc/parser.h>` 在 test_package / 下游编译必失败。

## 根因

- `install(DIRECTORY)` 与 `install(FILES)` 语义不同：DIRECTORY 复制的是目录**内容**（含子目录结构），目标 DESTINATION 再拼上 `${PROJECT_NAME}` 就把已存在的 `<lib>/` 子目录再套一层。
- 安装目标与导出的接口目录（`INSTALL_INTERFACE` / `INCLUDES DESTINATION`）未对齐，错误在消费者阶段才暴露（`conan create` 装库本身不报错）。

## 方案

最小 source patch：把 `install(DIRECTORY .../include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/${PROJECT_NAME})` 的 DESTINATION 改为 `${CMAKE_INSTALL_INCLUDEDIR}`（`include/` 根），使 `include/<lib>/xxx.h` 正确落在 `include/` 根下，与 `INSTALL_INTERFACE` 对齐；保留上游的 `<lib>/` 目录命名。配方 `package()` 继续用 `cmake.install()`，不做手工 copy。

```diff
-# Install Headers
-install(DIRECTORY ${CMAKE_SOURCE_DIR}/include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/${PROJECT_NAME})
+# Install Headers
+install(DIRECTORY ${CMAKE_SOURCE_DIR}/include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
```

（nanojsonc 1.3.0 实证补丁：`patches/0001-CMakeLists.txt.patch`）

## 验证

1. `grep -n 'install(DIRECTORY' CMakeLists.txt` 确认上游安装方式；
2. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing` 后检查 package folder：`find <pkg>/include -name 'parser.h'` 应落在 `include/<lib>/` 而非 `include/<lib>/<lib>/`；
3. test_package 消费者 `#include <nanojsonc/parser.h>` 编译、链接、运行退出码 0（nanojsonc 实测 e2e events=8 matched=6 errors=0，exit 0）；
4. 修复前负向观测：头文件落在 `include/nanojsonc/nanojsonc/` 时消费者 `#include <nanojsonc/parser.h>` 编译失败。

## 适用边界

- 源码树 `include/` 下已带 `<lib>/` 子目录、且上游用 `install(DIRECTORY .../include/ DESTINATION include/${PROJECT_NAME})` 的 CMake C/C++ 库。
- 不适用于：`install(FILES ... DESTINATION include/<subdir>)` 单层子目录场景（见 E217，改 recipe includedirs 对齐）；recipe `package()` 内 `copy()` pattern 保留目录导致的 `include/include/`（见 E1759，recipe 侧修复）。

## 反例与限制

- 若上游**有意**把公共头装到 `include/<lib>/` 且源码 `include/` 下**没有** `<lib>/` 子目录（纯 `parser.h` 平铺），`install(DIRECTORY include/ DESTINATION include/<lib>)` 是正确写法，不应套用本修复。
- 若上游同时使用 `configure_file` 生成头，需一并核对生成头是否随 `install(FILES)` 安装（参考 E1141/E1137 安装闭包教训）。
- 本条目只修安装目标；不改 `package_info().includedirs` 迁就错误布局（`forbid_1`），也不手工 copy 头文件（`forbid_2`）。

## 查重差异

- **E217**：`install(FILES ${c_headers} DESTINATION include/${PROJECT_NAME})` 单层子目录 + 配方 `includedirs` 对齐修复——本条目为 `install(DIRECTORY)` 双嵌套 + source patch 修安装目标，错误签名、根因、修复点均不同。
- **E1759**：recipe `package()` 内 `conan.tools.files.copy()` 保留 pattern 目录导致 `include/include/`——本条目为**上游 CMake install 目标**问题，非 recipe 编写语义。
- 快照扫描（`knowledge/graph/E*.kv` + `knowledge/doc/E*.md` + `knowledge/drafts/*.{md,kv}` + 根目录 `DRAFT-*`）：无等价条目，判定 `new_draft`（路径 B）。
