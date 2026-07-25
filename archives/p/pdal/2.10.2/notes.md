# pdal 2.10.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-24
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 使用 `conan create` 构建，CMake 构建系统
2. 在 `generate()` 中设置 `CMAKE_PREFIX_PATH` 指向系统预装依赖（gdal、proj 等）
3. 设置 `CMAKE_CROSSCOMPILING=ON` 绕过 CMake 对 HarmonyOS 平台的识别缺失
4. 使用 `-fuse-ld=bfd -Wl,--allow-shlib-undefined` 链接标志解决 GDAL 传递依赖未解析问题
5. 通过补丁将 dimbuilder 替换为 Python 脚本 `gen_dimension.py` 生成 `Dimension.hpp`
6. 批量禁用测试、backtrace、GCS、补全、lasdump 工具及全部 19 个可选插件

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HarmonyOS SELinux 禁止执行本地编译的 dimbuilder 二进制 | SELinux 安全策略限制 | 用内嵌 Python 脚本 gen_dimension.py 替代 dimbuilder 生成 Dimension.hpp |
| 2 | CMake 无法识别 HarmonyOS 平台 | CMake 无 HarmonyOS 平台配置 | 设置 CMAKE_CROSSCOMPILING=ON 绕过 |
| 3 | musl 动态链接器无法从 Conan 缓存加载共享库 | musl 不搜索 Conan 缓存路径 | 将 .so 文件复制到测试二进制所在目录 |
| 4 | PROJ/GeoTIFF 的 CMake 配置依赖 TIFF::TIFF 目标但未提前查找 | CMake 依赖顺序问题 | 在 include(proj.cmake) 前插入 find_package(TIFF CONFIG) |
| 5 | libgdal.so 有未解析的传递依赖 | GDAL 传递依赖链不完整 | 使用 --allow-shlib-undefined 链接标志 |

## 源码修改

- 0001-find-tiff-before-proj.patch: 在 CMakeLists.txt 中 include(proj.cmake) 之前插入 find_package(TIFF CONFIG)
- 0002-python-dimbuilder.patch: 在 cmake/dimension.cmake 中将 dimbuilder 命令替换为 python3 gen_dimension.py

## 依赖版本

- gdal/3.9.2 (系统预装)
- proj/9.3.1 (系统预装)
- nlohmann-json/3.11.2 (系统预装)
- curl/8.19.0 (系统预装)
- zlib/1.3.1 (系统预装)
- libxml2/2.15.3 (系统预装)
- libtiff/4.6.0 (系统预装)
- libgeotiff/1.7.4 (系统预装)

## 验证结果

```bash
# 主包构建成功
conan create . --build=missing -pr:h=profiles/ohos-aarch64 -pr:b=profiles/default

# 测试包构建
cd test_package && conan test . pdal/2.10.2
# test_pdal 二进制编译链接成功，验证 PointTable 和 StageFactory API 可用
```

## 注意事项

- 依赖通过 cmd-pkgs 系统预装，非 Conan requires 声明
- musl 动态链接器限制要求 .so 文件与测试二进制同目录
- Dimension.hpp 由 Python 脚本在 cmake build 阶段自动生成，无需手动预生成
---

**编译结束**: 2026-07-24 14:38
**最终状态**: built
