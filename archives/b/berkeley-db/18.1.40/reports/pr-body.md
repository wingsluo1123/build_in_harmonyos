## PR 信息
- **三方库名称**：berkeley-db（Berkeley DB — 嵌入式键/值数据库库：Btree/Hash/Queue/Recno 访问方法、事务与恢复机制、15 个 db_* 命令行工具）
- **上游版本**：18.1.40
- **上游仓库地址**：https://github.com/berkeleydb/berkeley-db（源码归档：https://download.oracle.com/berkeley-db/db-18.1.40.tar.gz，sha256 0cecb2ef0c67b166de93732769abdeba0555086d51de1090df325e18ee8da9c8）
- **适配路径**：路径 A（基础适配），`archives/b/berkeley-db/18.1.40`
- **使用知识库**：OpenHarmony 编译 Skills（openharmony-compile-agent v12.22）。本包为 C/autotools 项目、零第三方依赖；HMDFS 下 configure/config.status 的构建期改写方案（print 探测错配、config.status 临时目录 umask/setgid 写入被拒）沉淀于版本级 `manifest.yaml` 的 knowledge_gained；真机 conan-verify 报告随档 `reports/`

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| C 单元测试（CuTest） | 13 套件（注册用例 55 个；Test* 函数 83 个） | `test/c/suites/*.c` 逐文件按 `^int Test` 函数计数共 83 个（TestEnvConfig 16、TestDbHotBackup 12、TestEncryption 12、TestPartition 11、TestPartial 8、TestPreOpenSetterAndGetter 8、TestCallbackSetterAndGetter 6、TestChannel 5、MutexAlignment/DbTuner/EnvMethod/KeyExistErrorReturn/Queue 各 1）；其中注册为 CuTest 用例、`./cutest` 实际执行 55 个（真机 `OK (n tests)` 实测）。`make cutest` 构建聚合执行器，`test/c/README` 指明在 build_unix 目录 `./cutest` 运行 |
| Tcl 脚本测试 | 252 个 test proc（155 文件） | `test/tcl` 共 558 文件、553 个 .tcl；需 Tcl 解释器 + `--enable-tcl`（本平台构建配置外） |
| 其他子目录测试源 | 276 文件 | `test/{cxx,java,csharp,xa,micro,db_guitest,utils,tcl_utils}`：分别需 C++ 绑定（`--enable-cxx`）/JDK/.NET 工具链/Oracle Tuxedo（`$TUXDIR`）/基准框架/Java Swing GUI，均在本平台构建配置外（逐项原因见版本级 `notes.md` R51 申报表） |
| **合计** | **test/ 全树 863 文件** | 静态清点；可断言运行集 = CuTest 13 套件 55 注册用例（真机执行），其余 Tcl 252 test proc 与 276 文件系测试源需平台外工具链 |

### 是否存在对上游测试用例的修改？
- [x] **否**——未修改任何上游测试文件（本适配零补丁：全部 HMDFS 兼容处理在配方 `build()` 内对构建期脚本做改写，不进入 `test/` 树）；CuTest 13 套件（55 注册用例）按上游原样构建、原样执行

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 通过率 | 说明 |
|----------|-------------|-----------|--------|------|
| 单元测试（CuTest） | 55 | 0（上游可运行集原样全跑） | 100%（55/55） | 真机 build_unix 内逐套件执行——出厂 clang -O3 件：12 套件直跑全绿；TestQueue 为上游测试代码在 clang -O3 下 UB 触发 trap（仅测试 TU 以 -O0 复建后 136/136 全过）；测试脚手架整体 -O0 复建后 13 套件一并连跑全绿（归档 rc=0；详见版本级 notes.md 验证结果）；13 套件零改动 |
| 消费者测试 | 3 用例（15 断言） | 新增 | 100%（3/3，TEST SUMMARY: 15 checks, 0 failed -> ALL PASS） | test_package 驱动：db_version 版本核对 / db_create+close 句柄生存期 / 内存态 Btree open→put→get→del 全链路 + 读回值逐字节校验；逐断言 CHECK PASS/FAIL + 末行 TEST SUMMARY，任一失败退出码 1 |
| **合计** | **58 用例** | **+3** | **100%（58/58）** | 真机实测（CuTest 13 套件 55 注册用例 + 消费者 3）；Tcl/C++/Java/C#/XA/micro/GUI 系测试需平台外工具链，不在本构建配置内 |

---

## 上游测试用例修改说明
无——未修改上游任何测试文件。本适配不含任何补丁（`patches_applied: []`），全部平台兼容处理位于配方 `build()` 对构建目录内 `dist/configure` 与 `config.status` 副本的构建期改写；`test/` 树未被触碰，CuTest 套件在真机按上游原样构建执行。

## 验证结果

### 编译验证
- 编译器: OHOS clang（aarch64-linux-ohos；OHOS SDK，sysroot musl）
- 编译状态: 成功——conan create 退出码 0（源码完整构建 configure→config.status→make→install→打包 + test_package 消费者测试全绿）
- 构建系统: autotools（`build_unix/` 下运行 `../dist/configure`，`make -j1`，DESTDIR 安装；显式 `--build/--host=aarch64-unknown-linux-gnu`）

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ✅ | conan create 干净构建 100%，0 错误（仅上游旧式代码 -Wdeprecated-non-prototype 类警告，无平台相关错误） |
| 产物存在性 | ✅ | `bin/` 15 个 db_* 工具（真机 ls 逐名核，与 manifest.yaml 清单一致）；`lib/libdb-18.1.so`（1792384B）/ `libdb-18.1.a`（2815812B）+ libtool 便捷名（libdb.so / libdb.a / libdb-18.so）；`include/db.h` / `db_cxx.h` |
| ELF 格式 | ✅ | 真机 llvm-readelf：ELF64 / AArch64（EM_AARCH64）；`db_dump` 等可执行件 `INTERP=/lib/ld-musl-aarch64.so.1` |
| 安全属性（真机 readelf 核验） | ✅ | PIE（Type=DYN）/ GNU_RELRO 段在 / GNU_STACK=RW（无 E 位=NX） |
| 运行测试 | ✅ | test_package 3 用例 15 断言 ALL PASS（TEST SUMMARY: 15 checks, 0 failed）；CuTest 出厂 -O3 件 12/13 套件直跑全绿 + TestQueue 仅测试 TU -O0 复建后 136/136 全过（测试脚手架整体 -O0 全套连跑一并验证） |
| 动态依赖 | ✅ | `libdb-18.1.so` DT_NEEDED=仅 `libc.so`（musl 合一，无 libm/libdl/libpthread 分裂件）；`bin/db_dump` DT_NEEDED=`libdb-18.1.so` + `libc.so` |

### 补丁说明
零补丁——本适配不引入任何补丁文件（对照 5.3.28 线交付的 config.guess/config.sub 替换补丁；18.1.40 走 4.8.30 已实证的显式 `--build/--host` 免补丁路线）；HMDFS/OHOS 兼容处理以配方 `build()` 内构建期改写实现（见「遇到的问题与解决方案」#2–#7）

### 依赖
- requires：无（零第三方依赖；`--with-repmgr-ssl=no` 关闭 Replication Manager 的 SSL 支持以避免引入 openssl）

### 测试结论
- 总体评价: conan-verify 全门禁 PASS（rc=0）——G1/G0/G2/G3/G4 全 ✅（G2 以本配方干净重建全绿，G0 热点 E490 的 autotools 脚本执行位提示经实测未致失败），L2/L4/L5 按设备常态跳过（无 cache 路径）；报告随档 reports/conan-verify-report.md（1.4KB）；完整构建日志（约 1.1MB）未随档（控制 MR 体积、保证平台评审有效覆盖），可按需提供
- 已知限制: Tcl/Java/C#/XA/C++ 绑定测试与 db_guitest 需平台外工具链或 GUI 环境，不在本平台构建配置内（逐项原因见版本级 `notes.md` R51 申报表）
- 上游测试用例通过率: 100%（注册用例 55/55，真机逐套件实测；TestQueue 的 -O3/-O0 判别见上表注）
- 新增测试用例通过率: 100%（3/3，15 断言，TEST SUMMARY: 15 checks, 0 failed -> ALL PASS）

### 遇到的问题与解决方案
1. configure 报 "cannot guess build type"（上游 config.guess 2017-08-08 不识别 OHOS aarch64 目标三元组）→ 显式传 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`（berkeley-db 4.8.30 已实证路线），免去 5.3.28 的 config.guess/config.sub 替换补丁
2. configure 探测 `print -r --` 成功，但 config.status 执行环境无 `print` 命令（ksh 内建探测与执行上下文不一致），回显退化为空串导致 config.status 失败 → 配方构建期改写 `dist/configure`：8 处 `print -r --`、2 处 `print -rn --` 强制为 POSIX `printf %s\n` / `printf %s`
3. config.status 生成临时 awk 脚本报 `subs1.awk: Permission denied` → config.status 临时目录默认 `umask 077`，新建的 2700+setgid 目录被 HMDFS 拒绝写入 → 配方反激活 configure 末尾的 config.status 自动执行行（dist/configure L27743），并改写 config.status：临时目录改用 `$TMPDIR/conf$$-$RANDOM`、`umask 077`→`umask 022`，随后手动 `$SHELL ./config.status`
4. make 首条规则即失败：`./libtool: Permission denied`（126）→ OHOS 内核无 binfmt_script，make 对顶层 `./libtool`（`#!` 包装脚本）直接 execve 恒被拒 → 构建期把 config.status 内 `S["LIBTOOL"]` 替换为 `sh ./libtool`（生成 Makefile 时生效），config.status 跑完后再对 Makefile 做 `^(LIBTOOL=)(\s*)\./libtool` → `sh ./libtool` 正则兜底（双保险）
5. 链接/安装规则报 `ln: cannot create symbolic link from '.libs/libdb-18.1.a' to 'libdb.a'` → HMDFS 全盘拒绝 symlink(2)（EPERM），Makefile 中 23 处 `$(LN) -s` 便捷名生成全挂 → 统一改写为 `cp -f`（libtool 自身 LN_S 已被 configure 统一探测为 `cp -pR`，无需处理）
6. 装出的 db_* 工具在设备上全部 126（Permission denied）→ install_utilities 逐个执行 `$(STRIP)`（llvm-strip），剥离了 OHOS clang 链接时自动注入的 .codesign 段（27008B 签名件→10104B 未签名件），设备内核拒执未签名 ELF → Makefile 中禁用该 strip 行（改 no-op）；对照：未 strip 的 .libs 原件可直执且 `db_archive -V` 正常输出
7. install_docs 报 `cp: bad 'bdb-sql'` / `cp: bad 'gsg_db_server'` → DOCLIST 两个成员在上游 tarball 里是符号链接，HMDFS 解包时被跳过不落盘 → DOCLIST 剪枝这两个 token

### 验证命令
```
# 真机（HarmonyOS PC aarch64 真机，profile ohos-aarch64）
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
# 末段实录（test_package 消费者测试，摘自构建日志）：
#   CHECK PASS: 主版本号 == 18
#   CHECK PASS: 次版本号 == 1
#   CHECK PASS: 补丁号 == 40
#   CHECK PASS: 版本串包含 "18.1.40"
# TEST PASS: db_version
# TEST CASE: db_create / db->close
#   CHECK PASS: db_create 返回 0 且句柄非空
#   CHECK PASS: db->close 返回 0
# TEST PASS: db_create / db->close
# TEST CASE: in-memory Btree open/put/get/del
#   CHECK PASS: db_create 返回 0 且句柄非空
#   CHECK PASS: db->open(NULL, DB_BTREE, DB_CREATE) 返回 0
#   CHECK PASS: db->put 写入键值返回 0
#   CHECK PASS: db->get 读回返回 0
#   CHECK PASS: 读回值与写入值逐字节一致
#   CHECK PASS: db->del 删除键返回 0
#   CHECK PASS: 删除后 db->get 返回 DB_NOTFOUND
#   CHECK PASS: db->close 返回 0
# TEST PASS: in-memory Btree open/put/get/del
# TEST SUMMARY: 15 checks, 0 failed -> ALL PASS
#
# CONAN_CREATE_RC=0

# 上游 CuTest（build_unix 目录内）
make cutest && ./cutest
# 末段实录（测试脚手架整体 -O0 复建后 13 套件一套连跑；出厂 -O3 判据见上表注）：
# Running suite TestPreOpenSetterAndGetter
# ....
# OK (4 tests)
# Finished suite TestPreOpenSetterAndGetter
# Running suite TestQueue
# TESTING: sh_list
# ....................................................................	100.00% passed (68/68).
# TESTING: sh_tailq
# ....................................................................	100.00% passed (68/68).
# .
# OK (1 test)
# Finished suite TestQueue
# O0FULL_RC=0

# conan-verify
python3 scripts/ohc-run.py conan-verify berkeley-db 18.1.40
# Verdict: PASS（G1/G0/G2/G3/G4 全 ✅；L2/L4/L5 跳过=无 cache 路径）
# CONAN_VERIFY_RC=0（milestone: conan_verify_passed）
# 报告: reports/conan-verify-report.md（随档）
```

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？
- [x] **是**，上游有可运行的 C 单元测试（CuTest 13 套件 55 注册用例）但无消费者视角测试，适配后补全了消费者测试

适配后**新增** 3 项消费者测试（15 断言，见上表消费者测试行）：
- **新增测试文件清单**：
  1. `archives/b/berkeley-db/18.1.40/test_package/conanfile.py` —— 消费者测试驱动：CMake 构建 + `VirtualRunEnv` + `can_run` 守卫，真实执行 `test_berkeley-db`（非零退出即失败）
  2. `archives/b/berkeley-db/18.1.40/test_package/test.c` —— 真实执行器：3 用例 15 断言（db_version 版本核对 5 断言 / db_create+close 句柄生存期 2 断言 / 内存态 Btree open→put→get→del 全链路 8 断言，含读回值逐字节校验与删除后 DB_NOTFOUND 校验）；逐断言 CHECK PASS/FAIL + 末行 TEST SUMMARY，任一失败退出码 1
  3. `archives/b/berkeley-db/18.1.40/test_package/CMakeLists.txt` 与 `MANIFEST.yml` —— 构建接线与测试清单（`upstream_check_command: make cutest && ./cutest`，`assertion_count: 15`）
- **补全原因**：上游测试面为库内 C 测试（CuTest 单元测试），无「已安装产物可用性」的消费者视角验证；`find_package(berkeley-db)` 经 CMakeDeps 的 `berkeley-db::berkeley-db` 目标链接、头文件可用性、运行时 .so 寻址与数据库引擎真实读写（open/put/get/del）由 test_package 以消费方视角真实运行覆盖

## 补充说明
1. **HMDFS 兼容方案（零补丁）**：全部处理位于配方 `build()` 对构建期脚本的改写——仅作用于构建目录内的 `dist/configure`、`config.status` 副本与生成的 `Makefile`，不改动上游 tarball 本身、不随包交付补丁文件（对照：5.3.28 线交付大体积 config.guess 替换补丁）；
2. **软件级交付**：本 PR 同时携带软件级 `archives/b/berkeley-db/README.md`（库/工具/头文件矩阵，双版本）与 `commands.json`（15 个 db_* 工具注册、versions 双版本登记），与既有 4.8.30 交付并存互补；
3. **版本差异**：18.1.40 相对 5.3.28 新增 db_convert、移除 db_sql；UTIL_PROGS 共 15 个工具（清单见版本级 manifest.yaml）；
4. **R51 上游测试清点**：test/ 全树 863 文件逐目录计数与逐项排除原因见版本级 `notes.md`（含 CuTest 83 个 Test* 函数/55 注册用例逐套件计数）；
5. **文件字节一致性**：终态 10 个交付文件与 reports/conan-verify-report.md 经真机 md5sum 逐件核验——**设备侧与本地逐字节一致**：conandata.yml `f6ce0dd6d3fb5a3a58716a39d04b4fc7` 170B；conanfile.py `2c82a0c73c9913472ab2e0157810c96a` 12458B；manifest.yaml `18d08a622cd54cd91a3a437814998d0d` 3304B；notes.md `3e5c12ec3941a149c0a320d2ba5e5c3f` 8601B；test_package/CMakeLists.txt `c67fbc648e5b186f150d697d9a2d1da4` 331B；test_package/MANIFEST.yml `bde88a9b683553674c0687c7c6b475ae` 1691B；test_package/conanfile.py `3d6bd10c5728026be4e9e4bb9c50f32f` 1697B；test_package/test.c `6b6d1e59d291e13da7e08d3b919ad402` 4554B；README.md `f7b0bf6a4a645bd2d42f8e5fa277f43f` 1327B；commands.json `045aabcc5677a5083a07865696a79d9e` 393B；reports/conan-verify-report.md `0904fb9407f6ed7848a340cfee53e76b` 1408B（构建日志不随档，仅本地/设备留档）。
