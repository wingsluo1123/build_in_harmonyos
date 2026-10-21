# vdr 2.6.9 适配笔记

## 编译环境

| 项 | 值 |
|---|---|
| 构建系统 | 手写 GNU make（`Makefile` + 可选 `Make.config`），无 configure / CMake / meson |
| 编译器 | clang 15.0.4（`aarch64-unknown-linux-ohos`，`/data/service/hnp/bin/clang`） |
| C++ 标准 | profile 的 `compiler.cppstd=17`（VDR 2.6.9 用到二进制字面量 `0b…`，至少需 C++14） |
| 目标 | `make vdr`（只建录像机主程序 + 内置 `libsi/libsi.a`） |
| 依赖 | libjpeg-turbo/3.2.0、libcap/2.78、freetype/2.14.3、fontconfig/**2.18.1.1**（连带 expat/2.8.2.1） |
| N（上游测试数） | **0** —— 2.6.9 tarball 内无 `make check` 目标、无 `test/` 目录、无 `test_*`/`*_test.*` 文件 |

## 构建步骤

```sh
# recipe 内实际执行的命令（INCLUDES/LIBS 由依赖 cpp_info 聚合而成）
make -j1 VERBOSE=1 -C <src> vdr \
    CC=<clang> CXX=<clang++> PKG_CONFIG=true \
    CINCLUDES="<deps include dirs> -I<generators>" \
    LIBS="<deps -L/-l> -L/lib -l:ld-musl-aarch64.so.1"
```

只有 `vdr` 目标被构建。上游的 `all` 还包含：

- `i18n`：从 `po/*.po` 生成 `.mo`，需要 `xgettext`/`msgfmt`（设备上只存在于 harmonybrew，CI worker 无）
- `plugins`：`PLUGINS/src/` 下 8 个演示插件，其中 `skincurses` 需要 ncurses

两者都不属于本包交付的录像机主程序，故不构建（README/manifest 已如实披露）。

## 关键决策与依据

| # | 决策 | 依据 |
|---|---|---|
| 1 | 不拷贝 `Make.config.template` → `Make.config` | 该模板把 `CC = gcc` / `CXX = g++` 写成**硬赋值**（非 `?=`）；照抄会把 gcc 假设带入。Makefile 自身用 `CC ?=`/`CXX ?=`，命令行传值即可 |
| 2 | 只传 `CC/CXX/PKG_CONFIG/CINCLUDES/LIBS`，**不传** `CXXFLAGS` | make 命令行变量优先，会顶掉 Makefile 内 `CXXFLAGS += -fPIC` 的追加（`+=` 对命令行变量无效）——传了会丢 `-fPIC` |
| 3 | 用 `CINCLUDES`（而非 `INCLUDES`）注入依赖头路径 | `INCLUDES ?= $(shell $(PKG_CONFIG) --cflags freetype2 fontconfig)`，而 Makefile 后段有 `INCLUDES += $(CINCLUDES)`，故 `CINCLUDES` 是官方留的追加口；同时用 `PKG_CONFIG=true` 关掉无用的 pkg-config 探测 |
| 4 | 依赖 flags 由 `cpp_info.aggregated_components()` 聚合，不用 pkg-config | 全图（含 fontconfig→freetype/libxml2 等传递依赖）一次性覆盖，避免 .pc 生成链引入不确定性 |
| 5 | 链接 `-L/lib -l:ld-musl-aarch64.so.1` | `gettext` 家族、`adjtime`、`pthread_cancel` 在 **SDK 链接期 `libc.so` 桩**里不存在，但在**运行期 musl 加载器**里导出（实测 `llvm-nm --dynamic --defined-only /lib/ld-musl-aarch64.so.1`）。同 glib/abr2gbr recipe 的既有做法 |
| 6 | recipe `generate()` 写入最小 `libintl.h` | SDK 的 `libintl.h` 是空桩：只 `#define __USE_GNU_GETTEXT 1` 与 `__GNU_GETTEXT_SUPPORTED_REVISION`，**不声明任何 gettext 函数**；`i18n.c` 因此拿到隐式声明 |

## 遇到的问题与解决方案

| # | 现象（逐字） | 根因 | 解决方案（patch 0001） |
|---|---|---|---|
| 1 | `tools.h:450:20: error: token is not a valid binary operator in a preprocessor subexpression` | `__GLIBC_PREREQ` 是 glibc `<features.h>` 独有宏，OHOS musl 无 | 在 `tools.h` 非 glibc 分支注入 `#define __GLIBC_PREREQ(maj,min) 1`（走 `readdir()` 现代分支）并定义 `VDR_NO_GLIBC` 供后续条件编译 |
| 2 | `tools.h:477: error: use of undeclared identifier 'DEFFILEMODE'`（共 8 处） | `DEFFILEMODE`（0666）是 glibc `<sys/stat.h>` 扩展 | 同上注入 `#define DEFFILEMODE (S_IRUSR\|S_IWUSR\|…)` |
| 3 | `tools.h:824: error: unknown type name '__compar_fn_t'` | 该 typedef 是 glibc 扩展 | 同上注入等价 typedef |
| 4 | `i18n.h:49: expected function body after function declarator` → 级联 **125 处** `use of undeclared identifier 'I18nTranslate'` | `__attribute_format_arg__` 是 glibc `<sys/cdefs.h>` 宏；缺失使 `I18nTranslate` 声明变成语法错，全树依赖它的 TU 一并炸 | 注入 `#define __attribute_format_arg__(x) __attribute__((format_arg(x)))` |
| 5 | `vdr.c:141: unknown type name 'cap_t'`、`cap_from_text`/`cap_get_proc`/`CAP_SET`/`CAP_PERMITTED`/`cap_flag_value_t` 未声明 | OHOS 的 `sys/capability.h` **只有** `capget`/`capset` 系统调用，没有 libcap 用户态 API | 引入 conan `libcap/2.78`；其 `sys/capability.h` 经 `-I` 先于 sysroot 命中（无需改源码） |
| 6 | `i18n.c:136: use of undeclared identifier 'gettext'`（另 `textdomain`/`bindtextdomain`/`dgettext` 共 8 处） | SDK `libintl.h` 空桩 + `libc.so` 桩无 gettext 符号 | recipe 注入最小 `libintl.h` + 链接 musl 加载器（决策 5、6） |
| 7 | `eit.c:482: use of undeclared identifier 'adjtime'` | OHOS 头集未声明 `adjtime`（符号在加载器里） | patch 加 `extern "C" int adjtime(const struct timeval *, struct timeval *);` |
| 8 | `thread.c:381: use of undeclared identifier 'pthread_cancel'` | 同上 | patch 加 `extern "C" int pthread_cancel(pthread_t);`（须放在 `#include "tools.h"` **之后**，否则 `VDR_NO_GLIBC` 尚未定义） |
| 9 | `vdr.c:1599: use of undeclared identifier 'malloc_trim'` | `malloc_trim` 是 glibc 独有 | patch 条件化屏蔽该调用（musl 更早归还内存） |
| 10 | `thread.c:163: use of undeclared identifier 'PTHREAD_RWLOCK_PREFER_WRITER_NP'`、`pthread_rwlockattr_setkind_np` 不存在 | musl 无 rwlock "kind" 属性 | patch 条件化跳过该属性设置 |
| 11 | `thread.c:213: use of undeclared identifier 'PTHREAD_MUTEX_ERRORCHECK_NP'` | 常量是 glibc 命名 | 改用 OHOS 提供的 `PTHREAD_MUTEX_ERRORCHECK`（两者数值同为 2） |
| 12 | `osd.c:15: fatal error: 'sys/unistd.h' file not found` | 该路径是 glibc 专有 | patch 条件化改用 `<unistd.h>` |
| 13 | `vdr.c:665: error: cannot assign to variable 'stdin' with const-qualified type 'FILE *const'` | OHOS `<stdio.h>` 把三者声明为 `FILE *const` | patch 条件化去掉赋值（`freopen()` 本就原地重定向，赋值冗余） |
| 14 | `svdrp.c:76: no matching member function for call to 'Set'`（候选只有 `Set(const char*, int)`） | `INADDR_ANY` 展开为 `((in_addr_t) 0x00000000)`，是 **非字面量空指针常量**——C++03 允许、C++11 起不再是空指针常量。GCC 容忍，clang 报错（实测 `-Wnon-literal-null-conversion` 仅在 `-std=gnu++03` 下退化为告警） | patch 条件化改用文本形式 `Set("0.0.0.0", 0)`（语义等价：通配地址 + 端口 0） |
| 15 | `font.c:19: error: expected "FILENAME" or <FILENAME>`（`#include FT_FREETYPE_H`） | 缺 freetype 头 | conan `freetype/2.14.3`（其 cpp_info 已含 `include/freetype2`） |
| 16 | `tools.c:18: fatal error: 'jpeglib.h' file not found` | 缺 libjpeg 头 | conan `libjpeg-turbo/3.2.0` |
| 17 | `fontconfig/fontconfig.h file not found` | 缺 fontconfig 头 | conan `fontconfig/2.18.1.1`；另见「运行期依赖库加载」节（远端 2.18.3 的 `.so` 在本机 `dlopen` 报 EACCES，故固定到本机构建且实测可加载的 2.18.1.1） |

> 注：第 1–4 条集中在 `tools.h` 一个 hunk 内（`tools.h` 被几乎所有 TU 包含，是最省的注入点）；`VDR_NO_GLIBC` 由该 hunk 定义。

## 运行期依赖库加载（fontconfig 版本固定的原因）

本机 OHOS 加载器**拒载 conan 远端的 `fontconfig/2.18.3` 共享库**，逐条实测：

| # | 读数 | 结论 |
|---|---|---|
| 1 | `dlopen("…/p/lib/libfontconfig.so.1.17.0")` → `Permission denied`（errno=13），可稳定复现 | 该 `.so` 本身不可加载 |
| 2 | 该文件 md5 `90e16133de27e24474c8d04807b0e55e` == 包内 `conanmanifest.txt` 记录值 | **不是下载损坏** |
| 3 | 复制到另一目录后仍 EACCES；`llvm-objcopy --remove-section=.codesign` 后仍 EACCES | 与路径、与 `.codesign` 段有无均无关 |
| 4 | 同 cache 内 `libfreetype.so.6`、`libjpeg.so.62`、`libturbojpeg.so.0`、`libxml2.so.16`、`libexpat.so.1` 均 `dlopen` OK | 非"所有共享库都不可加载" |
| 5 | 本机构建的 `fontconfig/2.18.1.1`（连带 `expat/2.8.2.1`）`dlopen` **OK** | 改用本机构建且实测可加载的版本 |
| 6 | 把 26 个 conan `p/*/lib` 全部注入 `LD_LIBRARY_PATH` 后仍拒载 | 排除"依赖没找齐" |

因此本包 `requirements()` 固定 `fontconfig/2.18.1.1`（连带 `expat/2.8.2.1`），而不是更高的 2.18.3。

**连带后果（如实记录）**：产物运行需要 conan run 环境提供依赖库目录（`test_package` 已按此验证 3/3；
`conan-verify` 的 L2 自动通道因同一原因 SKIP，已由 `reports/conan-verify-supplement.md` 人工补测）。
不带该环境直接执行会得到 `Error loading shared library libjpeg.so.62 / …` 与 rc=127——这是
动态依赖的常规表现，**不是编译缺陷，也不写成 PASS**。

## 运行期设备事实（本设备实测）

```
ABSENT  /dev/dvb          ABSENT  /sys/class/dvb
ABSENT  /dev/video0       ABSENT  /dev/input       ABSENT  /dev/ttyUSB0
PRESENT linux/dvb/frontend.h  linux/dvb/version.h  linux/dvb/dmx.h  (sysroot)
```

`dvbdevice.c` 的适配器枚举路径：

- `dvbdevice.c:2438: cReadDir d("/sys/class/dvb");` → 目录不存在，枚举 **0 条**
- `dvbdevice.c:2435: cString::sprintf("/dev/dvb/adapter%d/frontend%d", …)` → `open()` 必 `ENOENT`

因此本设备上 `vdr` 启动后必然是「0 个 DVB 设备」状态；`--version` / `--help` 在设备探测之前返回，是唯一可在本机稳定断言的行为面。

## 测试统计

见 `reports/test-report.md`（上游 N=0 与 `test_package` 分栏统计）。
