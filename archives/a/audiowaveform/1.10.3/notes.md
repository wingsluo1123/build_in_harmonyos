# audiowaveform 1.10.3 适配笔记

## 编译环境
- 构建系统: CMake (Conan CMakeDeps + CMakeToolchain)
- 编译日期: 2026-08-05
- 编译器: clang 15.0.4 (OHOS aarch64)
- 状态: built (conan package created)

## 编译步骤

```bash
conan create archives/a/audiowaveform/1.10.3/conanfile.py \
    -pr:h=ohos-aarch64-override -pr:b=default --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺失依赖 libmad, libid3tag, libgd, libsndfile | 制品仓无这些包 | 先适配并构建这4个依赖包到本地conan缓存 |
| 2 | boost/format.hpp not found | boost 1.91.0 ohpcd 包仅含5个指定库的headers | 从boost源码tarball提取format headers复制到boost包 |
| 3 | ZLIB::ZLIB target not found in libid3tag | zlib版本覆盖(1.3.1→1.3.1.1)导致CMakeDeps target名变化 | 移除libid3tag conanfile中的ZLIB::ZLIB→zlib::zlib替换 |
| 4 | libogg版本冲突 | libvorbis需1.3.6, flac需1.3.5, libsndfile需1.3.6.1 | [replace_requires] override profile |
| 5 | zlib版本冲突 | libgd需1.3.1.1, libid3tag需1.3.1 | [replace_requires] override profile |
| 6 | CMake 4.x不兼容cmake_minimum_required(2.8.7) | CMake 4.x移除了<3.5兼容 | CMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 7 | googletest submodule不可用 | 源码tarball不包含submodule | ENABLE_TESTS=0禁用测试 |
| 8 | custom FindXXX.cmake找不到conan管理的依赖 | find_path/find_library不搜索conan包目录 | 设置cache variables (LIBGD_INCLUDE_DIRS等) |

## 依赖版本

- libmad/0.16.4 (Tenacity Team fork, CMake)
- libid3tag/0.16.3
- libgd/2.3.3 (deps: libpng/1.6.58, libjpeg/10, freetype/2.14.3, zlib/1.3.1.1)
- libsndfile/1.2.2 (deps: libogg/1.3.6.1, libvorbis/1.3.7, flac/1.4.3, opus/1.5.2.1)
- boost/1.91.0

## 源码修改

- patches/0001-CMakeLists.txt.patch: 为静态libgd添加传递依赖链接

## 验证结果

```
audiowaveform -i test_tone.wav -o test_waveform.json  # 生成JSON波形数据
audiowaveform -i test_tone.wav -o test_waveform.png   # 生成PNG波形图
PASS: JSON output generated
PASS: PNG output generated
=== All tests passed ===
```

## 注意事项

- audiowaveform是命令行工具(非库), 需要commands.json
- 4个依赖(libmad, libid3tag, libgd, libsndfile)尚未发布到制品仓, 需先提交并合并其PR
- boost包缺少format headers, 需创建boost/1.91.0.1包含format库
---

**编译结束**: 2026-08-05 23:24
**最终状态**: built
