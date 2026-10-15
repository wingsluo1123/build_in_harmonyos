# berkeley-db 18.1.40 适配笔记

## 编译环境
- 构建系统: autotools（须在 build_unix/ 子目录运行 ../dist/configure）
- 编译器: clang（OHOS aarch64 工具链）
- 目标平台: HarmonyOS OHOS aarch64（conan profile ohos-aarch64）
- 状态: built

## 编译步骤

```bash
cd build_unix && SHELL=sh sh ../dist/configure --prefix=/ --enable-static --enable-shared \
    --with-repmgr-ssl=no --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
sh ./config.status
make -j1
make install DESTDIR=<conan package_folder>
```

说明：以上步骤由 conanfile.py 的 build() 编排（改写 dist/configure 与 config.status 后，config.status 手动执行），
最终以 `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64` 一键完成。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 无法识别 OHOS/HarmonyOS 平台 | 上游自带版本过旧 | 免补丁路线：显式传 `--build/--host=aarch64-unknown-linux-gnu`（berkeley-db 4.8.30 已实证），无需 5.3.28 的 config.guess/config.sub 替换补丁 |
| 2 | configure 探测 `print -r --` 成功，但 config.status 执行环境无 print，回显空串 | HMDFS 下探测 shell 与执行环境不一致 | 构建时改写 dist/configure：8 处 `print -r --`、2 处 `print -rn --` 强制为 POSIX `printf %s\n` / `printf %s` 回显 |
| 3 | config.status 生成临时 awk 脚本报 Permission denied（subs1.awk） | config.status 临时目录默认 `umask 077`，新建的 2700+setgid 目录被 HMDFS 拒绝写入 | 反激活 configure 末尾的 config.status 自动执行行（dist/configure L27743）；改写 config.status：mktemp 行改 `$TMPDIR/conf$$-$RANDOM`、`umask 077 && mkdir` 改 `umask 022 && mkdir -p`、兜底 umask 077→022；随后手动 `sh ./config.status` |
| 4 | make 首条规则即失败：`./libtool: Permission denied`（126） | OHOS 内核无 binfmt_script，make 直接 execve 顶层 `./libtool`（`#!` 脚本、shebang 指向 hnp bash）恒被拒 | 双保险：config.status 内把 `S["LIBTOOL"]` 替换为 `sh ./libtool`（生成 Makefile 时生效）；config.status 跑完后对 Makefile 做 `^(LIBTOOL=)(\s*)\./libtool` → `sh ./libtool` 正则兜底 |
| 5 | 链接/安装规则 `ln: cannot create symbolic link from '.libs/libdb-18.1.a' to 'libdb.a'` | HMDFS 全盘拒绝 symlink(2)（EPERM）；Makefile 有 23 处 `$(LN) -s` 生成便利名 | Makefile 中 `$(LN) -s ` 统一改写为 `cp -f `（libtool 自身 LN_S 已被 configure 统探测为 `cp -pR`，无需处理） |
| 6 | 装出的 db_* 工具在设备上全部 126（Permission denied） | install_utilities 逐个执行 `$(STRIP)`（llvm-strip），剥离了 OHOS clang 链接时自动注入的 .codesign 段（27008B 签名件→10104B 未签名件），设备内核拒执未签名 ELF | Makefile 中禁用该 strip 行（`$(STRIP) $(DESTDIR)$(bindir)/$$e;` → no-op）；对照：未 strip 的 .libs 原件可直执且 `db_archive -V` 正常输出 |
| 7 | install_docs 报 `cp: bad 'bdb-sql'` / `cp: bad 'gsg_db_server'` | DOCLIST 两个成员在上游 tarball 里是符号链接，HMDFS 解包时被跳过不落盘 | DOCLIST 剪枝这两个 token |

## 上游测试清点（R51 申报表）

解包上游 tarball（db-18.1.40.tar.gz，sha256 0cecb2ef…da9c8）对 test/ 全树递归计数：

| 子目录 | 文件数 | 可运行性 | 技术原因 |
|--------|--------|----------|----------|
| test/c | 29 | ✅ 部分 | CuTest 套件（13 套件：83 个 Test* 函数、注册用例 55 个）经 `make cutest` 可运行；chk.ctests 遗留脚本需 `--enable-compat185` 独立全量重建静态库（平台构建配置外） |
| test/cxx | 21 | ❌ | 需 C++ 绑定（`--enable-cxx`，平台构建默认 no） |
| test/tcl | 558 | ❌ | 553 个 .tcl、155 文件含 252 个 test proc；需 Tcl 解释器 + `--enable-tcl` |
| test/java | 133 | ❌ | 需 JDK + `--enable-java` |
| test/csharp | 56 | ❌ | 需 .NET/mono 工具链 |
| test/xa | 29 | ❌ | chk.xa 首检 `$TUXDIR`（Oracle Tuxedo 商业中间件），设备无 |
| test/micro | 26 | ❌ | 性能基准框架，非断言型测试 |
| test/db_guitest | 8 | ❌ | Java Swing GUI（无头设备不可行） |
| test/utils | 2 | ❌ | 辅助脚本 |
| test/tcl_utils | 1 | ❌ | Tcl 辅助脚本 |
| **合计** | **863** | | |

- 上游无 `make check`：dist/Makefile.in L1367 `check depend dvi info obj TAGS:` → L1368 统一回显
  "make: $@ target not available"（无 exit 1，非失败；对照 L1370 dist/rpm/rpmbuild 才是 exit 1）。
- 选定上游测试命令（`upstream_check_command`）：`make cutest && ./cutest`
  （test/c/README：POSIX 下 `make cutest` 构建，在 build_unix 目录 `./cutest` 运行）。
- CuTest 13 套件（test/c/suites/*.c，按 `^int Test` 函数计数共 83 个）：
  TestEnvConfig 16、TestDbHotBackup 12、TestEncryption 12、TestPartition 11、
  TestPartial 8、TestPreOpenSetterAndGetter 8、TestCallbackSetterAndGetter 6、
  TestChannel 5、TestDbTuner 1、TestEnvMethod 1、TestKeyExistErrorReturn 1、
  TestMutexAlignment 1、TestQueue 1。
  其中注册为 CuTest 用例、`./cutest` 实际执行的是 **55 个**（真机 `OK (n tests)`
  实测：2+1+8+1+12+12+1+1+1+4+7+4+1），其余为测试文件内辅助函数。

## 验证结果

真机（HarmonyOS aarch64，profile ohos-aarch64）实测：

- **conan create**：退出码 0 —— 从源码完整构建（configure→config.status→make→install→打包）＋消费者测试全绿；
  test_package 3 用例 15 断言 `TEST SUMMARY: 15 checks, 0 failed -> ALL PASS`，
  其中 `db_version()` 返回 banner 实证 `Berkeley DB 18.1.40: (May 29, 2020)`。
- **上游 CuTest（13 套件；注册用例 55 个）**：出厂构建（clang -O3）逐套件执行 12 套件全绿——
  CallbackSetterAndGetter 2/2、Channel 1/1、DbHotBackup 8/8、DbTuner 1/1（内含 db_tuner 96/96）、
  Encryption 12/12、EnvConfig 12/12、EnvMethod 1/1、KeyExistErrorReturn 1/1、
  MutexAlignment 1/1（24 组 system() 全部返回 0）、Partial 4/4、Partition 7/7、PreOpen 4/4。
  TestQueue 在 -O3 下首个 shim 用例（sh_list）即触发 SIGTRAP；-O3 整套连跑亦在 TestPartial 输出
  OK 后触发同源 trap（TestPartial 独立单跑 4/4 全过）——**上游测试代码在 clang -O3 下的未定义
  行为被优化为 trap 指令（重编仅涉及测试 TU，库本体二进制未动）**；将 TestQueue.c 单 TU 以 -O0
  复建后 136/136 子用例全过（sh_list 68/68、sh_tailq 68/68）；测试脚手架整体 -O0 复建后
  13 套件一套连跑全绿（归档 rc=0）。
- **工具冒烟**（真机实测）：`db_load -T -t btree`→RC=0；`db_verify`→"BDB5105 Verification of smoke.db succeeded."RC=0；
  `db_dump -p`→RC=0（键值逐字节回读一致）；`db_dump -V`→"Berkeley DB 18.1.40: (May 29, 2020)"；
  `db_stat -d` 正常读出 Btree 头（magic 53162 / 页 4096 / 小端）。
- **ELF 核验**（真机 llvm-readelf）：`libdb-18.1.so`=ELF64/DYN/AArch64 + GNU_RELRO + GNU_STACK NX +
  DT_NEEDED 仅 `libc.so`；`db_dump` INTERP=`/lib/ld-musl-aarch64.so.1`。
- **conan-verify**：✅ PASS（rc=0）——G1/G0/G2/G3/G4 全 ✅（G2 以本配方干净重建全绿；G0 热点 E490 的 autotools 脚本执行位提示经实测未致失败），L2/L4/L5 按设备常态跳过（无 cache 路径）；报告 reports/conan-verify-report.md；里程碑 conan_verify_passed

```bash
# conan create（含 test_package 消费者测试：db_version/db_create/db->open(内存态 Btree)/put/get/del，15 断言）
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64

# 上游 CuTest（build_unix 目录；全套连跑）
make cutest && ./cutest

# conan-verify（G1/G0/G2/G3/G4 + L2/L4/L5）
ohc-run.py conan-verify berkeley-db 18.1.40
```

## 注意事项

- 交付 15 个 db_* 命令行工具（bin/，package_info 已声明 bindirs=["bin"]）：
  db_archive db_checkpoint db_convert db_deadlock db_dump db_hotbackup db_load
  db_log_verify db_printlog db_recover db_replicate db_stat db_tuner db_upgrade db_verify。
  18.1.40 相对 5.3.28：新增 db_convert，移除 db_sql（后者仅 4.8.30/5.3.28 线交付）。
- 库文件 libdb-18.1.so / libdb-18.1.a；头文件 db.h / db_cxx.h。
- HMDFS 改写仅作用于构建期的 dist/configure 与 config.status 副本，不改动上游 tarball 本身。
- 本包与既有 berkeley-db4(4.8.30)、berkeley-db5(5.3.28) 并存，命令注册见软件级 commands.json。
---

**编译结束**: 2026-10-14 12:17
**最终状态**: built
