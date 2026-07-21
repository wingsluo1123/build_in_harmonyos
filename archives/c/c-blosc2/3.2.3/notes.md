# c-blosc2 3.2.3 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-07-16
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 源码获取：从 GitCode 镜像浅克隆 v3.2.3 tag
2. CMake 配置（参考 homebrew formula 的构建选项）：
   ```
   cmake -S . -B build \
     -DBUILD_TESTS=OFF \
     -DBUILD_FUZZERS=OFF \
     -DBUILD_BENCHMARKS=OFF \
     -DBUILD_EXAMPLES=OFF \
     -DBUILD_PLUGINS=OFF \
     -DPREFER_EXTERNAL_LZ4=ON \
     -DPREFER_EXTERNAL_ZLIB=ON \
     -DPREFER_EXTERNAL_ZSTD=ON \
     -DCMAKE_SYSTEM_PROCESSOR=aarch64
   ```
3. 编译：`cmake --build build`
4. 安装：`cmake --install build`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS aarch64 交叉编译需指定处理器架构 | CMake 默认检测宿主机架构 | 在 generate() 中设置 CMAKE_SYSTEM_PROCESSOR=aarch64 |
| 2 | CI 无法下载 GitHub 源码归档 | Worker 网络受限，无法直连 github.com | 从 GitCode 镜像浅克隆 v3.2.3 tag |

## 依赖版本

| 依赖 | 版本 | 制品仓状态 |
|------|------|-----------|
| lz4 | 1.10.0 | ✅ 已发布 |
| zstd | 1.5.7 | ✅ 已发布 |
| zlib-ng-compat | 2.3.3 | ✅ 已发布 |

## 验证结果

```bash
# test_package 通过：输出 "Successful roundtrip!"
# 压缩/解压缩往返测试验证通过
```

## 注意事项

- c-blosc2 是 blosc 压缩库的第二代，与旧版 blosc/c-blosc 1.x 并存
- 使用外部依赖（lz4、zstd、zlib-ng-compat），不使用内置编解码器
- 静态链接模式（default_options: shared=False）
