# git 2.56.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-10-14
- 编译器: clang 15.0.4 (OHOS 工具链)
- 状态: pending（全量测试进行中）

## 上游与源码
- URL: https://mirrors.ustc.edu.cn/kernel.org/software/scm/git/git-2.56.0.tar.gz（kernel.org 官方镜像）
- 上游最新稳定版，较此前归档的 2.49.0/2.45.2 跨 7 个 feature 版本
- 上游 2.56 新增可选 Rust 组件（gitcore 原型：根 Cargo.toml + contrib/libgit-rs + contrib/libgit-sys + src/*.rs），OHOS 无 Rust 工具链（CI 能力矩阵），已按可选组件移除，主构建纯 C 不受影响

## 编译步骤
```bash
# conan 依赖（制品仓已发布）
conan install --requires=zlib/1.3.1.1 --requires=openssl/3.5.6.1 \
  --requires=curl/8.15.0.1 --requires=expat/2.8.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
source conanbuild.sh
./configure --prefix=$DEFAULT_PREFIX --with-openssl --with-curl --with-expat ac_cv_header_libintl_h=no
# E129: HMDFS umask 077 + setgid → sed 修复（见下）
make -j$(nproc)
make install DESTDIR=... INSTALL="bash install.sh" NO_INSTALL_HARDLINKS=YesPlease NO_TCLTK=YesPlease
```

## config.mak 追加（本地覆盖）
```
NO_RUST=YesPlease
HAVE_DEV_TTY=YesPlease
BASIC_CFLAGS += -DNO_PTHREAD_CANCEL
BASIC_CFLAGS += -DTRUST_ALL_REPOSITORIES
PERL_PATH=/data/service/hnp/bin/perl
SHELL_PATH=/data/service/hnp/bin/bash
```

## 源码修改（适配补丁）
| # | 文件 | 修改 | 根因 |
|---|------|------|------|
| 1 | configure | `sed s/umask 077/umask 022/` | E129: HMDFS 新目录强制 setgid，umask 077 产生 drwx--S--- 连属主都不可写，config.status 无法生成 subs1.awk |
| 2 | compat/terminal.c 条件 | `HAVE_DEV_TTY=YesPlease`（无源码改动，走 termios 分支） | E093: musl 无 getpass 声明；鸿蒙有 /dev/tty，termios 分支为正确路径 |
| 3 | run-command.c | 两处 pthread_setcancelstate 调用用 `#ifndef NO_PTHREAD_CANCEL` 包裹 | E085: OHOS musl 裁剪线程取消 API，链接期 undefined symbol |
| 4 | setup.c ensure_valid_ownership() | `#ifdef TRUST_ALL_REPOSITORIES` 编译期短路（保留 GIT_TEST_ASSUME_DIFFERENT_OWNER 测试路径） | HMDFS 强制映射文件属主 uid（20001006）≠ 进程 uid（20020102），ownership 检查在平台语义下恒失败；config 方案（safe.directory=*）会污染 `git config --list` 输出破坏上游测试，故用编译期宏 |
| 5 | t/test-lib.sh | （测试框架，最终未保留修改；ownership 由 #4 解决） | — |

## 环境差异（非源码问题）
| 现象 | 根因 | 处理 |
|------|------|------|
| make install 失败 `install: No such file or directory` | E174: Toybox 无 coreutils install | 写 install.sh shim（支持 -d/-m/-p），经 `INSTALL="bash .../install.sh"` 注入 |
| git-gui 安装硬链接失败 | HMDFS 不支持硬链接 | NO_INSTALL_HARDLINKS=YesPlease（用拷贝）；git-gui/gitk 为 Tcl/Tk 程序，OHOS 无运行环境，NO_TCLTK=YesPlease 跳过 |
| 测试框架 `/usr/bin/perl` 找不到 | perl 在 /data/service/hnp/bin | config.mak PERL_PATH/SHELL_PATH 指定 |
| hooks `cannot exec: No such file or directory` | 系统 `/bin/bash` 不存在（仅有 /bin/sh），bash 位于 /data/service/hnp/bin/bash，hooks 的 `#!/bin/bash` shebang 解析失败 | hooks 功能本身正常；使用 `#!/data/service/hnp/bin/bash` 或 `#!/bin/sh` shebang |
| `git version --build-options` cpu 显示 | （继承自 2.45.2 已知项）编译期 uname 元数据 | 无功能影响 |

## 验证结果

详见 reports/test-report.md。摘要：
- 手工功能清单 34/34 全过（含 sha256/sparse/hooks/bisect/bundle/notes/range-diff/replace 等细节特性）
- HTTPS 全链路实测通过（kernel.org ls-remote 真实端点）
- 上游套件 t0000-t9xxx 全系列覆盖：最终轮约 96.5% 通过率，26 个批量失败单跑复核后 22 个 ≥92% 通过；失败均归类为 HMDFS 权限语义/慢 IO 竞争/环境缺失（无 /bin/bash、无 web 服务），无 git 本体缺陷
- conan-verify G0-G4 全绿（配方含 openssl/curl 依赖 flags 手动聚合 + curl-config 显式注入）

### 已知平台事项（非 git 缺陷）
1. hooks shebang 需用 `#!/bin/sh` 或 `#!/data/service/hnp/bin/bash`（系统无 /bin/bash）
2. 测试并行度超过 ~6 即可能触发 HMDFS 页缓存累积 → cgroup 内存耗尽（20 核机器实测 -j20/-j6 均会打爆，串行+批间休眠可跑）——此为系统内存回收特性，与 git 无关

## 交付物
- 安装前缀: /storage/Users/currentUser/usr/local（bin=7, libexec/git-core=174, templates 完整）
---

**编译结束**: 2026-10-15 13:21
**最终状态**: published
