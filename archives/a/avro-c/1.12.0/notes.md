# avro-c 1.12.0 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-08-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤
1. 使用 Apache 官方 C 专用 tarball (avro-c-1.12.0.tar.gz)
2. 应用 2 个补丁
3. 安装依赖: jansson/2.15.1 + zlib/1.3.1 + snappy/1.1.10 + xz/5.6.2 (liblzma)
4. `cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXE_LINKER_FLAGS=-lc++`
5. `make -j$(nproc)`
6. `make install`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bash 路径不标准 | OpenHarmony bash 在 /data/service/hnp/bin/bash | 补丁改为 #!/usr/bin/env bash |
| 2 | CMake SOVERSION 为空 | HarmonyOS 下 CMake 无法正确获取 | 补丁设置默认 SOVERSION |
| 3 | snappy 链接失败 | snappy 是 C++ 库 | 添加 CMAKE_EXE_LINKER_FLAGS=-lc++ |
| 4 | 共享库构建问题 | 默认构建共享库但 Conan 默认静态 | 补丁条件化共享库构建 (BUILD_SHARED_LIBS) |
| 5 | Conan 依赖查找 | CMake 使用 pkg_check_modules | 添加 CMakeDeps + PkgConfigDeps 生成器 |

## 源码修改
- `src/CMakeLists.txt` — SOVERSION 空值处理 + 共享库条件构建 (0001-src-CMakeLists.txt.patch)
- `version.sh` — bash 路径修复 (0002-version.sh.patch)

## 验证结果
- conan-verify: G0-G4 + L2/L4/L5 全部 PASS
- test_package: avro-c API schema 解析 + record 创建 + 字段读写验证通过
- 所有 Codec 已启用: deflate (zlib), snappy, lzma (xz/liblzma)

## 依赖说明
- jansson/2.15.1: JSON 库 (必需)
- zlib/1.3.1: deflate 压缩 codec
- snappy/1.1.10: snappy 压缩 codec (来自 conancenter)
- xz/5.6.2: liblzma 压缩 codec
