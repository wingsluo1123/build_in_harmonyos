# yaml 0.2.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载 release tarball: yaml-0.2.5.tar.gz (https://github.com/yaml/libyaml/releases/download/0.2.5/yaml-0.2.5.tar.gz)
2. 补充缺失的 cmake 模板文件 (从上游 git tag 0.2.5):
   - cmake/config.h.in
   - yamlConfig.cmake.in
   - tests/CMakeLists.txt
3. mkdir build && cd build
4. cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ..
5. make -j1
6. make install DESTDIR=$TEST_PREFIX
7. ctest (2 tests passed)
8. ohc-run.py package (生成 yaml-0.2.5-ohos-aarch64.tar.gz)
9. make install (安装到 $DEFAULT_PREFIX)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake configure_file 失败: cmake/config.h.in does not exist | Release tarball 未包含 cmake 模板文件 | 从上游 git tag 0.2.5 下载补充 (ref: E081) |
| 2 | CMake Error: cmake_minimum_required 兼容性 | CMake 4.x 移除了 <3.5 兼容性 | 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 3 | G0 clean-verify 失败 | G0 脚本硬编码 ./configure，不支持 cmake 项目 | 已知限制，手动验证通过 |

## 源码修改

新增 3 个文件 (从上游 0.2.5 tag 获取):
- 0001-cmake-config.h.in.patch (+4 lines)
- 0002-tests-CMakeLists.txt.patch (+27 lines)
- 0003-yamlConfig.cmake.in.patch (+16 lines)

## 依赖版本

无依赖 (yaml 0.2.5 是独立的 YAML 解析库)

## 验证结果

### CTest 单元测试 (ctest --verbose)
```bash
# Test 1: version
sizeof(token) = 80
sizeof(event) = 104
sizeof(parser) = 480
1/2 Test #1: version ..........................   Passed    0.02 sec

# Test 2: reader (UTF-8 序列检测、BOM 检测、长序列解析)
checking utf-8 sequences: 0 fail(s)
checking boms: 0 fail(s)
checking a long utf8 sequence: 0 fail(s)
checking a long utf16 sequence: 0 fail(s)
2/2 Test #2: reader ...........................   Passed    0.38 sec

100% tests passed, 0 tests failed out of 2
Total Test time (real) =   0.41 sec
```

### 链接功能测试 (真实编译链接 libyaml.a)
```bash
# 编写测试程序 yaml_link_test.c，链接 libyaml.a 静态库
clang -fPIC -O2 -I$DEFAULT_PREFIX/include yaml_link_test.c \
      $DEFAULT_PREFIX/lib/libyaml.a -o yaml_link_test

# 运行结果:
libyaml version: 0.2.5
libyaml version numbers: 0.2.5
# 解析 YAML 文档 "---\nname: yaml\ntype: library\nversion: 0.2.5\n..."
# 产生 12 个事件: STREAM_START → DOCUMENT_START → MAPPING_START →
#   SCALAR(name) → SCALAR(yaml) → SCALAR(type) → SCALAR(library) →
#   SCALAR(version) → SCALAR(0.2.5) → MAPPING_END → DOCUMENT_END → STREAM_END
=== Link test PASSED ===
```

### 安装产物验证
```bash
ls $DEFAULT_PREFIX/lib/libyaml.a
# /storage/Users/currentUser/usr/local/lib/libyaml.a (156,136 bytes, ar archive)

file $DEFAULT_PREFIX/lib/libyaml.a
# /storage/Users/currentUser/usr/local/lib/libyaml.a: ar archive
```

详细测试报告见: reports/test-report.md

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| yaml-0.2.5-ohos-aarch64.tar.gz | 225KB | 预编译包 (静态库 libyaml.a + headers) |

## 注意事项

- libyaml 默认构建为静态库 (libyaml.a)，无共享库 (.so)
- 无独立二进制文件 (纯库)
- CMake 4.x 需要 -DCMAKE_POLICY_VERSION_MINIMUM=3.5
- Release tarball 缺少 cmake 模板文件，需要从 git tag 补充
---

**编译结束**: 2026-06-26 14:32
**最终状态**: built
