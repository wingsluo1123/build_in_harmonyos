# nnn 5.0 适配笔记

**日期**: 2026-08-08
**状态**: ✅ 构建成功 (built)

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | nnn |
| 版本 | 5.0 |
| 描述 | 终端文件管理器 (n³) |
| 构建系统 | Makefile |
| 上游仓库 | https://github.com/jarun/nnn |
| 许可证 | BSD-2-Clause |

## 依赖

| 依赖 | 版本 | 来源 | 链接类型 |
|------|------|------|---------|
| ncurses | 6.6 | ohpcd Conan 制品仓 | 静态 (.a) |
| musl-fts | 1.2.7 | ohpcd Conan 制品仓 | 动态 (.so) |
| readline | 8.2 | 源码编译 (conanfile.py 内) | 静态 (.a) |

### readline 构建说明

readline 8.2 不在 ohpcd Conan 制品仓中，因此在 conanfile.py 的 build() 方法内从源码编译：
- 源码下载自 https://ftp.gnu.org/pub/gnu/readline/readline-8.2.tar.gz
- 应用 OHOS 平台补丁（config.guess/config.sub 添加 HarmonyOS 检测）
- 修复 HMDFS umask 问题（mktemp -d with umask 077 创建的目录不可写）
- 使用 `--disable-shared --enable-static` 静态编译
- 链接 ncurses（--with-curses）

## 编译步骤

1. `conan create` 触发 source() 下载 nnn 源码
2. build() 调用 _build_readline() 下载并编译 readline
3. build() 调用 _build_nnn() 使用 make 编译 nnn
4. package() 安装 nnn 二进制和 man page

## 关键修复

### 1. config.guess 添加 HarmonyOS 检测
readline 的 config.guess 不识别 HarmonyOS，添加 `*:HarmonyOS:*:*)` 分支输出 `aarch64-unknown-linux-ohos`。

### 2. config.sub 添加 ohos 支持
readline 的 config.sub 不识别 `linux-ohos`，需要三处修改：
- maybe_os case 添加 `linux-ohos*`
- OS 验证列表添加 `ohos*`
- kernel-OS 验证添加 `linux-ohos*`

### 3. HMDFS umask 问题
HarmonyOS HMDFS 文件系统中，`mktemp -d` 配合 `umask 077` 创建的目录无法写入。
修复：移除 configure 和 config.status 中的 `umask 077`。

### 4. TERMCAP_LIB 修复
readline 的 shlib/Makefile.in 中 TERMCAP_LIB 未正确传递，添加 `$(TERMCAP_LIB)` 到链接命令。

## 验证结果

- nnn -V: 输出 "5.0" ✅
- nnn -h: 显示完整帮助 ✅
- readelf -d: NEEDED libfts.so.0, libc.so (readline/ncurses 静态) ✅
- conan-verify: G0-G4 + L2/L4/L5 全部 PASS ✅

## 知识沉淀

- nnn 使用 Makefile 构建，通过 pkg-config 检测 ncursesw
- readline 不在制品仓时可在 conanfile.py 内从源码编译
- HMDFS umask 077 + mktemp -d 创建的目录不可写，需移除 umask
- readline config.sub 需要三处修改才能识别 linux-ohos
