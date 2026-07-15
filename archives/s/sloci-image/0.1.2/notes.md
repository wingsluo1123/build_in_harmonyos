# sloci-image 0.1.2 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang/clang++（未使用，纯 shell 脚本）
- 状态: built

## 软件描述

sloci-image 是一个简单的 POSIX shell 脚本工具，用于创建单层 OCI 容器镜像。
它符合 OCI Image Format 1.0.1 规范，只需要 POSIX sh 和常见 Unix 工具
（awk, date, gzip, sed, sha256sum, tar）。

## 编译步骤

sloci-image 是纯 shell 脚本，无需编译。安装命令:

```bash
cd ~/tmp/builds/sloci-image-0.1.2.work
make install DESTDIR=$HOME/tmp/test-install-sloci-image-0.1.2 PREFIX=$HOME/usr/local
```

安装后验证脚本在 `$TEST_PREFIX$DEFAULT_PREFIX/bin/sloci-image` 中。

```bash
# 验证脚本可执行
sloci-image --version
# 输出: sloci-image 0.1.2

sloci-image --help
# 输出: Usage: sloci-image [options] ROOTFS NAME[:TAG] ...
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | HarmonyOS 环境到 GitHub 网络延迟 | 使用 curl --max-time 120 下载成功 |
| 2 | 模板生成 Autotools 配方 | conan-init 默认使用 autotools 模板 | 手动改为 makefile 配方，使用 make install |

## 源码修改

无源码修改。sloci-image 是纯 shell 脚本，在 HarmonyOS 环境下直接可用。

## 依赖版本

- 无编译依赖（shell 脚本工具）
- 运行依赖：POSIX sh, awk, date, gzip, sed, sha256sum, tar

## 验证结果

```bash
file ~/tmp/test-install-sloci-image-0.1.2/storage/Users/currentUser/usr/local/bin/sloci-image
# 输出: /bin/sh script

sloci-image --version
# 输出: sloci-image 0.1.2
```

## 交付物

| 文件 | 说明 |
|------|------|
| sloci-image | POSIX shell 脚本 (11KB) |

## 注意事项

- sloci-image 是 CLI 工具（非库），已创建 commands.json (R38)
- conanfile.py package_type 设为 "application"
- 无编译步骤，build() 仅 apply_conandata_patches，package() 使用 copy() 将脚本安装到 bin 目录并 chmod 755
- test_package 验证脚本可执行且能显示版本
---

**编译结束**: 2026-07-15 20:10
**最终状态**: built
