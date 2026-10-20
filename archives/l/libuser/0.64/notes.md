# libuser 0.64 适配笔记

## 编译环境

- 构建系统：autotools（configure + make；本 dfsg 解包树无预生成 `configure`/`Makefile.in`/`admin/`，build() 内 `_run_autogen` 自举）
- 编译日期：2026-10-19（W3 本地 conan-verify；CI upload 成功后方可标 published）
- 编译器：clang（OHOS aarch64 原生构建）
- 状态：built（W3 conan-verify 全 PASS，2026-10-19 15:24；CI upload 成功后方可标 published，读数见下方 §验证结果）

## 上游调研

- 上游：https://pagure.io/libuser/（Red Hat 用户/组账户管理库）
- 本版本为 0.64 正式发布源码包：`libuser_0.64~dfsg.orig.tar.xz`（365428 字节，tar.xz）
- SHA256 `87169b85d1c207b06b43a34aad7e4074ab211db2268744c1286afa75befbda58` 来自 Debian 官方
  `libuser_0.64~dfsg-1.dsc`（Checksums-Sha256）与本机 `sha256sum` 双源一致
- `configure.ac` 关键结论（决定配方依赖与开关，0.64 release 文本亲读）：
  - `AC_INIT([libuser], [0.62], …)`（上游 release 着色仍写 0.62，Debian 改版级 0.64，任务/配方/归档以任务版本串 `0.64` 为准，不做归一化）
  - glib 三件套为硬依赖：`PKG_CHECK_MODULES(GLIB/GOBJECT/GMODULE)`（精确名 `glib-2.0 gmodule-no-export-2.0 gobject-2.0`）→ 需 `glib/2.88.3` + PkgConfigDeps 提供 `.pc`
  - popt 仅路径参数、无开关，全部 CLI 以 `-lpopt` 链接 → 需 `popt/1.19`（W0 recipe-only rc=0）
  - `apps/libapputil.la` 无条件链接 `-lpam -lpam_misc` → 需 `linux-pam/1.7.2`（barada-pam/0.5.3 与 vlock/2.2.2 同口径依赖先例）
  - ldap/sasl 默认均为 no（传 `--with-ldap/--with-sasl` 才启用），selinux 默认 no，audit 默认 auto（无 libaudit 则静默关闭，本配方显式 `--without-audit` 求确定性）
  - `AC_SEARCH_LIBS([crypt], [crypt])` 条件链接（本 OHOS musl 侧 configure 实测解析结果见 §遇到的问题；`libxcrypt/4.5.2` W0 recipe-only rc=0 仅作备仓记录，不进 requires —— 与已合入的 0.64-git20241106-dfsg 配方口径一致）
  - python 默认 YES（`with_python=yes`）；本配方保持 `--with-python`（worker HNP python3 自带 Python.h，4/5 自动化 TESTS 需要 `import libuser`，见 0.64-git20241106-dfsg CI #62950/#91463 教训）
  - gtk-doc：**0.64 release 的 `configure.ac` 里 `GTK_DOC_CHECK` 是裸宏调用（无参数）**，git 快照 Span 版为 `GTK_DOC_CHECK([1.14],[--flavour no-tmpl --docdir docs/reference])`；配方内的 ENABLE_GTK_DOC=false 置换正则对两种形态均命中
  - `bison -y`（getdate.y，无预生成 getdate.c）→ worker/CI 需 bison（HNP bin 已见；配方未声明 tool_requires bison —— 同门 0.64-git20241106-dfsg 配方同样未声明且已过 CI，若 CI 报缺再按 R43 单点补）
- 上游测试（`Makefile.am` 的 `TESTS`，LDAP/SASL 禁用时共 5 项）：
  `tests/config_test.sh`、`tests/fs_test`、`tests/files_test`、`tests/pwhash_test`、`tests/utils_test`
  （另有 `tests/default_pw_test`、`tests/ldap_test` 仅在 `--with-ldap` 时注册，本配方不启用；官方注册总数口径 7）
- 模块加载：`lib/modules.c` 经 `lu_cfg_read_single(ctx, "defaults/moduledir", MODULEDIR)` 定位后端 `.so`；
  `lib/config.c` 允许 `LIBUSER_CONF` 环境变量覆盖配置文件（非 setuid 时）。test_package 靠此机制把模块目录
  指向 Conan 包内 `lib/libuser`，不写死绝对路径。

## 与同门已合入配方的关系（0.64 vs 0.64-git20241106-dfsg）

本配方以主仓已合入的积分赛配方 `archives/l/libuser/0.64-git20241106-dfsg/` 为底稿（`recipe-search` top1），
版本串与源码包为 0.64 正式 release（`libuser_0.64~dfsg.orig.tar.xz`），与 git 快照包
`libuser_0.64+git20241106~dfsg.orig.tar.gz`（SHA256 e383cbda…）为**不同版本号、不同文件**的真包，
R37 版本未被占用（preflight 读数 `[OK] 版本号未被占用: libuser/0.64`）。

两树 `diff -rq` 亲测（本机 ~/tmp/uc2/libuser/src/orig/libuser-0.64 对 git 快照解包树，2026-10-19）：
源码差异**仅**以下四处，构成「非同包版本语义差异」证据仓：

| # | 差异 | 原文位置 | 语义 |
|---|------|----------|------|
| 1 | `GTK_DOC_CHECK` 与 `GTK_DOC_CHECK([1.14],[--flavour no-tmpl …])` | `configure.ac` L172 | doc 工具探针形态不同，功能等价（配方置 ENABLE_GTK_DOC=false 两形态通吃） |
| 2 | `len > UT_NAMESIZE - 1` vs `len > UT_NAMESIZE`（+对应 memcpy 长度 -1） | `lib/user.c` L226-229（共 8 行 diff） | utmp 名字段截断边界：release 0.64 保守 1 字节（含 NUL），git 快照放宽 |
| 3 | `tests/files_test.py`、`tests/default_pw_test`、`tests/ldap_test.py` | `tests/` | 驱动脚本细节；两个 ldap 门控项不在本配方 TESTS 注册内 |
| 4 | `po/*.po` 翻译与 `po/libuser.pot` 有无 | `po/` | 仅文案，无构建语义 |

其余源码树（含 `lib/config.c` 的 secure_getenv 块、`python/libusermodule.c` 的 getusershell 族、
`modules/files.c`、Makefile.am）逐字节一致 ⇒ 配方机制（autoreconf 自举链、gtk-doc 桩、
sgml 文档禁用、mktemp/umask 兜底、libtool 陈旧 .la 清理、proxy-libintl whole-archive LIBS、
模块查找经 LIBUSER_CONF）同源可复用；下表问题台账里仅第 5 条为 0.64 侧新增读数。

## 依赖版本（W0 全 recipe-only rc=0，2026-10-19）

| 依赖 | 版本 | 用途 | 核验 |
|------|------|------|------|
| glib | 2.88.3 | glib-2.0/gobject-2.0/gmodule-no-export-2.0 硬依赖 | `conan download --only-recipe -r=ohpcd` rc=0 |
| popt | 1.19 | 全部 CLI -lpopt | 同上 rc=0 |
| linux-pam | 1.7.2 | apps/libapputil.la 无条件 -lpam -lpam_misc | 同上 rc=0 |
| proxy-libintl | 0.5（static） | g_libintl_* 符号闭环（glib nls=disabled） | 同上 rc=0 |
| m4/autoconf/automake/libtool/gettext | 1.4.19 / 2.72 / 1.18 / 2.5.4 / 0.22.5.1 | tool_requires（autoreconf 自举链，CI #93801 教训：全链必须显式声明） | 同上 rc=0 |
| libxcrypt（备仓记录） | 4.5.2 | crypt 条件链接备选 | 同上 rc=0（未进 requires） |

**包名教训（可复用先例 vlock/2.2.2 W0 段）**：本任务前手曾以 `pam/1.7.0` 探测连续两轮报
`system acceleration policy not enabled [Remote: ohpcd]` 而停手。该错误在制品仓语义有二义
（瞬时故障 **或** 精确配方不存在，判据见 12a 经验库 §12.5/§12.x：必须同批跑已知已发布对照包），
本窗口另发现根因之一是**包名本身错了**——仓内 PAM 配方正名为 `linux-pam`（`linux-pam/1.7.2`
recipe+binary 双可消费，vlock/2.2.2 notes W0 段同先例），`pam/*` 精确名在 ohpcd 无配方。
今后 W0 探测对「平台同义别名包」先查仓内最近成功归档的精确依赖名再探。

## 编译步骤

1. `get()` 解包 0.64 release tarball（strip_root=True，树根为 libuser-0.64/，与 git 快照平铺树不同）
2. `generate()`：PkgConfigDeps（glib 的 `.pc`，含 gmodule-no-export-2.0 别名拷贝）+ AutotoolsDeps
   + AutotoolsToolchain（`--with-python --without-sasl --without-ldap --without-selinux
   --without-audit --disable-nls --disable-dependency-tracking` + shared/static 开关）
3. `build()`：陈旧 `.la` 清理 → 占位 install-sh → docs sgml/gtk-doc 桩与 disable →
   configure.ac issetugid/getusershell 探针增强与 lib/config.c、python/libusermodule.c 兜底实现
   → autoreconf/gettext 自举 → `configure` → `make -j1` → `make check -j1`（best-effort，
   真实计数解析自 `test-suite.log` 的 `# TOTAL/# PASS/# FAIL/# SKIP` 汇总块并输出
   `HMBS_UPSTREAM_TEST_RESULT`）
4. `package()`：`make install`（bundled install-sh 变量兜底），删除 `lib/*.la`，复制 `COPYING`
   到 `licenses/`，持久化 `res/hmbs_upstream.json`
5. `test_package`：CMake 编译 `test_libuser.c`（**7 组**真实 API 调用），运行时经 `LIBUSER_CONF`
   把 `defaults/moduledir` 指向包内模块目录，输出 `HMBS_TEST_PACKAGE_RESULT`

## E338 族消费端探针（0.64 版本特有增量，第 7 组）

test_package 第 7 组 `e338_pwd_semantics`（单二进制内，真 API 真执行，断言 4 项 + DIAG 日志）：

- a) `getpwnam("root")` 真装配：非 NULL 且 `pw_name=="root"`（E338 census：root 在 /etc/passwd 内；DIAG 实测 pw_dir 空串）
- 快照) 装配记录立刻序列化（char 缓冲 + uid）——**musl 所有 pwd 族共用一个静态结构，失败查找会把它复写成下一条记录**（实测 root/uid=0 → 失败查找后同指针读到 `kkbor_service_user20`/uid=9020）；断言 (d) 只消费快照
- b) 缺失行 `getpwnam("hmbs-e338-nosuchuser")` 返回 NULL（空转不制造填充结构、不 SIGSEGV）
- c) 库级：空 files 后端（LIBUSER_CONF 的 files 目录为空）上 `lu_user_lookup_name(nonexistent)` 返回 FALSE、不崩、不设 error（generic_lookup 对"行不存在"就不记错——契约=有序 FALSE，非"必须带 error"）
- d) `struct passwd → lu_ent` 真回灌：`lu_ent_set_string(LU_USERNAME)/lu_ent_set_id(LU_UIDNUMBER)`（注意：`lu_ent_add` 系 API 收 `const GValue*`，传 char* 会编译告警+运行 SIGSEGV——本轮 r3 首错即此）后读回一致（uid=0）

四项 + 快照全部通过组才 PASS；无环境豁免、无计数下调（未测项不吃 N）。DIAG 行逐组留日志尾证据。

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案 |
|---|----------------------|------|----------|
| 1 | 前手 `pam/1.7.0` 两轮 `system acceleration policy not enabled` | 错误包名（仓内正名 `linux-pam`）+ 错误正文二义 | 正名 `linux-pam/1.7.2` recipe-only rc=0 + 同批对照包排除瞬时故障（见上） |
| 2 | （继承同门，机制同源）`cannot run C compiled programs` | 本机沙箱禁行 CC 探针二进制 | 显式 `--build=x86_64-pc-linux-gnu --host=aarch64-unknown-linux-gnu`（诚实交叉声明；conanfile `_manual_configure_args`/generate 均含） |
| 3 | （继承同门）gtk-doc.m4 缺失致 automake 中止 | 0.64 release 树同样不带 gtk-doc.make | 配方桩 + configure.ac `GTK_DOC_CHECK` 置换（两形态通吃，见差异表 #1） |
| 4 | （继承同门）configure `secure_getenv` 系探针全空 → `#error` | musl/Yocto 类 libc 无该族 | issetugid 探针 + uid/gid 恒等守卫 getenv 兜底（0.64 release 的 `lib/config.c` 与快照逐字节一致，锚点命中） |
| 5 | r1 `Component 'glib::glib-2.0' not found in 'glib' package requirement`（test_package CMakeDeps） | glib/2.88.3 配方组件 ID=`glib/gobject/gmodule`（pkg_config_name 才是 -2.0 后缀）；2.84 时代引用串写法不兼容 | cpp_info.requires 改 `glib::glib::` 三件新 ID |
| 6 | r2 `package_info(): …requires to other internal components that are not defined: ['popt','proxy-libintl']` | 无组件包被裸名引用时被当成**内部**组件名解析 | 无组件依赖按 Conan 2 隐式默认组件写 `popt::popt`/`proxy-libintl::proxy-libintl` |
| 7 | r3 消费端 `PASS: context_start` 后 SIGSEGV（rc=-11） | 我方第 7 组用例把 `char*` 传给 `lu_ent_add`（API 收 `const GValue*`）；叠加 musl pwd 静态区已被失败查找复写 | `lu_ent_set_string`/先快照（见 E338 段）；修正后 7/7 |
| 8 | 上游 make check：files_test `ModuleNotFoundError: No module named 'crypt'` | worker python3=3.14.7，PEP 594 已移除 crypt/crypt_r（上游 git 快照的 try import crypt_r 于此机同样落空） | 真实 ohos_feature 缺口，诚实落 marker（不改测试凑 N） |
| 9 | 上游 pwhash_test/utils_test `Cannot obtain lock …passwd.lock/group.lock: Operation not permitted` | 队列文件锁（HMDFS 工件目录）worker 不支持 | 真实 ohos_feature 缺口，诚实落 marker（同门 CI #62950 同类）；fs_test 因 fakeroot 缺 SKIP（上游设计） |

## 验证结果（W3 conan-verify，2026-10-19 15:24，conan-verify-report.md：Verdict PASS）

- **G0（知识命中 E566 提示性风险：显式 --build/--host 已在配方内，实跑无失误）/ G1 配方完整性 / G2 conan create rc=0 / G3 R26 无系统同名冲突：全 PASS**；G4/L2/L4/L5 由 verifier 判 PASS（无 cache 路径时跳过型，见报告原文）。
- **conan create 制品**：libuser.so.1.5.2 + libuser_files.so/libuser_shadow.so 后端、luseradd/lusermod/luserdel/lgroupadd/lgroupmod/lgroupdel/lpasswd/lchage/lchfn/lchsh/lid/lnewusers 13 CLI、man 页 13+1、pkgconfig/libuser.pc、include 7 头、libuser.conf、licenses/COPYING、res/hmbs_upstream.json。
- **消费者 test_package（L1）7/7 PASS**：`HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "discovered": 7, "passedCount": 7}`；E338 组 DIAG 读数见 §E338 族消费端探针。
- **上游 make check（best-effort，非 W3 门禁）**：`# TOTAL 5 / PASS 1 / SKIP 1 / FAIL 3`（PASS=config_test.sh；SKIP=fs_test 上游设计需 fakeroot；FAIL=files_test（python3.14 无 crypt）+ pwhash_test/utils_test（HMDFS 锁）），缺口诚实分类落 `HMBS_UPSTREAM_TEST_RESULT`（discovered=7=常驻 5 + LDAP 门控 2）。
- `status: built`（CI upload 成功后方可标 published）。
- 本地 finish 的全树 W3 模拟第一步被**其他窗口遗留**的 9 个 `.staging-verified`/`.build-closed` 挡在 JC 门（cloog/kcachegrind/libdazzle 等，均非本任务产物、不动他人资产）；PR 只含本包归档目录，CI 于我的 diff 分支不受影响（AGENTS §8 基线怀疑口径）。

---

**编译结束**: 2026-10-19 15:39
**最终状态**: built
