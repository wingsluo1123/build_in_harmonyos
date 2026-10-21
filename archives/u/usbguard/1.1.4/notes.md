# usbguard 1.1.4 适配笔记

## 任务来源

- 平台任务 11561（claimer=Ember5843，status=assigned），分支 `feat/usbguard-1.1.4`，
  本地卡 `t_usbguard11561`，worktree `/storage/Users/currentUser/worktrees/deliver-usbguard-1.1.4`（HEAD 7d1f961b7）。
- 上游：github usbguard/usbguard，tag `usbguard-1.1.4`（commit f22233175f7a4539bc96ede8e3d67f7017b6675b），
  tarball sha256=`607c811fb65260634a6c3f58efb6351c9be36216eb4f4483a4606e744aefc5ec`。
- 语言实测（R47 lang-preflight）：**C++**（177 个 .cpp，autotools；平台 lang 字段一致）。

## 选库核验

- main 档案无 usbguard（精确+模糊）；ohpcd `usbguard/1.1.4` 不存在；同版本无他人 claim。
- 认领核验包：`~/tmp/ohpc-porting/claim-recon-2-20261015-1/usbguard/`（gate.json 五项 source_version /
  cpp_language / no_duplicate / dependencies / delivery_capacity 全 pass，含 sha256）。
- 依赖（ohpcd 均有制品）：libqb/2.0.10、libsodium/1.0.22、protobuf/3.17.3（含 protoc）、
  automake/1.18、libtool/2.5.4、m4/1.4.19。

## 关键适配点（按遇到顺序）

| # | 现象 | 根因 | 处置 |
|---|------|------|------|
| 1 | `conan create` 图解析失败：`Conflict between zlib/1.3.1 and zlib/1.3.1.1` | protobuf/3.17.3 钉 zlib/1.3.1，libqb → glib/2.84.0.1 钉 zlib/1.3.1.1 | 配方 `self.requires("zlib/1.3.1.1", override=True)`（zbackup 1.5 先例） |
| 2 | `configure: error: cannot guess build type` | config.guess 用 `umask 077 && mktemp -d`，hmdfs 下生成 `drwx--S---` 目录不可写 → 无法编译探测程序 | 配方在 autoreconf 后把生成脚本里的 `umask 077` 一律改 022（configure + config/config.guess，E114/E011；0 命中即报错） |
| 3 | 仍 `cannot guess build type` | `uname -s` = HarmonyOS，config.guess 无匹配分支 | 铁律 R1 禁止 `--build/--host`，故在 autoreconf 后教 config.guess 识别 HarmonyOS（`UNAME_SYSTEM=Linux`），得到与其它配方显式传入相同的 `aarch64-unknown-linux-gnu` |
| 4 | 所有 TU `error: expected unqualified-id`（`../version:1:1`，内容 1.1.4） | 用户卷大小写不敏感，源码根 `VERSION` 文件遮蔽 libc++ 的 `<version>` 头（gadap/libodb-pgsql 同类问题） | 补丁 0001–0003：删除 `VERSION`，`configure.ac` 用字面量版本，`Makefile.am` 去掉 EXTRA_DIST 引用 |
| 5 | `redefinition of 'sockaddr_storage'`（sys/socket.h ↔ linux/socket.h） | OHOS sysroot 两个头都定义该结构；usbguard 同一 TU 同时引入 `<linux/netlink.h>` 与 `<sys/socket.h>` | `-D__MUSL__`（E119；sysroot 中仅 sys/socket.h 引用该宏，影响面窄；agetty/aircrack 先例） |
| 6 | 4 个上游测试全挂：`Error loading shared library libglib-2.0.so.0 ... libcheck.so` | libqb/2.0.10 的配方把 glib/libxml2/check 声明为 host requires，PkgConfigDeps 生成 `libqb.pc` 的 `Requires:` 把这串共享库带进链接行；libqb 自身并不使用它们（`nm -u libqb.a` 无任何 glib/xml/check 符号），且 ohpcd 的 glib 只有 shared 变体 | `generate()` 中删除生成 `libqb.pc` 的 `Requires:` 行，只保留 `-lqb -lpthread` |
| 7 | `test-regression` 6 个断言失败：`cannot create temporary file` | 上游测试硬编码 `/tmp/usbguard-test.XXXXXX`，而 OHOS 的 `/tmp` 是只读文件系统 | 补丁 0004 改用 `$TMPDIR`（fallback `/tmp`）；配方 `build()` 导出可写的私有 TMPDIR |
| 8 | `package()` 报 `copy() got an unexpected keyword argument 'delete'` | Conan 2 的 `copy()` 无 `delete` 参数 | 改用 `conan.tools.files.rm(self, "*.la", lib)` |
| 9 | 消费者测试 `find_dependency(protobuf)` 找不到 config | protobuf/3.17.3 导出 `cmake_find_mode=none`，CMakeDeps 不生成其 config | test_package 里设 `protobuf_DIR`/`Protobuf_DIR` 指向包内 `lib/cmake/protobuf`（grpc 1.70 / protobuf 自带 test_package 先例） |
| 10 | 消费者 `The link interface of target "usbguard_DEPS_TARGET" contains protobuf::protobuf but the target was not found` | CMakeDeps 引用 conan 目标名 `protobuf::protobuf`，而 vendor config 只定义 `protobuf::libprotobuf` | test_package 的 CMakeLists 先 `find_package(protobuf CONFIG)`，缺目标时补一个指向 `protobuf::libprotobuf` 的 IMPORTED INTERFACE 别名 |

## 降级边界声明（均使用上游自带开关，configure.ac 有明确 OFF 路径）

- Linux Audit（平台无 auditd；ohpcd libaudit 2.7.4 亦低于所需的 ≥2.7.7）
- seccomp allowlist、POSIX capabilities（libcap-ng）、umockdev 设备管理
- D-Bus bridge 服务与 PolicyKit（无 dbus/gio/polkit 运行环境）
- LDAP 规则源、bash-completion 数据文件
- crypto 后端显式选 libsodium（上游默认）

## 交付形态

- `libusbguard.a`（静态库，`--disable-shared --enable-static`）+ `bin/{usbguard, usbguard-daemon, usbguard-rule-parser}`
- 二进制仅依赖 `libc++_shared.so` 与 `libc.so`（`readelf -d` 实测），无 glib 等共享库
- 头文件安装到 `include/usbguard/`，pkg-config 名 `libusbguard`（与上游一致），CMake 目标 `usbguard::usbguard`
- `package_info.requires` 补全 libqb/libsodium/protobuf（上游 `libusbguard.pc` 只写了 libqb，对静态消费者不足）

## 上游测试（R51 逐项计数）

### 上游测试总数 N = 17（口径：完整 automake `TESTS` 列表）

上游入口为顶层 `check: all` → 递归 `src/Tests/Makefile.am`。其 `TESTS` 由 3 个
configure 条件门控，**全部开启时共 17 项**（这也是本 PR 声明的「上游 N」）：

| 门控 | 项数 | 内容 |
|------|------|------|
| 默认（无条件） | 2 | `USB/test-descriptor-parser.sh`、`Rules/test-rules.sh` |
| `CATCH_ENABLED`（默认 on） | 2 | `test-unit`、`test-regression` |
| `FULL_TEST_SUITE_ENABLED`（`--enable-full-test-suite`，默认 off） | 7 | `Source/check-driver.sh` + `UseCase/000..005` |
| `WITH_LDAP`（`--with-ldap`，默认 off） | 6 | `LDAP/Sanity/ldap-nsswitch.sh` + `LDAP/UseCase/ldap-test-1..5` |
| **合计 N** | **17** | |

（2 个 Catch2 二进制展开为 17 个 `TEST_CASE`：unit 13 + regression 4。）

### 本 PR 构建内实际运行 N' = 4（上游默认条件：CATCH on / FULL off / LDAP off）

最终一轮（CI 同构 job `usbguard-1.1.4-ci-20261015-2-1`，干净重建，日志
`~/.local/share/ohpc-porting/runs/usbguard-1.1.4-ci-20261015-2-1/output.log`）
automake 汇总：**TOTAL=4 PASS=4 FAIL=0 SKIP=0 ERROR=0（4/4 = 100%）**。

| 项 | 命令 | 结果 | 计数 |
|----|------|------|------|
| USB/test-descriptor-parser.sh | `usbguard read-descriptor` 对 data/0001.bin 与 0001.out diff | PASS | 1 样本 |
| Rules/test-rules.sh | `usbguard-rule-parser` 解析 test-rules.good / 拒绝 test-rules.bad / 解析 test-rules.file | PASS | 3 组 |
| test-unit | Catch2 `./test-unit` | PASS | **423 assertions / 13 test cases** |
| test-regression | Catch2 `./test-regression` | PASS | **15 assertions / 4 test cases** |

### 其余 13 项（上游 opt-in 套件）未纳入构建内运行——逐项具体技术原因

这 13 项在上游 `configure.ac` 里默认 **off**（`--enable-full-test-suite` / `--with-ldap`），
非本任务裁剪。为如实核实其在本 OHOS 目标上的可运行性，已做**设备侧补充实跑**
（job `usbguard-r4-fts-20261015-1`，以 automake `TESTS_ENVIRONMENT` 同款环境直接运行；
上游 harness 约定 0=PASS / 77=SKIP / 其他=FAIL）：

| 项 | 设备侧结果 | 具体技术原因 |
|----|-----------|--------------|
| `UseCase/001,002,003,005` | **SKIP**（exit 77） | 缺 `umockdev-wrapper`（001/003/005）与 `modprobe`/`dummy_hcd`（002）；与本配方已 `--disable-umockdev` 一致 |
| `UseCase/000,004` | **FAIL** | `src/Tests/bash-testlib.sh` 用 `mktemp --tmpdir name.XXXXXX.log`；OHOS 的 `mktemp` 是 **toybox 0.8.12**，要求模板以 `X` 结尾，故报 `need XXXXXX: Invalid argument`（GNU coreutils 允许 X 后带后缀，toybox 不允许） |
| `Source/check-driver.sh` | **FAIL/超时** | CheckScripts 依赖 `astyle`（code-style）与 `aspell`（spell-check），OHOS 目标机均无；且驱动遍历整棵源码树超时 |
| `LDAP/Sanity/ldap-nsswitch.sh` + `LDAP/UseCase/ldap-test-1..5` | **NOT_RUN** | 需 OpenLDAP 服务器（`slapd`）+ 免密 root 修改 `/etc/nsswitch.conf`；`--with-ldap` configure 路径还需 `libldap` 头/库（目标机无） |

> 计数口径：N=17 与 N'=4 均为「automake TESTS 条目」同一单位；
> 未运行/跳过项不记 PASS（R51）。设备侧补充实跑日志见
> `$HOME/.local/share/ohpc-porting/runs/usbguard-r4-fts-20261015-1/output.log` 与
> `$HOME/tmp/ohpc-porting/usbguard-r4-fix-20261015-1/fts-logs/`。

## 门禁结果

- **conan-verify**（job `usbguard-1.1.4-w3-20261015l-1`，exit 0）：G0/G1/G2/G3/G4 全 PASS；
  L2/L4/L5 在本框架路径下标注「无 cache 路径」跳过（框架通用行为，同仓 322 份报告一致），
  由 CI 同构门禁覆盖。
- **CI 同构** `ci/conan/build_and_test.sh`（job `usbguard-1.1.4-ci-20261015-2-1`，exit 0，干净重建）：
  - G0 / KC / JC（prdiff，13 文件、1 个软件）全 pass
  - L0 pass（含 L0i 依赖在制品仓、L0k commands.json、L0m 目录结构）
  - L1 pass（`L1a/L1b/L1c`：上游 `make check` 与 test_package 均执行）
  - **L1e pass**：破坏性反向验证（移走 bin/lib/include 后测试确实失败）
  - L2 pass（`usbguard --version` OK、`usbguard-rule-parser --help` OK；
    `usbguard-daemon` 无 `--version/--help` 长选项，非阻塞告警，实测 `-h` 返回 0）
  - L4 pass（补丁无危险函数）、L5 pass（bin/ 有产物）
  - Build Summary: Total 1 / Success 1 / Pass rate 100%
- **消费者测试**：库 API 消费者二进制 9/9 断言通过；`usbguard --version` 输出 `usbguard 1.1.4`；
  `usbguard-rule-parser` 合法规则 rc=0、非法规则 rc=1。

## 编译结束

### rule4 计数更正后的门禁复跑（2026-10-15，HEAD 2fb9ef94b）

- **conan-verify**（job `usbguard-r4-w3-20261015-1-1`，exit 0）：G0/G1/G2/G3/G4 全 PASS
  （G2 为缓存命中，同包字节未变；新鲜重建证据见下）。
- **CI 同构** `ci/conan/build_and_test.sh`（job `usbguard-r4-ci-20261015-2-1`，exit 0，干净重建）：
  L0/L1/L2/L4/L5 全 pass；`make check` 汇总 `# TOTAL: 4`（与上文 N'=4 一致）；
  L1c 上游测试执行、L1e 破坏性反向验证通过；Build Summary 1/1，Pass rate 100%。
- 复跑仅改 `notes.md`/`test_package/MANIFEST.yml`（文档/元数据，不进配方制品），
  故构建与测试结果与首次一致；计数更正见上「上游测试」段。

（详细证据见 receipts/port-usbguard-20261015-1.md）
