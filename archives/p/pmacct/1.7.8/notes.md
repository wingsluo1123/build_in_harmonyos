# pmacct 1.7.8 适配笔记

## 编译环境

- 构建系统: autotools（上游 tag 归档不含 `configure`，需 autoreconf 自举）
- 编译日期: 2026-10-08
- 编译器: clang 15.0.4 / clang++（OHOS SDK 26.0.0.18）
- 目标平台: aarch64-unknown-linux-ohos（OHOS / HarmonyOS PC）
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 依赖: `libpcap/1.10.6`（静态）；vendored `libcdada 0.4.0`
- 状态: built

## 编译步骤

### 对话 #1 [2026-10-08]

- 问题: 上游 v1.7.8 的 GitHub archive tarball 里**没有 `configure`**（git 树快照），直接
  `./configure` 报 not found
- 操作: `build()` 内先 `autoreconf -f -i -I m4` 自举；`-I m4` 不可省，因为
  `configure.ac` 用到的 `AC_LINEARIZE_PATH` 宏只在源码树 `m4/ac_linearize_path.m4`
- 结果: configure 生成成功（`[autoreconf] configure 已生成`）

### 对话 #2 [2026-10-08]

- 问题: 自举后 configure 报 `unable to guess system type`（config.guess 不认识设备
  `uname -s = HarmonyOS`）
- 操作: 显式传 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`
  （同 profile 下 conan 不会自动补三元组，见"问题 #2"）
- 结果: configure 顺利通过，`checking whether we are cross compiling... no`

### 对话 #3 [2026-10-08]

- 问题: 首次跑 `autoreconf` 时 `aclocal` 崩：`Can't load .../auto/Cwd/Cwd.so:
  Error relocating ...: Perl_my_cxt_init: symbol not found`（rc=255）
- 操作: 定位为 conan perl 5.42.2 与 hnp perl 5.42.0 的 XS 模块 ABI 不兼容；写 perl shim
  把 `aclocal`/`automake` 显式指向 conan perl，并在 autoreconf 命令行层内联 PATH 前缀
  （`ACLOCAL=<shim> AUTOMAKE=<shim> PATH=<tool_bins>:...`）
- 结果: 全链 perl 统一为 conan perl 5.42.2，autoreconf 通过

### 对话 #4 [2026-10-08]

- 问题: 编译到 8 个 daemon 源文件时报
  `error: use of undeclared identifier 'M_CHECK_ACTION'`（`-Werror` 下为硬错）
- 操作: OHOS/musl 的 `malloc.h` 有 `mallopt()` 但无 `M_CHECK_ACTION`，而
  `AC_CHECK_FUNCS(mallopt)` 会置上 `HAVE_MALLOPT` ⇒ 把
  `#if defined HAVE_MALLOPT` 加宏守卫为 `#if defined HAVE_MALLOPT && defined M_CHECK_ACTION`
  （8 文件各 1 处，形成补丁 `0001-mallopt-m-check-action-guard.patch`）
- 结果: make 全量通过，无 `error:`

### 对话 #5 [2026-10-08]

- 问题: `src/external_libs/libcdada` 是 git submodule，制品仓未发布；tarball 里只是空目录
- 操作: 在 `source()` 里按 pmacct `.gitmodules` 声明的官方仓库 + submodule 固定 commit
  (`4eb0b613efa080596f38a5e66caaf4accb97d06e`) vendored 解包进该目录；其余交给上游
  自带的 submodule 构建系统（configure 默认 `--with-external-deps=yes`）
- 结果: libcdada 就地编译为静态库并装到 `<build>/src/external_libs/rootfs`，
  `nfacctd -V` 显示 `cdada 0.4.0`

### 对话 #6 [2026-10-08]

- 问题: 上游 `configure.ac:1220` 硬编码 `LIBS="-lcdada -lstdc++ ${LIBS}"`，而设备上
  找不到 libstdc++
- 操作: 实测 OHOS clang 15.0.4 的 C 与 C++ driver 都把 `-lstdc++` 归一化为 libc++
  （`clang -lstdc++` 链接行出现 `-lc++ -lc++abi -lunwind`，rc=0）⇒ **无需补丁**
- 结果: 链接正常，`readelf -d` 显示 nfacctd 仅 NEEDED `libc++_shared.so` + `libc.so`

### 对话 #7 [2026-10-08]

- 问题: 上游把 6 个守护进程装到 `sbin/`、只有 `pmacct` 在 `bin/`
- 操作: `package()` 内折叠 `sbin/` → `bin/`（同 accel-ppp/1.14.0 先例）
- 结果: 7 个可执行文件全部落在 `bin/`，加 install 假绿防护（逐个核实物）

### 对话 #8 [2026-10-08]

- 问题: 上游没有自动化测试套件，需要确认"上游测试入口"到底是什么
- 操作: 全树 grep `TESTS`/`check_PROGRAMS`/`check-local` 均 0 命中、无 `tests/` 目录
  ⇒ `make check` 无目标；真实入口是 `ci/script.sh`（`ls -l src/nfacctd` +
  `src/nfacctd -V`）与 `ci/smoke-test/docker-compose.yml`（需 docker）
- 结果: `build()` 内逐字复现 `ci/script.sh` 的测试段并断言版本行含
  `cdada`/`libpcap version`/`clang`；docker smoke-test 登记不执行（沙箱无 docker）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tarball 无 `configure` | GitHub archive 是 git 树快照，configure 是 autoreconf 产物、不进版本库 | `build()` 内 `autoreconf -f -i -I m4` 自举 |
| 2 | `unable to guess system type` | 同 profile 下非 cross build ⇒ conan 不补 `--build`/`--host`；设备 `uname -s=HarmonyOS` 不被 config.guess(2024-07-27) 识别 | 显式传 `--build`/`--host=aarch64-unknown-linux-ohos` |
| 3 | `Perl_my_cxt_init: symbol not found` | conan perl 5.42.2 与 hnp perl 5.42.0 的 XS 模块 ABI 不兼容；automake/1.18 的 `.aclocal-real`/`.automake-real` shebang 写死 hnp perl，profile `[buildenv] PATH` 又让 hnp/bin 优先 | perl shim 把 aclocal/automake 指向 conan perl + 命令行层内联 PATH 前缀 |
| 4 | `use of undeclared identifier 'M_CHECK_ACTION'` | OHOS/musl `malloc.h` 有 `mallopt()` 但无 `M_CHECK_ACTION`，`AC_CHECK_FUNCS(mallopt)` 照样置 `HAVE_MALLOPT` | 补丁 `0001-mallopt-m-check-action-guard.patch`：宏守卫加 `&& defined(M_CHECK_ACTION)` |
| 5 | libcdada submodule 空目录 | submodule 内容不进 tarball，制品仓也无 libcdada | vendored 官方仓库 + 固定 commit 源码，交给上游 `--with-external-deps=yes` 机制就地编译 |
| 6 | 找不到 libstdc++ | 上游硬编码 `LIBS=-lstdc++`，但 OHOS 工具链无 libstdc++ | 无需处理：实测 OHOS clang 把 `-lstdc++` 归一化为 `-lc++` |
| 7 | 守护进程装到 `sbin/` | 上游 install 约定 | `package()` 折叠 `sbin/` → `bin/` |
| 8 | `make check` 无目标 | 上游无自动化测试套件 | 复现 `ci/script.sh` 测试段；登记 docker smoke-test |

## 源码修改

唯一补丁：`patches/0001-mallopt-m-check-action-guard.patch`（8 文件 x 1 处）

```diff
-#if defined HAVE_MALLOPT
+#if defined HAVE_MALLOPT && defined M_CHECK_ACTION
   mallopt(M_CHECK_ACTION, 0);
```

涉及文件：`src/nfacctd.c`、`src/plugin_hooks.c`、`src/pmacctd.c`、`src/pmbgpd.c`、
`src/pmbmpd.c`、`src/pmtelemetryd.c`、`src/sfacctd.c`、`src/uacctd.c`。
补丁为纯可移植性守卫（no-`__OHOS__` 守卫，R8/PF5 合规），不改变任何平台行为分支。

## 依赖版本

| 依赖 | 版本 | 角色 | 来源 |
|------|------|------|------|
| libpcap | 1.10.6 | 抓包后端（`configure.ac` 硬门禁） | 制品仓（静态 `.a`） |
| libcdada | 0.4.0 | BGP/BMP 数据结构（上游 git submodule） | vendored（官方仓库固定 commit） |
| autoconf | 2.72 | autoreconf 自举 | 制品仓（tool_requires） |
| automake | 1.18 | autoreconf 自举 | 制品仓（tool_requires） |
| libtool | 2.5.4 | libtoolize / ltmain.sh | 制品仓（tool_requires） |
| perl | 5.42.2 | aclocal/automake 解释器（经 autoconf 传递引入） | 制品仓（tool_requires） |

## 验证结果

```bash
# 上游测试入口（逐字复现上游 ci/script.sh 的测试段）
$ ls -l src/nfacctd
-rwxr-xr-x 1 ... 2964032 src/nfacctd
$ src/nfacctd -V
cdada 0.4.0
libpcap version 1.10.6 (64-bit time_t, with TPACKET_V3)
Compiler: clang-15.0.4
Build system: aarch64-unknown-linux-ohos
...
OK, Exiting ...  (rc=0)

# 消费者端到端用例（test_package/test_pmacct.py）
$ python3 test_pmacct.py <package_folder>
PASS A1 七个可执行文件齐备且可执行
PASS A2 七个二进制 -V 全部 rc=0
PASS B1 nfacctd -V 含 cdada
PASS B2 nfacctd -V 含 libpcap 版本
PASS B3 nfacctd -V 含 clang 编译器指纹
PASS C1 构造离线 pcap (258 bytes = 24 + 3*(16+62))
PASS C2 pmacctd 消费 pcap 退出码为 0
PASS C3 CSV 表头正确
PASS C4 flow A 聚合 10.0.0.1,10.0.0.2,12345,80,4,192
PASS C5 flow B 聚合 10.0.0.3,10.0.0.2,53,53,2,96
===== 总 10 / 通过 10 / 失败 0 =====
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/pmacct` | 在线/离线 pcap 流量统计前端 |
| `bin/pmacctd` | 基于 libpcap 的链路层流量统计守护进程 |
| `bin/nfacctd` | NetFlow/sFlow/IPFIX 收集守护进程 |
| `bin/sfacctd` | sFlow 收集守护进程 |
| `bin/pmtelemetryd` | 流式遥测收集守护进程 |
| `bin/pmbgpd` | BGP 监控守护进程 |
| `bin/pmbmpd` | BMP 监控守护进程 |
| `share/pmacct/` | 上游文档（CONFIG-KEYS/FAQS/QUICKSTART…）与 examples |

## 注意事项

- **uacctd 未构建**：上游第 8 个守护进程由 `WITH_NFLOG` 条件控制
  （`src/Makefile.am:162-166`），需 `libnetfilter_log`；制品仓未发布该包。
- **插件不是 `.so`**：pmacct 的 `plugins:` 是进程内字符串选择，插件对象静态编入各
  daemon，因此包内没有 `.so` 产物，消费方也不需要 `LD_LIBRARY_PATH`。
- **无系统同名库冲突面**：本包不产出任何 `.so`，不涉及 R26/R4 静态化问题。
- **libcdada 随包 vendored**：制品仓没有 `libcdada`，如需单独复用需另行适配；
  本包已静态编入，消费方无需额外依赖。
- **`--enable-debug` 未启用**：会额外加 `-Werror`，历史上是本补丁的触发面；
  本版本走补丁修复而非关掉 `-Werror`。

---

**编译结束**: 2026-10-08

状态: built
---

**编译结束**: 2026-10-09 00:41
**最终状态**: built
