# htop 3.4.1 适配笔记

## 编译环境
- 构建系统: autotools (configure)
- 编译日期: 2026-08-06 (Conan 适配)
- 编译器: clang 15.0.4 (LLVM)
- 状态: built（conan 配方已生成，等待 CI 验证）

## 编译步骤
1. 从 GitCode 镜像克隆源码 (GitHub 不可达): gitcode.com/htop-dev/htop
2. 创建 config.h（手动生成，因 automake 不可用）
3. 创建 Makefile.manual（手动 Makefile，因 configure 无法生成）
4. 应用 3 个补丁：config.guess + config.sub + IOPriorityPanel.h
5. 编译：make -f Makefile.manual
6. 验证：htop --version → "htop 3.4.1"

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 不可达 | 网络限制 | 从 GitCode 镜像克隆源码 |
| 2 | automake 不可用 | 系统未安装 | 手动创建 config.h 和 Makefile |
| 3 | VERSION 宏冲突 | 系统 version.h 定义 VERSION | config.h 中 #undef VERSION 后重定义 |
| 4 | COPYRIGHT 未定义 | 缺少 AC_DEFINE | 手动在 config.h 中定义 |
| 5 | sys/utsname.h 未找到 | HAVE_SYS_UTSNAME_H 未定义 | 在 config.h 中添加定义 |
| 6 | IOPriorityPanel.h include 路径错误 | htop 3.4.1 自身 bug | 修改为 #include "../Panel.h" |
| 7 | ncurses 头文件缺失 | cmd-pkgs 包未包含头文件 | 从 ncurses 6.4 源码生成头文件 |
| 8 | ncurses conan 构建失败 | config.guess 不识别 HarmonyOS | CI build_and_test.sh 处理 AR 和 /tmp |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|----------------|
| build-aux/config.guess | 添加 HarmonyOS 系统检测 | ✅ 0001-build-aux-config.guess.patch |
| build-aux/config.sub | 添加 ohos 操作系统支持 | ✅ 0002-build-aux-config.sub.patch |
| linux/IOPriorityPanel.h | `#include "Panel.h"` → `#include "../Panel.h"` | ✅ 0003-linux-IOPriorityPanel.h.patch |

## 依赖版本
- ncursesw (6.4, cmd-pkgs 预编译包)
- clang, make

## 验证结果
- htop --version 通过 ✅
- 二进制为 ELF 64-bit ARM64, 动态链接 musl libc

## Conan 配方
- conanfile.py: package_type=application, requires ncurses/6.4
- conandata.yml: sha256=904f7d4580fc11cffc7e0f06895a4789e0c1c054435752c151e812fead9f6220
- test_package/: 冒烟测试 (htop --version)
- commands.json: 命令行工具声明

## 注意事项
- GitHub 不可达时使用 GitCode 镜像: gitcode.com/htop-dev/htop
- 必须使用 sudo 运行: `sudo -E TERM=xterm-256color TERMINFO=$HOME/usr/local/share/terminfo $HOME/usr/local/bin/htop`
- ncursesw 已静态嵌入，无需运行时 ncurses 库
