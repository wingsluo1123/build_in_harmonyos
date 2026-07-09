# yabasic 2.91.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-25
- 编译器: clang/clang++ (clang 15.0.4, aarch64-unknown-linux-ohos)
- 平台: aarch64-unknown-linux-ohos (HarmonyOS)
- 状态: built

## 编译步骤

1. 下载 release tarball: `https://www.yabasic.de/download/yabasic-2.91.4.tar.gz` (762KB)
2. init-build: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build yabasic 2.91.4 --url=... --no-download`
3. 安装预编译依赖: ncurses 6.4, libx11 6.4.0, xorgproto 2024.1, libxau 6.0.0
4. 生成 ncurses 头文件（预编译包缺少头文件）:
   - 下载 ncurses 6.4 源码
   - 修补 config.guess/config.sub 支持 HarmonyOS
   - 修补 config.sub 添加 linux-ohos* 到 kernel-OS 兼容性列表
   - 用 Python 从 config.status 提取替换变量，处理 .h.in 模板
   - 用 awk + MKterm.h.awk 生成 term.h
   - 组装完整 curses.h: curses.head + MKkey_defs(Caps) + curses.wide + curses.tail (2114行)
5. 创建 stub libxcb.so.1（libX11 依赖但无预编译包）
6. 修补 yabasic 的 config.guess/config.sub（替换为新版本，支持 HarmonyOS）
7. configure: `CPPFLAGS="-I$DEFAULT_PREFIX/include" LDFLAGS="-L$DEFAULT_PREFIX/lib" ./configure --prefix=$DEFAULT_PREFIX --without-ffi`
8. 修复 configure 脚本的两个问题:
   - ECHO 检测: `if test "X\`( print -r -- -n ) 2>` → `if false && \` (禁用 ksh print 检测，强制使用 printf)
   - umask 077 → umask 022 (修复 HarmonyOS 临时目录权限问题)
9. make -j1 — 编译成功，生成 yabasic 二进制 (518KB ELF)
10. make install DESTDIR=$TEST_PREFIX — 暂存安装
11. make check — 18/21 PASS，3 个 shell 脚本测试因 /bin/bash 不存在而 FAIL，手动验证全部通过
12. package — 打包成功，生成 2 个 tar.gz
13. make install (无 DESTDIR) — 安装到 $DEFAULT_PREFIX
14. 验证: `$DEFAULT_PREFIX/bin/yabasic --version` → "yabasic 2.91.4, built on aarch64-unknown-linux-ohos"

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 下载 URL 404 | Savannah 镜像失效 | 使用官方站点 yabasic.de 下载 |
| 2 | config.guess 无法识别平台 | 2015版过旧，无 HarmonyOS 检测 | 替换为 2022-08-01 版本 (E007) |
| 3 | config.sub 拒绝 linux-ohos 三元组 | kernel-OS 兼容性列表缺少 linux-ohos* | 手动添加 linux-ohos* 到 case 列表 (E007) |
| 4 | ncurses 预编译包缺少头文件 | 预编译包只含 .a 和 config 脚本 | 从 ncurses 6.4 源码生成头文件 (E092) |
| 5 | configure ECHO='print -r --' | libtool 检测到 ksh print，但平台 sh 不支持 | 禁用 print 检测，强制使用 printf (E082) |
| 6 | configure umask 077 临时目录不可写 | umask 077 创建的目录平台限制不可写 | 改为 umask 022 (E082) |
| 7 | X11/Intrinsic.h not found | libXt (X toolkit) 不可用 | 移除未使用的 #include (E092) |
| 8 | libX11.so 依赖 libxcb.so.1 | libxcb 无预编译包 | 创建 stub libxcb.so.1 (E092) |
| 9 | 3 个 shell 脚本测试 FAIL | #!/bin/bash 不存在，exit status 126 | 环境兼容性问题，手动验证通过 |

## 源码修改

1. **config.guess**: 替换为新版本 (2022-08-01)，含 HarmonyOS 系统识别
2. **config.sub**: 替换为新版本，添加 linux-ohos* 到 kernel-OS 兼容性列表
3. **yabasic.h**: 移除 `#include <X11/Intrinsic.h>`（未使用任何 Xt 类型/函数，libXt 不可用）
4. **configure**: (1) 禁用 ksh print ECHO 检测，强制使用 printf; (2) umask 077→022 修复临时目录权限

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| ncurses | 6.4 | 预编译包 (库) + 源码生成 (头文件) |
| libx11 | 6.4.0 | 预编译包 |
| xorgproto | 2024.1 | 预编译包 |
| libxau | 6.0.0 | 预编译包 |
| libxcb | stub | 手动创建 stub 库 (返回 NULL/0) |
| libffi | - | 不可用，使用 --without-ffi 禁用 |

## 验证结果

### 二进制版本验证
```bash
$ $DEFAULT_PREFIX/bin/yabasic --version
yabasic 2.91.4, built on aarch64-unknown-linux-ohos
```

### make check 真实输出
```
PASS: tests/break.yab
PASS: tests/bugs.yab
PASS: tests/grammar.yab
PASS: tests/io.yab
PASS: tests/long_variable_name.yab
PASS: tests/simple.yab
PASS: tests/switch_continue_break.yab
PASS: tests/switch_for.yab
PASS: tests/switch_gosub.yab
PASS: tests/switch_goto.yab
PASS: tests/switch_return.yab
PASS: tests/switch_simple.yab
PASS: tests/switch_subr.yab
PASS: tests/switch.yab
PASS: tests/numbers.yab
PASS: tests/system.yab
PASS: tests/string.yab
FAIL: tests/silent.sh
PASS: tests/nested_import.yab
FAIL: tests/docu.sh
FAIL: tests/read_stdin.sh
============================================================================
# TOTAL: 21
# PASS:  18
# FAIL:  3
============================================================================
```

### 失败测试手动验证
```bash
$ /data/service/hnp/bin/bash tests/silent.sh; echo $?
0
$ /data/service/hnp/bin/bash tests/docu.sh; echo $?
0
$ /data/service/hnp/bin/bash tests/read_stdin.sh; echo $?
0
```

失败原因: 脚本 shebang 为 `#!/bin/bash`，HarmonyOS 上 bash 位于 `/data/service/hnp/bin/bash`，`/bin/bash` 不存在导致 exit status 126。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| yabasic-2.91.4-ohos-aarch64.tar.gz | 2.1MB | 预编译包 (release) |
| yabasic-2.91.4-ohos-aarch64-debug.tar.gz | 284KB | 预编译包 (debug) |

## 注意事项

- ncurses 预编译包缺少头文件，需从源码生成
- libX11 依赖 libxcb，无预编译包时需创建 stub
- configure 的 umask 077 在 HarmonyOS 上导致临时目录不可写
- yabasic 的 X11 图形功能在无 X server 环境下不可用（stub libxcb 使 X11 调用优雅失败）
- --without-ffi 禁用了 foreign library 调用功能（libffi 不可用）

## 知识积累

- ✅ config.guess (2015版) 过旧无法打补丁，需替换为新版本 (2022-08-01) — ref: E007
- ✅ config.sub 需要添加 linux-ohos* 到 kernel-OS 兼容性列表 — ref: E007
- ✅ ncurses 预编译包缺少头文件，需从源码生成 — ref: E092
- ✅ ncurses curses.h 由 curses.head + MKkey_defs + curses.wide + curses.tail 组装而成 — ref: E092
- ✅ configure 的 umask 077 导致创建的临时目录不可写（平台限制），需改为 umask 022 — ref: E082
- ✅ configure 的 ECHO='print -r --' 使用 ksh print 命令，需禁用 print 检测强制使用 printf — ref: E082
- ✅ libX11.so 依赖 libxcb.so.1，预编译包不可用时需创建 stub 库 — ref: E092
- ✅ yabasic 包含 X11/Intrinsic.h 但实际不使用任何 Xt 类型/函数，可安全移除 — ref: E092

### 对话 #1: configure ECHO 检测问题

**问题**: configure 脚本第 3602 行检测 ksh 的 `print -r --` 命令作为 ECHO 实现，但 HarmonyOS 的 sh (musl libc) 不支持 `print` 内建命令。

**分析**: libtool 的 configure 脚本通过 `if test "X\`( print -r -- -n ) 2>` 检测 print 是否可用。如果可用，设置 `ECHO='print -r --'`。但 HarmonyOS sh 不支持 print，导致检测逻辑异常。

**解决方案**: 将 `if test "X\`( print -r -- -n ) 2>` 改为 `if false && \` 强制跳过 print 检测，使用 printf 作为 ECHO。

### 对话 #2: umask 077 临时目录权限问题

**问题**: configure 脚本在第 17636/17641 行使用 `umask 077` 创建临时目录，但 HarmonyOS 平台限制下 umask 077 创建的目录权限不足，导致后续写入失败。

**分析**: `umask 077` 将文件权限设置为 600、目录权限设置为 700。在 HarmonyOS 的 HMDFS 文件系统上，某些操作需要更宽松的权限。

**解决方案**: 将所有 `umask 077` 替换为 `umask 022`（目录权限 755，文件权限 644）。

### 对话 #3: ncurses 头文件缺失

**问题**: 从 cmd-pkgs 安装的 ncurses 预编译包只包含 .a 静态库和 config 脚本，不包含 curses.h、term.h 等头文件。

**分析**: yabasic 的 configure 检测 `curses.h` 和 `ncurses.h`，缺少头文件会导致 configure 失败。

**解决方案**: 下载 ncurses 6.4 源码，运行 configure 后用 Python 脚本从 config.status 提取 sed 替换变量，处理 .h.in 模板文件。curses.h 需要从 curses.head + MKkey_defs.sh(Caps) + curses.wide + curses.tail 组装（共 2114 行）。term.h 由 MKterm.h.awk 生成。

### 对话 #4: libX11 依赖 libxcb

**问题**: yabasic 链接 libX11，而 libX11.so 依赖 libxcb.so.1，但 cmd-pkgs 中没有 libxcb 的预编译包。

**分析**: yabasic 使用 X11 进行图形输出。libX11 的动态库在运行时需要 libxcb.so.1。

**解决方案**: 创建一个 stub libxcb.so.1，其中所有函数返回 NULL/0。这样 X11 调用会优雅失败而不是崩溃。编译命令: `clang -shared -o libxcb.so.1 stub_xcb.c`。

### 对话 #5: X11/Intrinsic.h 不可用

**问题**: yabasic.h 包含 `#include <X11/Intrinsic.h>`，但 libXt (X toolkit intrinsics) 在 HarmonyOS 上不可用。

**分析**: 检查 yabasic 源码后发现，虽然包含了 Intrinsic.h，但实际代码中并未使用任何 Xt 类型或函数（如 Widget、XtAppContext 等）。这个 include 是历史遗留。

**解决方案**: 移除 `#include <X11/Intrinsic.h>`，添加注释说明移除原因。编译验证通过，无功能影响。
---

**编译结束**: 2026-06-26 15:12
**最终状态**: built
