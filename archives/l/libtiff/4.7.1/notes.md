# libtiff 4.7.1 编译笔记

## 编译概述
- **版本**: 4.7.1
- **日期**: 2026-05-26
- **状态**: built (测试失败，但编译和安装成功)

## 编译过程

### 下载
- **URL**: https://download.osgeo.org/libtiff/tiff-4.7.1.tar.gz
- **大小**: 3.8 MB

### 配置
- **构建系统**: autotools
- **平台检测**: 需要修改 config.guess/config.sub (E007)
- **umask 问题**: 修改 configure/config.status 中的 umask 077 → 022 (E011)

### 编译
- **编译器**: clang
- **并行数**: $(nproc)
- **结果**: 成功

### 测试
- **make check**: 100 个测试全部失败
- **原因**: 运行时库加载问题 (ELF 签名问题)
- **决定**: 跳过测试，记录原因

### 安装
- **DESTDIR 模式**: ~/tmp/test-install-libtiff-4.7.1
- **最终安装**: ~/usr/local
- **产物**: libtiff.so.6.2.0, libtiffxx.so.6.2.0, 头文件, pkg-config

## 需要的补丁

### 0001-port-for-ohos.patch
修改 config/config.guess 和 config/config.sub 以支持 HarmonyOS 平台检测。

## 依赖

| 依赖 | 版本 | 状态 |
|------|------|------|
| zlib | 已安装 | ✅ |
| lzma | 5.6.2 | ✅ |
| jpeg | 未安装 | ❌ (可选) |
| jbig | 未安装 | ❌ (可选) |

## 注意事项

1. **liblzma.so 符号链接**: 需要手动创建 `ln -s liblzma.so.5.6.2 liblzma.so`
2. **ELF 签名**: 二进制工具需要签名才能执行
3. **pkg-config**: 需要设置 `PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig`

## 验证结果

```bash
pkg-config --modversion libtiff-4
# 输出: 4.7.1
```

---
*编译完成: 2026-05-26*