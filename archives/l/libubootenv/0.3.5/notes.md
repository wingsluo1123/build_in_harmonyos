# libubootenv 0.3.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-18
- 编译器: clang/clang++ (target aarch64-linux-ohos)
- 状态: built

## 编译步骤

1. **源码获取**: conan source() 从 GitHub 下载 v0.3.5 tarball (sha256: dc27ddcb...)
2. **CMake 修复** (build() inline replace_in_file):
   - `cmake_minimum_required(VERSION 2.6)` → `VERSION 3.5` (CMake 4.x 兼容)
   - 显式设置 SONAME: `target_link_options(ubootenv PRIVATE "LINKER:-soname,libubootenv.so")`
   - 注入 Conan 依赖路径: `include_directories(zlib_inc yaml_inc)` + `target_link_libraries(ubootenv <zlib_full_path> <yaml_full_path>)`
   - OHOS SDK bug: `<mtd/ubi-user.h>` → `#if !defined(__OHOS__)` 跳过，提供 UBI 桩结构
3. **构建**: `cmake.configure()` + `cmake.build()` → 产出 libubootenv.so + fw_printenv/fw_setenv CLI
4. **打包**: `cmake.install()` + copy LICENSES/* → package/licenses/
5. **test_package**: 消费者 API 测试 (version_info, init_exit, env_set_get, iterator) + 鸿蒙 dlopen 运行时测试

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake_minimum_required(VERSION 2.6)` 与 CMake 4.x 不兼容 | CMake 4.x 移除了 < 3.5 的兼容性 | replace_in_file 改为 VERSION 3.5 |
| 2 | `yaml.h not found` | Conan 不提供 libyaml 的 CMake 配置文件，FindPackage 失败 | build() 阶段获取 cpp_info 路径，注入 include_directories |
| 3 | `Could NOT find ZLIB` | Conan 不提供 ZLIBConfig.cmake | 改为 include_directories + 完整路径链接 |
| 4 | `<mtd/ubi-user.h>` `__packed` 重定义 (6 errors) | OHOS SDK 头文件 bug | __OHOS__ 宏跳过 include，提供 ubi_attach_req/ubi_mkvol_req 桩 |
| 5 | SONAME 不匹配 (libubootenv.so.0 vs libubootenv.so) | CMake 在 OHOS 平台忽略 VERSION/SOVERSION 属性 | 显式 target_link_options(LINKER:-soname,libubootenv.so) |
| 6 | `Error loading libubootenv.so` (test_package) | cmake.test() 不设置 LD_LIBRARY_PATH | self.run() 显式传入 LD_LIBRARY_PATH |

## 源码修改

无独立补丁文件 — 所有修改通过 conanfile.py build() 中 inline replace_in_file 实现：
- CMakeLists.txt: cmake_minimum_required 2.6 → 3.5
- src/CMakeLists.txt: cmake_minimum_required 升级 + SONAME 注入 + Conan 依赖路径注入
- src/uboot_env.c: OHOS 宏跳过 `<mtd/ubi-user.h>`

## 依赖版本

- zlib/1.3.1
- libyaml/0.2.5

## 交付物

| 文件 | 说明 |
|------|------|
| libubootenv.so | U-Boot 环境访问共享库 (SONAME: libubootenv.so) |
| fw_printenv | 打印 U-Boot 环境变量 CLI |
| fw_setenv | 设置 U-Boot 环境变量 CLI |

## 验证结果

```
conan create: ALL TESTS PASSED (shared=False)
test_package:
  - test_ubootenv: 4/4 PASSED (version_info, init_exit, env_set_get, iterator)
  - test_dlopen: OK (dlopen 加载 + 5 个关键符号解析)
conan-verify: G1 PASS (export_sources + apply_conandata_patches 完整)
```

**编译结束**: 2026-10-18
**最终状态**: built
---

**编译结束**: 2026-10-18 02:46
**最终状态**: built
