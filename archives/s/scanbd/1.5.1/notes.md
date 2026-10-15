# scanbd 1.5.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-10-03
- 编译器: clang/clang++（OHOS SDK 26.0.0.18，sysroot aarch64-linux-ohos）
- 目标: os=OHOS, arch=armv8, build_type=Release
- 状态: built

## 编译步骤

```bash
conan create . --build=missing -pr:h ohos-aarch64 -pr:b default
```

配方 `build()` 内自动完成：

1. `apply_conandata_patches()` — 应用 `patches/0001`~`0004`
2. `autotools.configure()` — `--host=aarch64-linux-ohos --build=aarch64-linux-gnu
   --with-systemdsystemunitdir=no --disable-udev --disable-hal
   ac_cv_func_malloc_0_nonnull=yes`
3. `autotools.make(args=["-j1"])`
4. `package()`: `autotools.install()`

`generate()` 另外做两件平台必需的事：把依赖包内的 libtool archive 复制到
`<generators>/ohos-la-stage` 并改写 `libdir`/`dependency_libs`，再往生成的每个
`.pc` 的 `Libs:` 前置该 staging 目录；以及补一个 `dbus-1.pc` 别名（Conan 的 dbus
配方导出的是 `dbus.pc`，上游 configure.ac 探测的是 `dbus-1`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.sub` 不认 `aarch64-linux-ohos` | 上游 Autoconf 快照早于 HarmonyOS | `patches/0001-config.sub-ohos.patch` |
| 2 | `./confXXXX/subs1.awk: Permission denied` → `could not setup config files machinery` | HMDFS 上 `mktemp -d` 的 0700 目录投影为不可写 (E114/E046) | `patches/0002-configure-tmpdir-mkdir.patch`：改用 `mkdir` |
| 3 | `undefined symbol: pthread_cancel/_testcancel/_setcancelstate` | OHOS libc 无线程取消 API（仅导出 `_pthread_cleanup_push/pop`） | `patches/0003`：dbus.c/sane.c 改协作式停止标志；并移除 sane.c 自带的 `#define CANCEL_TEST`（否则取消测试块是活代码） |
| 4 | libtool: `//lib/libpng16.la is not a valid libtool archive`、`/usr/local/lib/libusb-1.0.la` 找不到 | 依赖包内 `.la` 记录其构建机绝对路径（`libdir='//lib'`、`dependency_libs` 含绝对 `.la`） | 见下节「libtool archive staging」 |
| 5 | `undefined symbol: rpl_malloc` | 交叉编译下 `AC_FUNC_MALLOC` 的运行探针无法执行，Autoconf 判定 malloc 损坏并把 `malloc` 重定向到 gnulib 的 `rpl_malloc()`，OHOS 不提供该符号 | configure 传 `ac_cv_func_malloc_0_nonnull=yes` |
| 6 | `make[1]: *** [Makefile:840: Makefile.conf] Error 1`（`Makefile.conf.in: No such file or directory`） | 上游 `Makefile.am` 的 `noinst_DATA` 规则用 `$@.in` 而非 `$(srcdir)/$@.in`，只在源码树内构建可行 | `patches/0004-vpath-makefile-conf.patch` |

### libtool archive staging（问题 4 的落地）

依赖包只读（Conan 缓存不可改写），因此 `generate()` 中：

1. 收集所有依赖 `cpp_info.libdirs` 下的 `*.la`，复制到 `<generators>/ohos-la-stage/`；
2. 把副本的 `libdir=''` 改写成该依赖真实的 lib 目录；
3. 重写 `dependency_libs`：命中依赖包的 `.la` → 指向 staging 副本；只剩 `.so` →
   改写为 `-L<dir> -l<name>`；两者都没有 → 丢弃（依赖包是共享库，自身 `DT_NEEDED` 已带依赖）；
4. 往每个生成 `.pc` 的 `Libs:`/`Libs.private:` 前置 `-L<staging>`，让 configure 烘进
   Makefile 的 `-L` 顺序里 staging 排在依赖目录之前，libtool 即优先命中改写过的副本。

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| `0001-config.sub-ohos.patch` | `config.sub` 接受 `*-linux-ohos` 三元组 |
| `0002-configure-tmpdir-mkdir.patch` | configure 生成 config.status 临时目录由 `mktemp -d` 改 `mkdir` |
| `0003-no-pthread-cancel.patch` | `src/scanbd/dbus.c`：`volatile bool dbus_thread_stop_requested` + dispatch 循环守卫，`dbus_start/stop_dbus_thread` 协作式退出；`src/scanbd/sane.c`：`sane_thread_t.stop_requested` + 轮询循环协作式退出，并移除 L26 `#define CANCEL_TEST` |
| `0004-vpath-makefile-conf.patch` | `Makefile.in`/`Makefile.am`：`Makefile.conf`/`Makefile.include` 规则改用 `$(srcdir)/$@.in` |

未纳入构建的源码：`src/udev.c`（`USE_LIBUDEV` 宏保护，已 `--disable-udev`）、
`src/scanbuttond_wrapper.c`（不在 Makefile.am 目标中）、`src/test/`（游离调试程序，不在 `AC_OUTPUT`）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| libconfuse | 3.3 | scanbd.conf 解析 |
| sane-backends | 1.2.1 | libsane（扫描仪后端） |
| dbus | 1.14.10 | scanbm 的 D-Bus 服务 |

## 上游测试清点（R51）

| 项 | 结果 |
|----|------|
| `tests/` 目录 | 无 |
| `test/` 单元测试框架 | 无（`src/test/` 是游离调试程序，未进 `AC_OUTPUT`/Makefile 目标，`./configure && make` 不构建它） |
| `make check` 目标 | 未定义（`AC_CONFIG_TESTDIR`/`TESTS` 均未使用，`make check` 不运行任何用例） |
| check_PROGRAMS | 无 |
| 结论 | 上游 1.5.1 无自动化测试；仅 `src/test/` 手工调试源码（本适配未纳入构建） |

因此 `test_package/` 采用消费者级验证：`test.sh` 断言三处**进程行为（退出码）**——
`command -v scanbd`/`scanbm` 解析成功；`-f -c <缺失配置>` → rc=1 的干净 EXIT_FAILURE；
未知选项 → rc≠0 且非 126/127（加载失败）。scanbd 经 syslog 记录日志、stdout 无输出，
故以退出码为证据，证明安装的 ELF 可加载且 libconfuse/libsane/libdbus 运行期可解析。
详见 `test_package/MANIFEST.yml`。`--version`/`--help` 不在断言范围内（上游 scanbd 未提供）。

## 验证结果

```
$ conan create . --build=missing -pr:h ohos-aarch64 -pr:b default
--- scanbd consumer verification ---
PASS 1: scanbd binary resolves -> <pkg>/bin/scanbd
PASS 2: missing config -> clean EXIT_FAILURE (rc=1) after startup
PASS 3: unknown option rejected (rc=1)
PASS 4: scanbm compatibility entry resolves -> <pkg>/bin/scanbm
test scanbd 1.5.1: 4/4 checks PASS
scanbd/1.5.1: Package '<pkgid>' created

$ python3 scripts/ohc-run.py finish scanbd 1.5.1 built   # Step 5/10 W3 本地 CI（阻塞门禁）
L0_RESULT=pass / L1_RESULT=pass: test_package executed
L2_RESULT=skip: scanbd version/help failed, scanbm failed
L4_RESULT=warn: dangerous functions in patches / L5_RESULT=pass: bin/ has content
━━━ Build Summary ━━━ Total: 1  Success: 1  Failed: 0  Pass rate: 100.0% (1/1)
```

> 用例 2/3 退出码 126/127 视为加载失败；rc=1 表示 ELF 在 OHOS 上成功加载并执行到
> scanbd 自身的启动/选项解析路径（libconfuse/libsane/libdbus 运行期可解析）。
> 用例 3 的实际观测值为 rc=1（选项解析失败路径），与 reports/w3-local-ci.log 一致。
> L2 冒烟为 skip：上游 scanbd/scanbm 不提供 `--version`/`--help`（非失败）。
> R40 说明：CI 仅覆盖二进制加载与配置/选项路径；真实扫描仪取图（sane 后端、libusb、
> udev/dbus 按键事件）无硬件环境未验证，需真机人工确认。
> 测试用例对比与上游清点详见 `reports/test-report.md`。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/scanbd` | 守护进程主程序（aarch64 PIE ELF，702 976 B） |
| `bin/scanbm` | 兼容入口（软链 → `scanbd`） |
| `etc/scanbd/scanbd.conf` | 默认配置 |
| `etc/scanbd/*.script` | 动作脚本（action / example / insert / scanadf / test） |
| `etc/scanbd/scanner.d/*.conf` | 厂商扫描仪配置（avision / canon / fujitsu / hp / pixma / plustek / snapscan） |
| `share/man/man8/scanbd.8`、`scanbm.8` | 手册页 |

`commands.json`（软件级）声明 `type: tool`、`ref: scanbd/1.5.1`（R38）。

## 注意事项

- OHOS 无线程取消：任何依赖 `pthread_cancel` 的上游代码都需要协作式改造，本包已处理 dbus.c/sane.c。
- `/system/bin/sh`（mksh）无法执行 ELF，`test_package` 用 `bash` 运行 `test.sh`。
- 上游 out-of-tree 构建不被官方支持（问题 6），后续版本升级需保留 `0004` 或推动上游修复合入。
---

**编译结束**: 2026-10-03 13:17
**最终状态**: built
