# rawrec 0.9.991 适配笔记

## 编译环境

- 构建系统: makefile（`src/Makefile`，无 configure、无 CMake）
- 编译日期: 2026-10-13
- 编译器: clang/clang++（Conan `tools.build:compiler_executables` 提供）
- 状态: built（待 HarmonyOS aarch64 真机预检回填）
- 申请人: gcw_uQ09W7jl / 队伍：干

## 上游信息

- 上游版本: 0.9.991
- 上游仓库地址: http://rawrec.sourceforge.net
- 源码包: https://downloads.sourceforge.net/rawrec/rawrec-0.9.991.tar.gz（主，与 Gentoo ebuild SRC_URI 同源；2026-10-13 真机预检经此镜像成功取包进入 build 阶段）/ https://www.ibiblio.org/pub/Linux/apps/sound/recorders/rawrec-0.9.991.tar.gz（回退，本地实测 62134 字节 sha256 与配方完全一致；真机首试 ibiblio 曾报异哈希 3a2a…，由第二镜像自动恢复，本轮将真机可用的官方地址前置，sha256 保持不变）
- sha256: `1b65d65ae5f11650cc9cd2c10d54ac379eaaa802b89b08423b6a95046faac03f`
- 许可证: GPL-2.0-only（源码树 `copyright`）
- 源码结构: 共 39 个文件；`src/` 下约 20 个 `.c` 文件 + `rawrec.h` + 1 个 `Makefile`；`docs/user/rawrec.1` 为手册页

## 上游测试审计（R51 三步法第 1 步：清点）

- `src/Makefile` 目标: `all/debug/bin_install/man_install/install/clean/distclean/uninstall`，**无 `check`/`test` 目标**
- 源码包内无 `tests/` 目录、无 ctest/gtest/pytest 注册；唯一含 test 字样的 `src/test_dsp_params.c` 是生产代码（定义 `test_dsp_params()` 经 `OBJS = $(patsubst %.c,%.o,$(wildcard *.c))` 链接进 rawrec 主二进制，含 `rawrec.h` 引用与 SNDCTL_DSP_* ioctl，无断言/harness/独立 runner）
- Gentoo 侧同样未运行上游测试（ebuild 仅 `dobin rawrec` + man 页）
- 结论: 上游确无自动化测试（`upstream_tests_exist: false`，总数 0，口径 manual_audit，check 命令为空）

## 编译步骤

1. `get()` 解包（`strip_root=True`）
2. `apply_conandata_patches()` 打 soundcard 补丁 + 配方内 `replace_in_file` 做 Makefile 可移植改写（替代易漂移的 0001 补丁）
3. 取 Conan conf 的 C 编译器：`tools.build:compiler_executables:c`（回退 clang）
4. `make -j1 CC=<conan cc> OPTFLAGS=-O0 DEBUGFLAGS=-g1`（`cwd=src/`；命令行覆盖上游 `-O2`/`-O0 -g` 默认，低内存封顶，外部注入旗标经 `+=`/`?=` 保留）
5. `package()` 手工分装：`src/rawrec` → `bin/rawrec`，创建 `bin/rawplay` 软链接，`docs/user/rawrec.1` → `share/man/man1/`（含 `rawplay.1` 链接）；**不调用上游 `make install`**（其 `bin_install` 含 `chown root` + `chmod u+s`，制品包不需要 suid）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `CC = gcc` 硬编码、无视外部 CFLAGS/LDFLAGS，链接顺序 `$(OBJS) $(LDFLAGS)` 在现代工具链下易失败 | 2006 年手写 Makefile，未考虑发行版/交叉 flag 注入；原 0001 统一补丁因上游 Makefile 注释行漂移导致上下文失配（真机 `Failed to apply patch ... source file is different - src/Makefile`） | 配方 `build()` 内 `replace_in_file` 三处精确替换：`CC = gcc`→`CC ?=`、`CFLAGS = ...`→`CFLAGS +=`+`CPPFLAGS +=`（含 `_LARGEFILE64_SOURCE`）+`LDFLAGS ?=`+`LIBS = -lm -lpthread`、链接改为 `$(CC) $(LDFLAGS) $(OBJS) -o $(PROG) $(LIBS)`；经 ibiblio 镜像包实测字符串精确匹配，`debug` 目标的 `CC = gcc-3.2` 不受影响 |
| 2 | `audio_init.c` / `test_dsp_params.c` / `get_format_code.c` 直引 `<linux/soundcard.h>`，OHOS 下该头文件缺失导致编译失败 | 上游只面向 Linux OSS Free API | 补丁 0002：`__has_include` 三级探测（linux → sys → 顶层），缺失时提供最小 OSS 常量/ioctl 回退；全程特性检测，补丁内无 `__OHOS__` 平台宏（PF5 合规） |
| 3 | 上游 `make install` 做 `chown root/chgrp root/chmod u+s` | suid 音频工具的历史设计，容器/制品场景不需要且会失败 | 配方内手工 `copy` + `os.symlink` 分装，不调用 `bin_install`/`man_install` |
| 4 | 0002 补丁 `Failed to parse patch ... invalid hunk ... patch stream is incomplete` 导致 build 阶段失败 | 手写补丁的 hunk 头计数错误（新行数写成 39/39/40，实际为 29/29/30）且空白上下文行缺少前导空格，Conan 严格校验下报 invalid hunk 并因预期行数不足报 stream incomplete | 用 `git diff` 重新生成补丁：修正为 `@@ -20,7 +20,29 @@` / `@@ -16,7 +16,29 @@` / `@@ -7,7 +7,30 @@`，空白上下文行保留单空格前缀（含尾部空行），内容（__has_include 三级探测 + 最小 OSS 回退）与原补丁一致，经 `git apply --check/--apply` 验证三文件干净打上 |

## 源码修改

- 配方 `build()` 内 `replace_in_file` 改写 `src/Makefile`（尊重外部 CC/CFLAGS/LDFLAGS，修正链接库顺序；替代已删除的 0001 补丁）
- `patches/0002-soundcard-header-fallback.patch` — 三处 `linux/soundcard.h` 引用改为特性检测 + 最小 OSS 回退定义

## 依赖版本

- 无 Conan 依赖（仅系统 `libm`/`libpthread`，经 `LIBS` 链接）

## 验证结果

- 本地未跑 conan（按任务守则，验证统一走真机预检）
- test_package 设计 3 个用例（`rawrec --version` 含 `version 0.9.99` 字符串、`rawrec --help` 成功退出、`rawplay --version` 软链接有效）；均无需音频硬件（`record()`/`play()` 的 `/dev/dsp` 路径不在测试范围内）
- 上游测试：0 个（无测试可跑，`HMBS_UPSTREAM_TEST_RESULT` 以 `no_tests` 输出）
- 待 HMBS 真机预检回填：`conan create` 日志、`HMBS_TEST_PACKAGE_RESULT`、`HMBS_UPSTREAM_TEST_RESULT` 实测计数

## 注意事项

- `rawrec --version` 上游硬编码打印 `version 0.9.99`（与包版本 0.9.991 不一致，属上游历史笔误，测试据此断言，不修改上游行为）
- `--help` 上游仅打印 `Try ... --help ...` 一行并退出 0（不打印完整 usage），测试只断言成功退出
- 真机/CI 均无 `/dev/dsp`，录音/放音真实音频路径无法验证；测试覆盖 CLI 解析与分装完整性，不覆盖音频 ioctl
- 稀疏检出说明：本机为绕开上游 `archives/g/gama/2.29/patches/` 下一个含回车文件名在 Windows 落盘失败，本地 `.git/info/sparse-checkout` 排除了 `archives/g/gama/`；该配置仅本地生效、不进版本控制，不影响本 PR 内容（本 PR 只含 `archives/r/rawrec/`）
