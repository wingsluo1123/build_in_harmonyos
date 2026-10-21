# pmidi 1.7.1 适配笔记

## 编译环境
- 构建系统: autotools（源码包自带预生成 configure，无需 autoreconf）
- 编译日期: 2026-10-13
- 编译器: clang 15.0.4 / clang++（OHOS aarch64，musl）
- 状态: built（conan create 通过：编译 + test_package 全绿）

## 编译步骤

```bash
# 依赖（W0 预检通过，制品仓已发布）：alsa-lib/1.2.16.1
conan create archives/p/pmidi/1.7.1 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方内部流程（`conanfile.py`）：

1. `generate()`：AutotoolsToolchain + AutotoolsDeps（把 alsa-lib 的 `-I`/`-L`/`-lasound` 注入
   CPPFLAGS/LDFLAGS/LIBS）。**不声明 glib 依赖**：pmidi 自带 `src/glib.c` 最小 GLib 子集，
   configure 的 `AC_CHECK_HEADER(glib.h)` 探测失败后自动启用内置实现。
2. `build()`：apply 3 个补丁 → 把依赖 lib 目录（+ SDK llvm/lib）加入 `LD_LIBRARY_PATH` →
   `./configure` → `make -j1`。
3. `package()`：`make install`（install-sh `-c`），交付 `bin/pmidi` + `share/man/man1/pmidi.1`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./config.guess: unable to guess system type` / `configure: error: cannot guess build type` | config.guess（2015-01-01）无 HarmonyOS 分支；`uname -s` 返回 `HarmonyOS`，不匹配任何已知系统模式（E007） | 补 `*:HarmonyOS:*:*)` 分支输出 `aarch64-unknown-linux-ohos`；**必须 `echo ... ; exit`**（该脚本各 case 分支自行返回，缺 exit 会继续走到需编译 dummy.c 的兜底逻辑） |
| 2 | `config.sub: Invalid configuration 'aarch64-unknown-linux-ohos': machine 'aarch64-unknown-linux' not recognized` | config.sub（2015 版，无 `basic_os` 机制）不认识 `-ohos`；从右解析使 os=-ohos、machine=aarch64-unknown-linux（E072/E122） | 两处修改：`maybe_os` 列表加 `linux-ohos*`；OS 白名单加 `-linux-ohos*`。仅改白名单不生效——`maybe_os` 不匹配时 os 被拆成 `-ohos` |
| 3 | `configure: error: cannot run C compiled programs` / `Error loading shared library libatopology.so: (needed by ./conftest)` | configure 的跨编译试探程序链接了 `-lasound`，运行期找不到依赖共享库（无 RUNPATH） | 构建环境把依赖包 `lib/`（+ SDK llvm/lib）加入 `LD_LIBRARY_PATH` 后再 configure（与 aseqjoy 同款） |
| 4 | `config.status: error: could not setup config files machinery`（HMDFS） | configure 用 `umask 077 && mktemp -d ./confXXXXXX` 建 config.status 临时目录，HMDFS 上该目录不可写（E011/E114/E129） | 补丁把 `umask 077` → `umask 022`（两处） |
| 5 | `checking glib.h usability... no` | 未声明 glib 依赖，头文件不可见 | 预期行为：pmidi 自带 `src/glib.c` 最小 GLib 子集，`WITH_INCLUDED_GLIB=1` 自动启用，无需外部 GLib |

## 源码修改

3 个补丁（`patches/`，均为平台可移植性，无平台宏）：

- `0001-config.guess.patch`：补 HarmonyOS 系统识别分支（`aarch64-unknown-linux-ohos`，含 `echo`+`exit`）。
- `0002-config.sub.patch`：接受 `linux-ohos` 三元组（maybe_os 列表 + OS 白名单两处）。
- `0003-configure.patch`：config.status 临时目录 `umask 077` → `022`。

未改动任何 `src/*.c`（pmidi 源码本身无需平台修改）。

## 依赖版本

- alsa-lib/1.2.16.1（传递：libatopology，同包内）
- 无 GLib 外部依赖（使用源码内嵌的最小 GLib 子集）

## 上游测试

上游**无自动化测试**（清点证据）：

```bash
$ grep -rn "TESTS\|check_PROGRAMS\|check-local" Makefile.am src/Makefile.am man/Makefile.am
# → 0 命中；源码包无 tests/ 目录
$ make check
# → exit 0；man/ src/ 顶层逐目录输出 "Nothing to be done for 'check'"
```

日志：`reports/upstream-make-check.log`。

## 验证结果

```bash
# 1) 真实构建
conan create archives/p/pmidi/1.7.1 -pr:h=... -pr:b=...
#   → Package created，产物 bin/pmidi + share/man/man1/pmidi.1

# 2) test_package（消费者 + 鸿蒙专项）
#   test.sh（3 断言）: pmidi -v -> pmidi-1.7.1；无参数给出 "No client/port specified"；手册页存在
#   test_ohos.sh（8 断言）: 平台=OpenHarmony；ELF64/AArch64；.codesign；PT_INTERP=ld-musl-aarch64.so.1；
#                        无 glibc 专有 NEEDED；链接 libasound.so；依赖闭包可解析；设备端 pmidi -v 正常
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/pmidi` | 命令行 MIDI 播放器（ELF64/AArch64，带 .codesign） |
| `share/man/man1/pmidi.1` | 手册页 |

软件级 `commands.json` 已声明（R38，type=tool）。

## 注意事项

- **运行期平台限制**：OHOS 内核不提供 ALSA sequencer（`/dev/snd/seq` 不存在），
  因此实际播放与 `pmidi -l` 端口枚举在设备上报
  `Could not open sequencer No such file or directory`；`pmidi -v` / 无参数用法提示正常。
  本适配保证构建、链接、安装与可执行文件在 OHOS 上正常加载运行，缺 sequencer 时按上游逻辑报错退出。
- 使用方注意：运行 pmidi 需 `LD_LIBRARY_PATH` 能解析 `libasound.so`/`libatopology.so`
  （conan 依赖链由 `conan install`/`VirtualRunEnv` 自动注入）。
---

**编译结束**: 2026-10-13 14:29
**最终状态**: built
