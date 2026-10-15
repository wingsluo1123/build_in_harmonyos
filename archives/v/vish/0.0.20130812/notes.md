# vish 0.0.20130812 适配笔记

## 编译环境
- 构建系统: manual（真机池无 autoconf 套件，CXX 直接编译 vish.cpp + 静态链接 librevisa 包；等价于 configure 的 AC_CHECK_LIB/AC_CHECK_HEADER 选择）
- 编译日期: 2026-10-13
- 编译器: clang/clang++
- 状态: built (待真机 rule4 门禁验证)

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | vish |
| 版本 | 0.0.20130812 |
| 上游 | http://www.librevisa.org/ (Simon Richter, GPL-3.0-or-later) |
| 描述 | VISA 命令行 shell，仪器读写工具 |
| 产物 | bin/vish (静态链接，自包含) |

## 编译步骤

真机池无 autoconf 套件（librevisa 笔记已实证：`autoreconf` 不存在，
Conan `autoconf` 会拉起 m4 源码构建并失败），且 vish 归档的生成式
configure 无 config.guess/config.sub（无法规范化 --host），故不运行
autotools，直接以 CXX 编译：

```bash
# 依赖 librevisa/0.0.20130812（ohpcd 制品仓已 built，提供 visa.h + libvisa.a）
c++ $CXXFLAGS -O2 -I<librevisa>/include \
    -D'PACKAGE="vish"' -D'VERSION="0.0.20130812"' \
    vish.cpp <librevisa>/lib/libvisa.a $LDFLAGS -pthread -o vish
```

Conan 流程见 `conanfile.py`：直接编译链接，`package()` 安装 bin/vish，
`package_info()` 声明 bindirs（R38 CLI）。profile CFLAGS/CXXFLAGS/LDFLAGS
经 conanbuild 环境展开，交叉标志（--target/--sysroot）不丢失。

## 上游测试清点 (R51)

- 来源目录: 无 tests/ 目录（源码仅 11 个顶层文件）
- 注册总数: 0（Makefile.am 仅 bin_PROGRAMS=vish + dist_man_MANS=vish.1，
  无 check_PROGRAMS/TESTS target；configure.ac 无 AM_TESTS）
- 测试框架: 无
- 口径: `upstream_test_count_method = none`
- 硬件需求: 无上游测试；鸿蒙特有 test_package 2 断言均无硬件依赖

## 鸿蒙特有测试（test_package）

| # | 命令 | 断言 | 说明 |
|---|------|------|------|
| 1 | `vish --version` | 退出码 0 且输出含 "0.0.20130812" | 真实链接可执行文件 + PACKAGE/VERSION 宏 |
| 2 | `vish --scan` | 退出码 0 | 真实 VISA 路径 viOpenDefaultRM→viFindRsrc→viClose，librevisa 可移植核心无硬件也返回 SUCCESS（0 设备） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方源 librevisa.org/download/ 404 | 上游官网已失效（2026-10-13 实测） | 改用 Debian pool 官方 orig 权威镜像（vish_0.0.20130812.orig.tar.gz，非 dfsg 上游原版，sha256 本地实测 1c121057...db7ac0）；PF7/R39 例外在 PR 说明登记 |
| 2 | 生成式 configure 无 config.guess/config.sub | 上游 tarball 未携带 | 不运行 autotools，直接 CXX 编译（真机池亦无 autoconf 套件） |
| 3 | 直接编译无 config.h，--version 分支编译失败 | vish.cpp 第 21 行 `PACKAGE " " VERSION` | 编译命令注入 -D'PACKAGE="vish"' -D'VERSION="0.0.20130812"'（等价 autotools 生成的 config.h 定义） |
| 4 | vish.cpp 用 std::string/getline 未 include <string> | 上游依赖传递包含 | libc++ 经 <iostream> 传递包含，实测无需补丁 |

## 依赖版本

| 软件 | 版本 | 来源 |
|------|------|------|
| librevisa | 0.0.20130812 | ohpcd 制品仓（本仓库已 built，2026-09-26） |

## 验证结果

```bash
# conan create 本地验证（profile: ohos-aarch64-local）
conan create . --build=missing
# 产物
bin/vish  # 静态链接 libvisa.a，自包含

# test_package 2 断言
vish --version   # 退出 0，输出 "vish 0.0.20130812"
vish --scan      # 退出 0，输出 "I: 0 devices found."
```

## 注意事项

- vish.cpp 栈上 `ViChar buffer[256000]`（256KB）为运行期堆栈占用，非编译问题
- 依赖 librevisa 的静态库（libvisa.a），vish 可执行文件自包含，不依赖运行期共享库
- test_package 以探测到的 POSIX shell 包裹执行（OHOS mksh 不能直跑 ELF，zlib/libuio 前例）
---

**编译结束**: 2026-10-13 15:01
**最终状态**: built
