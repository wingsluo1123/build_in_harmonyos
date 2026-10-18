# vitunes 2.3 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 Makefile，Linux 用 `Makefile.linux`，无 configure/CMake/Meson）
- 编译日期: 2026-10-17
- 编译器: clang 15.0.4（OHOS SDK，profile `ohos-aarch64`）
- 目标: OHOS aarch64（armv8）
- 状态: published（conan-verify G1-G4 通过；W3 本地 CI：L0/L1/L4/L5 pass、L2 warn 非阻塞）

## 编译步骤

```bash
# 1) 源码：GitHub 官方仓库 tag 2.3
#    https://github.com/ryanflannery/vitunes/archive/refs/tags/2.3.tar.gz
#    sha256 a78f79d08a3a0e83aa3f4aa406eca64747f0496a7b810a1f7bac3f620a2fc5f3
# 2) 上游 Makefile.linux 通过 taglib-config 与 -lncurses/-lutil 取依赖；
#    配方改为按 Conan 依赖（taglib/1.13.1 + ncurses/6.6）显式传入编译/链接参数：
make -f Makefile.linux \
  CC=<clang> \
  CFLAGS='-c -std=gnu99 -D_GNU_SOURCE -fPIC -Wall -Wextra -Wno-unused-value -I<taglib/include> -I<taglib/include/taglib> -I<ncurses/include>' \
  LDFLAGS='-L<...> -lm -lncursesw -ltag_c -ltag -lz <libc++.a> <libc++abi.a> <libunwind.a>' -j1
```

> 说明：命令行覆盖 `CFLAGS`/`LDFLAGS` 后，Makefile 中的 `taglib-config` 反引号与
> `-lncurses -lutil` 不会生效，因此上游 Makefile 无需改动，全部差异只在源码层。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `medialib.h:32: fatal error: 'fts.h' file not found` | OHOS sysroot 既无 `fts.h` 也无 `fts_open/fts_read/fts_close` 符号（`nm -D libc.so` 无 fts 符号，`find sysroot -name fts.h` 为空）；制品仓无 libbsd（`conan download libbsd/0.12.2 -r=ohpcd` 报 Recipe not found），无法作为依赖补齐 | 把 medialib.c 的目录遍历改为 POSIX `opendir/readdir/stat` 递归，并维护 dev/inode 祖先表防止符号链接环无限递归（`patches/0002`、`patches/0003`，纯 POSIX，无平台宏） |
| 2 | `vitunes -e check -s file` 等带选项的 e-command 全部报 `usage: -e check [-rsd] file1 ...` | `e_commands.c` 用 `char ch` 接收 `getopt(3)` 的返回值；aarch64 上 `char` 默认 **unsigned**，`ch = 255` 与 `-1` 比较恒为真，循环不终止，下一次迭代落入 default 分支报 usage（探针实测：`char ch` 时 inner getopt 打印 `ch=255` 后中断；`int ch` 时正常得到 `ch=115('s')`） | 三处 getopt 使用点（ecmd_check/ecmd_flush/ecmd_tag）`char ch` → `int ch`（`patches/0001`） |
| 3 | 产物运行报 `Error loading shared library libc++_shared.so` / 大量 `symbol not found` | 上游是 C 程序但 taglib C 绑定 `libtag_c.a` 包装 C++ API，运行期需要 libc++；OHOS 上 libc++ 只提供 `libc++_shared.so`，设备加载器不搜索其目录 | 静态链接 C++ 运行时：`clang -static-libstdc++` 在 OHOS clang 下**不生效**（实测仍报 `operator new` 等未定义符号），改为在配方中显式链接 `clang -print-file-name=libc++.a / libc++abi.a / libunwind.a`；`llvm-readelf -d` 确认产物 NEEDED 仅 `libc.so` |
| 4 | 链接 `-lncurses` 失败 / `-lutil` 在 OHOS 不存在 | ncurses 包为 wide 静态库（`--disable-shared --enable-widec`，libs=`ncursesw` 等），无 `libncurses.a`；源码不引用 libutil（`compat.h` 仅在 `__OpenBSD__`/`__FreeBSD__` 下 include `util.h`，全树无 `openpty/forkpty/login_tty`） | 链接行由配方按依赖重组为 `-lncursesw`，去掉 `-lutil` |
| 5 | `aggregated_components().includedirs` 取不到 `include/taglib` → `tag_c.h` 编译失败 | taglib 的组件视图只继承包级 `include`，vitunes 用 `#include <tag_c.h>` | 头文件路径先取包级 `cpp_info.includedirs`（`include` + `include/taglib`），再并入组件视图 |
| 6 | 依赖版本选择：taglib/2.3 无 C wrapper | taglib/2.3 配方 `BUILD_BINDINGS=False`，不产出 `libtag_c`/`tag_c.h`；taglib/1.13.1 提供 `tag_c` 组件 | 依赖固定为 `taglib/1.13.1`（同 `archives/e/ezstream/1.0.2` 先例） |

## 源码修改

| 补丁 | 文件 | 修改内容 |
|------|------|----------|
| `patches/0001-e_commands.c.patch` | e_commands.c | ecmd_check/ecmd_flush/ecmd_tag 中 `char ch` → `int ch`（getopt 返回值为 int） |
| `patches/0002-medialib.c.patch` | medialib.c | 目录遍历由 fts(3) 改为 POSIX dirent 递归（新增 `scan_file()`/`scan_dir()` + `struct scan_stats` + dev/inode 祖先表；输出与计数语义保持不变） |
| `patches/0003-medialib.h.patch` | medialib.h | `#include <fts.h>` → `#include <dirent.h>` |

## 依赖版本

| 依赖 | 版本 | 用途 | 说明 |
|------|------|------|------|
| taglib | 1.13.1 | 音频元数据读写 | 只用其 C 绑定（`tag_c.h` + `libtag_c`）；2.x 线无 C wrapper |
| ncurses | 6.6 | 终端 UI（wide 静态库） | `-lncursesw` |
| zlib | 1.3.1 | taglib 传递依赖 | 静态链接 |
| libc++/libc++abi/libunwind | SDK clang 15 自带静态库 | C++ 运行时 | 静态链接，产物仅依赖 `libc.so` |

## 验证结果

```bash
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify vitunes 2.3
G1: PASS   G2: PASS（conan create，test_package 真实执行）
G3: PASS（系统同名库隔离）   G4: PASS（产物完整性）
# conan-verify 内的 L2/L4/L5 因无 cache 路径被跳过（见 reports/conan-verify-report.md）；
# 安全/产物/冒烟检查以 W3 本地 CI 为准（reports/w3-local-ci.log）：
#   L0 pass / L1 pass（test_package executed，L1e 破坏性反向验证通过）/ L4 pass / L5 pass
#   L2 warn（vitunes -h 上游设计为打印 usage 后退出 1，非阻塞）

# test_package 端到端断言（conan create 内执行；日志 reports/conan-create.log 中
# 以 "PASS: vitunes -e help lists the supported e-commands" 起始、以 "11/11 checks passed" 收尾）
$ python3 test_package/test_vitunes.py <package>/bin/vitunes
PASS: vitunes -e help lists the supported e-commands
PASS: vitunes -e init creates the database file
PASS: vitunes -e add succeeds on the music tree
PASS: directory walk visits each directory exactly once (symlink cycle stops)
PASS: both tagged FLAC files are added to the database
PASS: directory walk reports no errors
PASS: scan summary counts 2 added files
PASS: non-audio file is reported as skipped
PASS: vitunes -e check -s shows the tags read via the taglib C API
PASS: vitunes -e flush dumps the database entries with their tags
PASS: vitunes -e update reports the 2 unchanged files as skipped
11/11 checks passed
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/vitunes` | CLI 主程序（`package_type=application`，软件级 `commands.json` 声明） |
| `share/man/man1/vitunes.1` | 上游 man 手册 |

## 注意事项

- 上游无任何测试用例（release tarball 46 个条目无 test/tests 目录、Makefile 无 check/test 目标），
  按 SKILL 要求自研 `test_package` 端到端测试（11 项断言，覆盖目录扫描、符号链接环终止、
  taglib 元数据提取、数据库导出与复扫）。
- 上游 `make install` 使用 `/usr/bin/install` 与绝对 `/usr/local` 路径，配方改为直接 copy 产物。
- 上游 `Makefile.linux` 依赖 `taglib-config`，OHOS/Conan 构建下不可用（仅本地环境探测用），
  配方通过命令行覆盖 `CFLAGS`/`LDFLAGS` 绕开，补丁中不含任何平台宏（PF5 通过）。
---

**编译结束**: 2026-10-17 17:25
**最终状态**: published
