# keyfinder-cli 1.2.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-10
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: https://github.com/EvanPurkhiser/keyfinder-cli/archive/refs/tags/v1.2.0.tar.gz
2. conan install libkeyfinder/2.2.8 + ffmpeg/7.1.5 获取依赖
3. cmake 配置 (使用 CMakeDeps + PkgConfigDeps)
4. make 编译
5. make install 安装
6. 二进制签名 (OHOS 平台)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 历史补丁不再需要 | 历史补丁为 FFmpeg < 7.x 兼容性修复，源码已有 #if LIBAVFORMAT_VERSION_MAJOR > 60 块支持 FFmpeg 7.x | 使用 ffmpeg/7.1.5，移除历史补丁 |

## 源码修改

无（源码已原生支持 FFmpeg 7.x）

## 依赖版本

- libkeyfinder/2.2.8 (from ohpcd registry, PR #4859)
- ffmpeg/7.1.5 (from ohpcd registry)

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# G0-G4 all PASS
# Test package: keyfinder-cli --help PASS
```

## 注意事项

- 历史补丁(0001-0004)为 FFmpeg < 7.x 兼容性修复，使用 ffmpeg/7.1.5 时不需要
- 源码已有 FFmpeg 7.x 原生支持 (#if LIBAVFORMAT_VERSION_MAJOR > 60)
- 需要先生成并发布 libkeyfinder/2.2.8 到制品仓

## 编译结束
COMPLETED
---

**编译结束**: 2026-08-10 03:10
**最终状态**: published
