# snappy — OpenHarmony 编译记录

## 基本信息
- 软件: snappy
- 描述: Google Snappy — a fast compression/decompression library
- 主页: https://google.github.io/snappy/
- 许可证: BSD-3-Clause
- 目标: ohos-aarch64

## 版本

### 1.2.1 (Conan recipe)
- 构建系统: CMake
- 源码: https://codeload.github.com/google/snappy/tar.gz/refs/tags/release-1.2.1
- 默认静态库 (shared=False, fPIC=True)
- 作为 avro-c 1.12.0 的 Conan 依赖项
- 测试: test_package 包含压缩/解压往返测试

### 1.2.2 (autotools build)
- 构建系统: autotools
- 源码: https://codeload.github.com/google/snappy/tar.gz/refs/tags/1.2.2

## 编译指导
<!-- 编译注意事项 -->

## 补丁清单
<!-- patches/ 目录中的补丁说明 -->

## 已知限制
<!-- 平台相关限制 -->

## 功能验证
<!-- 验证命令和结果 -->
