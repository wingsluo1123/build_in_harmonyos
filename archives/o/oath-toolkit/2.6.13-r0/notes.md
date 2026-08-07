# oath-toolkit 2.6.13-r0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# 环境设置
export CONFIG_SHELL=/data/service/hnp/bin/bash
export SHELL=/data/service/hnp/bin/bash
export PKG_CONFIG_PATH=<libxml2-pkgconfig>:<pam-pkgconfig>
export CPPFLAGS="-I<pam-include>"
export LDFLAGS="-L<pam-lib> -L<libxml2-lib>"

# 配置、编译、安装
./configure --prefix=$DEFAULT_PREFIX --enable-pam --enable-pskc
make -j1
make install DESTDIR=$TEST_PREFIX
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 不识别 OHOS 平台 | 上游 autotools 版本旧 | 补丁 0001-0009: 添加 OHOS 平台检测 |
| 2 | umask 在 usersfile.c 中未掩码 | `~(S_IRUSR\|S_IWUSR)` 可能产生非零高位 | 补丁 0005: 改为 `& 0777` |
| 3 | configure config.status 失败 "Permission denied" | HarmonyOS SGID 目录 + umask 077 导致 mktemp 创建的目录权限异常 | 补丁 0010-0013: 将 umask 077 改为 022 |
| 4 | liboath gnulib 测试使用 /tmp | /tmp 在 HarmonyOS 上只读 | 补丁 0011: 将 /tmp 替换为 ${TMPDIR:-/tmp} |
| 5 | lld 链接器因 LD_LIBRARY_PATH 中的 conan libxml2 崩溃 | lld 依赖系统 libxml2.so.16，conan 版本 ABI 不兼容 | 编译时不将 conan libxml2 加入 LD_LIBRARY_PATH |
| 6 | configure 无法找到 PAM 头文件 | security/pam_appl.h 在 conan 包中 | 设置 CPPFLAGS 包含 PAM include 路径 |

## 源码修改

13 个补丁：
- 0001-0009: config.guess/config.sub OHOS 平台检测 + usersfile.c umask 修复
- 0010-0013: configure 脚本 umask 077→022 + /tmp→$TMPDIR 修复

## 依赖版本

- libxml2/2.15.3.1 (Conan 制品仓)
- linux-pam/1.7.2 (Conan 制品仓)

## 验证结果

```bash
make check
# All tests passed: liboath, libpskc, oathtool, pskctool, pam_oath
```

## 注意事项

1. **CONFIG_SHELL 必须设置为 bash**: HarmonyOS 默认 /bin/sh 不支持 config.status 中的某些操作
2. **不要将 conan libxml2 加入 LD_LIBRARY_PATH**: lld 链接器依赖系统 libxml2，ABI 不兼容
3. **umask 077 会导致 mktemp 目录创建失败**: HarmonyOS 文件系统 SGID 位继承导致权限异常
---

**编译结束**: 2026-08-07 08:13
**最终状态**: built
