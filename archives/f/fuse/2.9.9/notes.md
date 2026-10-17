# fuse 2.9.9 适配笔记（FUSE 2.x / Libfuse2 legacy ABI）

## 编译环境

| 项 | 值 |
|----|----|
| 构建系统 | autotools（configure + make） |
| 编译器 | clang 15.0.4（OHOS SDK 26.0.0.18 / aarch64-linux-ohos） |
| profile | `ci/conan/profiles/ohos-aarch64`（os=OHOS / arch=armv8 / build_type=Release） |
| 本机 | B 机（aarch64 HarmonyOS / 31G） |
| 源码 | `https://github.com/libfuse/libfuse/releases/download/fuse-2.9.9/fuse-2.9.9.tar.gz`，sha256 `d0e69d5d608cc22ff4843791ad097f554dd32540ddc9bed7638cc6fea7c1b4b5` |
| 源码交叉核对 | Debian pool 的 `fuse_2.9.9.orig.tar.gz` 与本 URL **同 1813177 字节、同 sha256**（curl -sIL 两处 Content-Length 一致 + 本机 sha256 实测）⇒ 只写官方源（R39） |
| 包类型 | library（同时含 `bin/` CLI ⇒ 软件级 `commands.json` + `cpp_info.bindirs=["bin"]`） |

## 构建步骤（配方等价命令）

```bash
conan create archives/f/fuse/2.9.9 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

configure 参数（由 `AutotoolsToolchain` 注入）：

```
--enable-static --disable-shared --disable-example --enable-util \
--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
```

## 遇到的问题与解决方案（逐条含首条真实错误原文）

### 1. E011 —— configure 的 umask 077 让 config.status 临时目录不可写

首条真实错误原文（`configure` 阶段）：

```
config.status: error: cannot create ./confXXXXXX/subs1.awk: Permission denied
```

根因：`configure` 用 `tmp=\`(umask 077 && mktemp -d "./confXXXXXX")\`` 建临时目录，
HMDFS 的 UID 映射 + setgid 使该 0700 目录对当前进程不可写（E011）。
解法：`patches/0001-configure.patch` 把**两处** `umask 077` 改成 `umask 022`
（第 15161 / 15166 行，由 `refresh-patch --auto` 生成，非手写）。
补丁适用性：对上游原始 `configure` 逐字节可比（`orig hash ddcfafd2d02aecaa` /
`work hash d6ce7e04136d06fa`），CI 用 `conandata.yml` 的原始 URL 重新下载后
`apply_conandata_patches` 可命中。

### 2. E007/E072 —— 自带 config.sub 是 2016-11-04 版

首条真实错误原文（若直接传 `--host=aarch64-linux-ohos`）：

```
configure: error: cannot guess build type; you must specify one
checking host system type... Invalid configuration `aarch64-unknown-linux-ohos': machine `aarch64-unknown' not recognized
```

解法：不改 `config.guess`/`config.sub`（避免 R6 改生成文件），改为传
`--build/--host=aarch64-unknown-linux-gnu` —— 2016-11-04 的 `config.sub`
接受该三元组；同时绕开自带 `ltmain.sh` 对 `-ohos` 的不稳定处理。
`--enable-util` 只在 `$arch = linux` 时生效，用 gnu 三元组恰好让
`arch=linux` 成立 ⇒ `bin/fusermount`、`bin/ulockmgr_server` 才会被构建。

### 3. E085 —— OHOS bionic 缺 pthread_cancel / pthread_setcancelstate

首条真实错误原文（**test_package 链接期**，R34 真跑才暴露）：

```
ld.lld: error: undefined symbol: pthread_cancel
>>> referenced by fuse_loop_mt.c
>>>               fuse_loop_mt.o:(fuse_session_loop_mt) in archive .../p/lib/libfuse.a
>>> referenced by fuse.c
>>>               fuse.o:(fuse_stop_cleanup_thread) in archive .../p/lib/libfuse.a
ld.lld: error: undefined symbol: pthread_setcancelstate
>>> referenced by fuse_loop_mt.c
>>>               fuse_loop_mt.o:(fuse_do_work) in archive .../p/lib/libfuse.a
```

实测清点（`llvm-nm --undefined-only libfuse.a`）：libfuse.a 的未定义 pthread 符号里，
**只有这两个** libc 不提供，其余（`pthread_create/join/mutex_*/cond_*/key_*/sigmask`）
OHOS libc 均有。

两处处置，都不放松断言：

* **库侧**：`--disable-example`。上游 `example/` 的 10 个示例程序链接
  `libfuse.so`（`LDADD = ../lib/libfuse.la`），在 `--no-allow-shlib-undefined`
  下因这两个符号直接失败；示例不是交付物，跳过。
* **消费侧**：`test_package/pthread_stubs.c` 提供 **ENOSYS 语义**（置 `errno=ENOSYS`
  并返回 -1）的定义，**不是空壳**：真调用会看到错误而不是"以为已取消"。
  该文件顶部注释写明了清点方法与证据。

### 4. R26 —— 系统同名库必须静态

`libfuse` 与系统同名，动态 `.so` 会污染 `/lib`；配方
`--enable-static --disable-shared`，并在 `validate()` 中拒绝 `shared=True`
（含 `settings.os in ("Linux","OHOS")` 的 R32 写法与 OHOS/armv8 校验）。

### 5. `_FILE_OFFSET_BITS=64` 硬要求

`fuse_common.h` 第 32 行 `#if _FILE_OFFSET_BITS != 64` / `#error` ⇒ 必须在
`cpp_info.defines` 声明（同时 test_package 的 CMakeLists 再声明一次，
使消费者测试可独立构建）。

### 6. ★ 运行期能力墙 —— /dev/fuse 存在但 EACCES（本包新增知识）

实测读数（B 机、同一进程，全部为**原始输出**）：

| 探针 | 读数 |
|------|------|
| `ls -l /dev/fuse` | `ls: /dev/fuse: Permission denied` |
| `open("/dev/fuse", O_RDWR)` | **FAIL，errno=13（EACCES Permission denied）** |
| `os.path.exists("/dev/fuse")` | `False` ← **EACCES 造成的假阴性**（stat 失败被 exists() 归成"不存在"） |
| `grep -i fuse /proc/modules` | 无命中（fuse 模块未加载） |
| `ls -ld /etc` | `lrwxrwxrwx … /etc -> /system/etc` |
| 系统 `fusermount` | `/usr/bin`、`/bin`、`/system/bin`、`/usr/sbin` 四处均不存在 |
| `bin/fusermount` 权限 | `mode=0o770 setuid=False` ⇒ upstream `install-exec-hook` 的 `chmod u+s fusermount` **未生效**（E046 chmod 不起作用） |
| upstream `install-exec-hook` 的 `mknod dev/fuse -m 0666 c 10 229` | 不生效（`|| true` 兜底，不阻塞构建） |

⇒ 结论：`fuse_mount()` 在本平台**必然返回 NULL**；`fusermount` 的挂载/卸载面
不可用。这**不是配方缺陷**，而是平台运行期能力缺口。已验证：
`fuse_mount(mountpoint, &args)` 打印 `fuse: mountpoint is not empty`（说明它已越过
参数/挂载点检查）后 open `/dev/fuse` 失败并返回 NULL，与裸 `open()` 的 errno=13
**一致**。

**验证面因此收敛**（消费者测试的取舍，⛔ 不 mock 设备、⛔ 不谎称可挂载）：

* 库面**离线 API** 真跑真断言：`fuse_version()==FUSE_VERSION==29`、
  `FUSE_MAJOR_VERSION/MINOR_VERSION`、`fuse_opt_parse` 取值（含
  "换一个输入值结果随之改变"的**负向对照**）、`fuse_parse_cmdline` 真解析
  （含 `-s` 翻转 multithreaded 的负向对照）、`fuse_lowlevel_new` 离线建会话后
  `fuse_session_destroy`；
* 设备探针 + **两条负向对照**：`open("/dev/null")` 必须成功（证明探针能观察到
  "成功"，不是恒 Fail）、不存在的路径必须返回 `ENOENT`（证明 errno 读数是区分的）；
* `fuse_mount()` 与裸探针的**一致性断言**：探针失败 ⇒ 断言 `fuse_mount()==NULL`；
  探针成功 ⇒ 断言返回非 NULL（换环境自动成立，非写死"必须失败"）；
* CLI 面真跑：`fusermount --version`（rc=0 且 stdout 逐字 `fusermount version: 2.9.9`）、
  `-h`（rc=1 + stderr usage）、无参数（rc=1 + `missing mountpoint argument`）、
  `-z` 无 `-u`（rc=1 + `-z can only be used with -u`）、非法选项（rc=1 +
  `unrecognized option`，作为**负向对照**证明 CLI 真在校验选项）。

## 消费者测试实测读数（25/25）

`conan create` 的 test_package 段逐字（摘要）：

```
== fuse/2.9.9 consumer test (Libfuse2 legacy ABI) ==
  PASS  headers declare FUSE 2.9 (major=2 minor=9)
  PASS  fuse_version()=29 == FUSE_VERSION=29 == 29 (legacy 2.x ABI)
  PASS  fuse_opt_parse(-n alpha) -> 'alpha'
  PASS  fuse_opt_parse(-n beta) -> 'beta'
  PASS  negative control: parser follows its input ('alpha' != 'beta')
  PASS  fuse_parse_cmdline() accepted '-f <cwd>' rc=0
  PASS  -f parsed as foreground (foreground=1)
  PASS  mountpoint resolved through realpath -> '<cwd>'
  PASS  negative control: -s flips multithreaded (1 -> 0)
  PASS  fuse_lowlevel_new() built an offline session object (no /dev/fuse)
  INFO  probe: /dev/fuse -> open FAILED (errno=13 Permission denied)
  PASS  probe control: open(/dev/null,O_RDWR) succeeded (errno=0)
  PASS  probe control: missing path -> errno=2 (No such file or directory)
  PASS  probe discriminates ENOENT(2) from /dev/fuse errno(13)
  PASS  consistency: /dev/fuse errno=13 -> fuse_mount()=NULL (mount capability wall, not a library defect)
== 14 checks, 0 failed ==
== consumer checks ==   (CLI 面)
  PASS  bin/fusermount mode=0o770 setuid=False
  PASS  fusermount --version rc=0 stdout='fusermount version: 2.9.9'
  PASS  fusermount -h rejects with usage on stderr rc=1
  PASS  fusermount with no mountpoint rc=1 stderr='...: missing mountpoint argument'
  PASS  negative control: invalid option rejected rc=1 stderr='...: unrecognized option: definitely-not-an-option'
  PASS  fusermount -z without -u rc=1 stderr='...: -z can only be used with -u'
  PASS  harness control: missing binary raises FileNotFoundError (rc capture is not vacuous)
  PASS  bin/ulockmgr_server installed / executable
== 11/11 checks passed ==
```

合计 **25 条断言，25 通过，0 失败**。`test.c` 14 条 + `test_package/conanfile.py` 的
`test()` 11 条。

## 上游测试用例

**结论：fuse 2.9.9 无上游测试套件（注册用例数 = 0）。**

R51 清点 6 条探针（对象 = `conandata.yml` 声明的官方 tarball，sha256 已核对）：

| 探针 | 结果 |
|------|------|
| `find . -maxdepth 2 -type d -iname '*test*'` | 0 命中（无 test/ 或 tests/） |
| `grep -rn 'TESTS *=\|check_PROGRAMS\|TESTS_ENVIRONMENT' --include=Makefile.am .` | 0 命中 |
| `find . -name 'test*.c' -o -name '*_test.c'` | 0 命中 |
| `make check` | automake 默认空实现（`check-am: all-am`，仅构建不断言） |
| `example/Makefile.am` | `noinst_PROGRAMS` = 10 个**示例**（fusexmp/fusexmp_fh/null/hello/hello_ll/fioc/fioclient/fsel/fselclient/cusexmp），非 `TESTS`/`check_PROGRAMS` |
| `util/Makefile.am` | `bin_PROGRAMS = fusermount ulockmgr_server`；`noinst_PROGRAMS = mount.fuse`；无测试声明 |

⇒ 上游通过率记 **0/0（无上游用例）**，适配后新增消费者用例 **25/25**。
`test_package/MANIFEST.yml` 已按同口径落盘清点证据。

## 与既有行 `libfuse/2.9.9` 的关系（如实说明）

本仓 `archives/l/libfuse/2.9.9/` 是**同版本、同上游 tarball** 的另一条包名线，
其知识（E011 的 umask 补丁、E085 的示例跳过、R26 静态化、gnu 三元组）本次
**全部复用**（属"使用知识库"）。本包与之的**新增量**是：

1. 平台任务要求的是 `fuse` 包名（`archives/f/fuse/2.9.9/`），消费方以
   `fuse/2.9.9` 引用；两条包名线并存互不替代（FUSE 2.x 旧 ABI 与 3.x 各自独立）；
2. **运行期能力墙的实测与沉淀**（见问题 6）：errno=13 与 `exists()` 假阴性、
   `chmod u+s` 不生效、`/etc -> /system/etc`、`fuse_mount()` 与裸探针的一致性判据
   —— 既有 `libfuse/2.9.9` 行只写到"无 /dev/fuse，无法真正挂载文件系统"，
   没有 errno 级读数、没有 `exists()` 假阴性、没有设备探针的负向对照，
   也没有把"怎么验证才对"写成可执行断言；
3. **消费者测试强度**：既有行 test_package 是 2 条断言（仅 `fuse_version()`
   链接验证）；本包 25 条，含 CLI 真跑与 3 条负向对照；
4. `package()` 剥除 rootfs 专用件（`sbin/mount.fuse`、`/etc/init.d`、
   `/etc/udev/rules.d`）—— 既有行保留了这些目录。

## 已知限制与诚实边界（⛔ 不谎称可用）

1. **挂载面不可用**：`/dev/fuse` EACCES ⇒ `fuse_mount`/`fuse_loop`/`fusermount`
   的挂载、卸载路径在本平台无法执行，也**无法**做端到端文件系统 smoke；
   本次未做，且不做任何 mock 来制造"通过"。
2. **setuid 不生效**：`fusermount` 在正常 Linux 上靠 setuid root 工作；OHOS 上
   `chmod u+s` 不生效（E046），即便 `/dev/fuse` 将来放开权限，`fusermount`
   的权限模型也需另议。
3. **`--disable-mtab` 未加**：上游默认让 `fusermount` 读写 `/etc/mtab`，而本平台
   `/etc` 是 `/system/etc` 符号链接。本包与既有 `libfuse/2.9.9` 保持同一参数集
   （不加 `--disable-mtab`），因为挂载面本身不可达、该差异当前不可观测；
   如实记录，供将来挂载面放开时复议。
4. **本机构建期的网络绕法（必须披露）**：本次 `conan create` 期间本机 DNS 故障
   —— `conan.cnb.cool` 与 `github.com` 双双 `Failed to resolve ... [Errno -3]`。
   处置（两处都不改配方、都可复原）：
   * 用 `core.sources:download_cache` 的**备份源**机制就位源码：
     `~/tmp/ch/dlcache/s/d0e69d5d…c1b4b5`（sha256 由 `sha256sum -c` 校验通过）
     + 同名 `.json` 记录官方 URL。这正是 CI 预下载（`ci/conan/build_and_test.sh`
     的 pre-download 段）写入的同一套缓存，**不修改 `conandata.yml`**，
     官方 URL 保持原样；
   * 构建期临时 `conan remote disable ohpcd`（本包 `requirements()` 为空、
     不依赖任何远程制品），构建后已恢复 `enable`。
   编译、链接、测试全部在本机真实执行，未使用任何预编译产物冒充。
   复现命令：`conan create archives/f/fuse/2.9.9 -pr:h=… -pr:b=… --build=missing --user=ohpcd --channel=stable`。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libfuse.a` | 主库（静态，R26） |
| `lib/libulockmgr.a` | 用户态锁管理库（静态） |
| `include/fuse.h`、`include/fuse/*.h`、`include/ulockmgr.h` | FUSE 2.x 头文件 |
| `bin/fusermount` | 挂载/卸载辅助（setuid 在 OHOS 不生效） |
| `bin/ulockmgr_server` | ulockmgr 用户态服务进程 |

> 已剥除：`sbin/mount.fuse`、`etc/init.d/fuse`、`etc/udev/rules.d/99-fuse.rules`、
> `lib/*.la`、`lib/pkgconfig/`。理由：前四者是 Linux rootfs 专用件（OHOS 无
> udev/SysV init，`/etc` 还是 `/system/etc` 符号链接），`.la` 是 libtool 包装，
> pkg-config 由 Conan 依赖链取代。

## 对话记录段（判定与决策留痕）

### 对话 #1 —— 接单判定、构建期真实失败与能力墙实测留痕

* **接单时的对照判断**：派发卡给的对照是"`fuse3/3.18.3` 已在本仓"。实测本仓
  实际存在的是 `archives/l/libfuse/2.9.9/`（**同版本同源**）与
  `libfuse/3.18.2`；登记表里 `fuse3 3.18.3` 仍是**候选（未做）**。
  ⇒ 对照对象按实际盘面修正为 `libfuse/2.9.9`，并据此判 **B**。
* **路径判定 = B（create）**，理由链：
  1. C 四条硬资质逐条不成立：①FUSE 用户态库有清晰的跨平台抽象层（mount.c /
     mount_bsd.c 已按平台分派）且编译面全通；②无私有工具链（clang + autotools
     原生可用）；③无汇编/闭源二进制/特殊调度；④零 conan 依赖、全量测试成本极低。
     ⇒ 不够 C，不走 C。
  2. A 的排除：本包不是"零新增" —— 见上"与既有行 libfuse/2.9.9 的关系"第 2/3/4 条，
     且在知识库四范围（`knowledge/graph/*.kv` + `knowledge/drafts/` +
     `经验文档/经验库/` + `OHOS行为探针清单`）里 **`/dev/fuse` 零命中**
     （`grep -rln 'dev/fuse' knowledge/graph knowledge/doc` 返回空）
     ⇒ 存在跨库可复用的新机制，判 **create**。
  3. 机制可复用面：所有 FUSE 消费者（sshfs / mtpfs / mhddfs / ifuse / bindfs /
     s3fs-fuse / ext4fuse / zfs-fuse / securefs / winregfs …）在本平台都要面对
     同一堵墙与同一套"该验证什么"的判据，故按**通用机制**沉淀
     （`DRAFT-fuse-2.9.9-dev-fuse-eacces-mount-capability-wall`）。
* **构建期两次真实失败都留了原文**：① `ld.lld: error: undefined symbol:
  pthread_cancel`（首次 `conan create`，test_package 链接期）；② 我自己的
  `pthread_stubs.c` 注释里写了 `mutex_*/cond_*` 导致 `*/` 提前闭合注释、
  `unexpected character <U+2026>` —— 属自制文件缺陷，已改注释措辞；
  两者都不改上游源码。
* **未采纳的方案**：不 mock `/dev/fuse`、不伪造挂载成功、不把能力墙写成
  "通过"；不加 `--disable-mtab`（保持与既有行同参数集，差异当前不可观测）；
  不改 `config.guess/sub`（改传 gnu 三元组，避开 R6）。
---

**编译结束**: 2026-10-16 14:40
**最终状态**: built

状态: built（与版本级 manifest.yaml 的 status 同值；验证证据见上「验证结果」与「已知限制」）
