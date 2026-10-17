# apt-pkg 2.7.14 适配笔记（OHOS aarch64）

## 编译环境
- 构建系统: cmake（OHOS 交叉编译，目标 aarch64-linux-ohos / HarmonyOS）
- 编译日期: 2026-10-06
- 编译器: clang/clang++（OHOS SDK LLVM，aarch64-unknown-linux-ohos-clang）
- 状态: built

## 编译步骤

```bash
# 依赖经 conan 制品仓注入（ohos-aarch64 profile，settings: os=OHOS arch=armv8 compiler=clang 15）
cd build-ohos
conan install ../conanfile-deps.txt -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing
cmake -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake \
      -DCMAKE_BUILD_TYPE=Release -DWITH_TESTS=ON ..
make -jN
# 产物: build-ohos/test/libapt/libapt_test（aarch64 musl 动态 ELF，5.0 MB）
```

- CMake 交叉编译 100% 通过；libapt-pkg/libapt-private 静态库与 test/libapt 测试二进制均编译成功。
- 编译期关键点：CMake 不识别 HarmonyOS 平台（“System is unknown to cmake”），依赖 conan toolchain 把
  CMAKE_SYSTEM_NAME 映射为 HarmonyOS，并靠 0010 补丁固定 GNUInstallDirs LIBEXECDIR=lib。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | xxhash 头文件找不到 | conan 的 XXHASH include 目录未传到项目级 | 0001 补丁：xxhash include 目录项目级传播 |
| 2 | methods/gnutls 头文件找不到 | gnutls include 目录是复数 include 未传 | 0002 补丁：methods gnutls include_directories 复数 |
| 3 | methods/seccomp 头文件找不到 | seccomp include 目录复数未传 | 0003 补丁：methods seccomp include_directories 复数 |
| 4 | methods/seccomp open64 等符号与 OHOS 头文件冲突 | musl LFS 别名 | 0004 补丁：seccomp 相关 TU #undef LFS 别名 |
| 5 | CMake 不识别 aarch64-linux-ohos 平台 | CMake 无 HarmonyOS 平台定义 | 0005 补丁：common/arch 平台适配（aarch64→arm64 等） |
| 6 | debSystem 评分判死 | OHOS 不在上游评分表 | 0006 补丁：给 OHOS 平台打分 |
| 7 | 无 /usr/share/dpkg cputable/tupletable，库初始化失败 | OHOS/musl 无 dpkg 数据目录 | 0007+0009 补丁：缺失时退化/内嵌 dpkg 1.21.x 架构表 |
| 8 | debSystem 动态链接符号缺失 | OHOS 静态库布局 | 0008 补丁：init debSystem 静态链接强制 |
| 9 | 架构<->tuple 映射为空致 multiarch 匹配失败 | 无 dpkg 表 | 0009 补丁：内嵌 cputable+tupletable |
| 10 | GNUInstallDirs LIBEXECDIR 解析为 bin，make install 失败 | OHOS 无 /etc/debian_version，CMake 不识别平台 | 0010 补丁：HarmonyOS 时同样固定 LIBEXECDIR=lib |

## 源码修改

20 个补丁，位于 `patches/0001-0020`。全部已在 pristine 源上**按序用 patch_ng（conan
`apply_conandata_patches` 所用的严格补丁库，fuzz=False、行号精确）验证可干净打入**，
最终树与构建工作区逐字节一致（`diff -rq` 0 差异）。原始 0001-0010 因在已改动的
源码上再生成而带行号偏移（patch_ng 严格匹配会拒绝，GNU/toybox patch 的 fuzz 能吞掉，
导致 conan create 首次失败），已全部按连续快照重新生成（`diff -u tree_{i-1} tree_i`）。
- 0001: CMake xxhash include 项目级传播
- 0002/0003: methods gnutls/seccomp include 目录复数修正
- 0004: methods/seccomp LFS 别名 #undef
- 0005: CMake common/arch OHOS 平台适配（dpkg-architecture 缺失时按 uname -m 推导 COMMON_ARCH）
- 0006: debSystem OHOS 评分
- 0007: init.cc pkgInitArchTupleMap 缺表退化（被 0009 演进替代）
- 0008: init debSystem 静态链接强制
- 0009: init.cc 内嵌 dpkg cputable/tupletable（__OHOS__ 分支）
- 0010: CMakeLists LIBEXECDIR 固定 lib（HarmonyOS）
- 0011: CMake/FindLFS.cmake LFS_FOUND PARENT_SCOPE（conan toolchain CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON 屏蔽 CACHE 值）
- 0012: CMake/apti18n.h.in 移除 C++17 已删除的动态异常规格 throw()
- 0013: CMakeLists include(CheckSymbolExists)（check_symbol_exists 未引入即调用）
- 0014: apt-pkg/CMakeLists.txt add_library SHARED→STATIC + install ARCHIVE（R26 静态库）
- 0015: apt-private/CMakeLists.txt 同上（SHARED→STATIC + ARCHIVE）
- 0016: apt-pkg/contrib/srvrec.cc 非 glibc（musl/OHOS）用 getservbyport() 替代 getservbyport_r()
- 0017: CMake/FindIconv.cmake 接受 musl-libc 内置 iconv（OHOS libc 自带 iconv，find_path 找不到单独头目录）
- 0018: CMake/FindBerkeley.cmake 把 conan 包前缀加入 find_path 搜索路径（NO_DEFAULT_PATH 挡掉了 conan prefix）
- 0019: CMake/FindGCRYPT.cmake 保留完整 pkg-config include 列表（被折叠只留最后一项导致 libgpg-error 头缺失）
- 0020: CMakeLists DPKG_DATADIR 在 perl Dpkg 探测失败时回退（OHOS 无 perl Dpkg 模块/无 /usr/share/perl）

> 注：0007 与 0009 是演进关系（0009 在 0007 之上改写同区域，0009 的上下文含 0007 新增行），
> 必须按 0007→0009 顺序应用，缺一不可。

## 依赖版本

| 依赖 | 版本 |
|------|------|
| libdb | 5.3.35 |
| zlib | 1.3.1 |
| bzip2 | 1.0.8 |
| liblzma | 5.8.1 |
| lz4 | 1.9.4 |
| libgcrypt | 1.11.0 |
| xxhash | 0.8.2 |
| libzstd | 1.5.7 |
| gnutls | 3.8.10 |
| systemd | 261 |
| libseccomp | 2.5.5 |
| eudev | 3.2.14 |
| gtest（仅测试） | 1.17.0 |
| triehash（构建期） | 0.3.1 |
| perl（构建期） | 5.42.2 |

## 验证结果（上游 test/libapt，R51）

运行环境：OHOS aarch64（HongMeng Kernel 1.12.0），本机直接执行 aarch64 musl 动态 ELF。
运行方式：

```bash
cd test/libapt && source build-ohos/conanrunenv-release-armv8.sh
build-ohos/test/libapt/libapt_test          # 全量：137 tests, 28 suites
build-ohos/test/libapt/libapt_test --gtest_filter='-FileUtlTest.*:HashSumsTest.*'   # 剔除环境失败组
```

### 通过率

- **全量（单次进程运行全部 137 项）: 119/137 通过（86.9%）**
- 剔除 FileUtlTest+HashSumsTest 两个环境失败套件后：**122/127 通过**，且 15 项
  OpenMaybeClearSignedFile 全部通过（证明其“失败”为全局错误栈污染，非自身缺陷）
- OpenMaybeClearSignedFileTest 单独运行：**15/15 通过**

### 上游测试清单（逐项）

| 测试套件 | 结果 | 说明 |
|----------|------|------|
| AcqProgress (5) | ✅ 5/5 | |
| NetRCTest (6) | ✅ 6/6 | |
| CacheFilterTest (1) | ✅ 1/1 | ArchitectureSpecification（依赖 0009 内嵌架构表）|
| CDROMTest (3) | ✅ 3/3 | |
| CommandLineTest (4) | ✅ 4/4 | |
| CompareVersionTest (5) | ❌ 0/5 | 见下：外部 dpkg 二进制缺失 |
| ConfigurationTest (7) | ✅ 7/7 | |
| ExtractTar (1) | ✅ 1/1 | |
| FileUtlTest (8) | ⚠️ 4/8 | 4 项环境原因失败（见下）|
| ArchitecturesTest (3) | ✅ 3/3 | |
| LanguagesTest (2) | ✅ 2/2 | |
| GlobalErrorTest (6) | ✅ 6/6 | |
| HashSumsTest (2) | ⚠️ 1/2 | FileBased 依赖 /etc/os-release（缺失）|
| IndexCopyTest (1) | ✅ 1/1 | |
| InstallProgressTest (1) | ✅ 1/1 | |
| JsonTest (5) | ✅ 5/5 | |
| OpenMaybeClearSignedFileTest (15) | ⚠️ 7/15（全量）→ 15/15（单独） | 8 项为错误栈污染 |
| ParseDependsTest (1) | ✅ 1/1 | |
| TreeParserTest (10) | ✅ 10/10 | |
| PriorityTest (1) | ✅ 1/1 | |
| SourceListTest (1) | ✅ 1/1 | |
| SrvRecTest (2) | ✅ 2/2 | |
| StringViewTest (5) | ✅ 5/5 | |
| StrUtilTest (15) | ✅ 15/15 | |
| TagFileTest (7) | ✅ 7/7 | |
| TagSectionTest (10) | ✅ 10/10 | |
| TeeStreamTest (3) | ✅ 3/3 | |
| URITest (7) | ✅ 7/7 | |

### 18 项失败逐一定位（崩溃点 = 断言/文件/行号 + 实测证据）

**1) CompareVersionTest.Basic/Epochs/Strangeness/DebianBug/CuptTests（5 项，compareversion_test.cc:62）**
- 断言：`EXPECT_PRED3(callDPKG, ...)`，`callDPKG()` 内部 `execvp("dpkg", ["dpkg","--compare-versions",A,op,B])` 后子进程 `exit(1)`，父进程 `WEXITSTATUS==1`。
- 实测证据：`which dpkg` → not found；`/usr/bin/dpkg`、`/bin/dpkg`、`/system/bin/dpkg` 均不存在；`find / -name dpkg -type f` 无结果。OHOS rootfs 只读，无法安装 dpkg（无 sudo，`touch /usr/bin/.wtest` → Read-only file system）。
- 关键佐证：同测试文件 line 61 的 `EXPECT_EQ(compare, Res)`（apt 侧 debVS.CmpVersion 对全部内嵌向量）**0 失败**——apt 版本比较逻辑本身全部正确，仅外部 dpkg 交叉校验二进制缺失。grep 统计 `compareversion_test.cc:61` 失败数 = 0。

**2) FileUtlTest.FileFD（fileutl_test.cc:173，permission 断言）**
- 断言：`EXPECT_EQ(ExpectedFilePermission, buf.st_mode & 0777)`。实测 0664→0660、0644→0640，缺 others-read(0004) 位。
- 实测证据：OHOS 用户存储文件系统屏蔽 world 读位——`umask 02; echo x > f; stat -c %a f` → 660（Debian 为 664）；`umask 022` → 640（Debian 为 644）。umask 077/026 用例（不含 others 位）通过，说明仅 “other” 位被文件系统屏蔽。
- 根因：OHOS /storage 用户存储的权限策略，非 apt 缺陷。

**3) FileUtlTest.GetTempDir（fileutl_test.cc:271）**
- 断言：`setenv("TMPDIR","/var/tmp"); EXPECT_EQ("/var/tmp", GetTempDir())` → 实测返回 “/tmp”。
- 实测证据：`ls /var/tmp` → No such file or directory；`mkdir /var` → Permission denied；/var 在 OHOS 上不存在。GetTempDir 按 stat 失败回退 /tmp，行为正确。
- 根因：Debian 专有目录 /var/tmp 在 OHOS 不存在，测试期望值 Debian 化。

**4) FileUtlTest.Popen（fileutl_test.cc:327）**
- 断言：`EXPECT_TRUE(ExecWait(Child,"PopenWrite"))`，错误栈含 “Sub-process PopenWrite returned an error code (100)”。
- 实测证据：测试写侧用绝对路径 `"/bin/bash" "-c" "read"`，而 `ls /bin/bash` → No such file or directory（OHOS 只有 /bin/sh）。fork 成功、execv("/bin/bash") ENOENT → 子进程 exit(100)。
- 根因：/bin/bash 缺失（OHOS 无 bash，仅有 toybox sh）。/bin 只读不可补。

**5) FileUtlTest.flAbsPath（fileutl_test.cc:335）**
- 断言：`chdir("/etc/"); flAbsPath("passwd")` 期望 “/etc/passwd”，实测 “/system/etc/passwd”。
- 实测证据：`ls -ld /etc` → `lrwxrwxrwx /etc -> /system/etc`。realpath 沿符号链接解析。
- 根因：OHOS 将 /etc 符号链接到 /system/etc，realpath 规范化结果不同。非 apt 缺陷。

**6) HashSumsTest.FileBased（hashsums_test.cc:38/78/88-91/102-105）**
- 断言：`FileFd input("/etc/os-release", ReadOnly); ASSERT_TRUE(input.IsOpen())` 失败；后续 hash 值对比为空 vs 预期。
- 实测证据：`ls /etc/os-release` → No such file or directory；`/system/etc/os-release` 亦不存在。该测试硬编码以 /etc/os-release 作为哈希样本，Debian 专有。
- 根因：OHOS 无 /etc/os-release。

**7) OpenMaybeClearSignedFileTest.TwoSimpleSignedFile/GarbageTop/GarbageBottom/BogusNoSig/BogusSigStart/StrangeDashArmorFile/StrangeDashMsgFile/StrangeDashSigFile（8 项，openmaybeclearsignedfile_test.cc:133/142）**
- 断言：`EXPECT_FAILED_PARSE()` 入口 `EXPECT_TRUE(_error->empty())`（line 133）与弹出消息相等（line 142）失败。
- 实测证据：失败弹出的 msg 是前序用例残留错误——“Sub-process PopenWrite returned an error code (100)”、
  “Could not open file /etc/os-release - open (2: No such file or directory)”、
  “Unable to determine file size for fd -1 - fstat (9: Bad file descriptor)”。
- 根因：apt 的全局 `_error` 栈是进程级共享；FileUtlTest.Popen（/bin/bash 缺失）与 HashSumsTest.FileBased
  （/etc/os-release 缺失）失败时遗留错误未清，污染后续用例。**单独运行本套件 15/15 全过**；
  全量剔除 FileUtl+HashSums 后 15/15 全过。clearsign 拆包/校验逻辑无缺陷。

### 结论
18 项失败 100% 归因于 OHOS 不可变 rootfs 缺失 Debian 专有文件/工具
（dpkg、/bin/bash、/var/tmp、/etc/os-release）及 OHOS 平台语义
（/etc→/system/etc 符号链接、/storage 屏蔽 others-read 位），全部有实测命令输出佐证，
**无一为 libapt-pkg 代码缺陷**。库的解析/哈希/版本比较/clearsign/配置等核心逻辑通过。

### 集成测试套件审计（test/integration，300 项存在但不可运行）

上游 apt 除 gtest 单测外，还有一套 bash 集成测试 `test/integration/`：
`run-tests` 以 `find . -regex '^\./test-[^/]*$'` 枚举，共 **300 个 `test-*.sh` 脚本**
（另有 7 个 `skip-*` 非测试文件、`framework`/`run-tests` 驱动、`Packages-*`/`status-*`
等 fixture 数据）。**本适配如实申报为"存在但不可运行"，未计入通过数，不伪造通过**：

- **不可运行根因（双重）**：
  1. 集成测试执行的是 `apt-get`/`apt-cache`/`apt-ftparchive`/`apt-helper` 等 **CLI 二进制**，
     而本交付按 R26 仅产出 `libapt-pkg`/`libapt-private` **静态库**（补丁 0014/0015
     `add_library SHARED→STATIC`，recipe `WITH_TESTS=OFF`），CLI 未构建；
  2. 集成测试依赖 dpkg/gpg/bash 等 Debian 工具链，OHOS rootfs 无
     `/usr/bin/dpkg`（`which dpkg` 无结果）、`/bin/bash`（仅 `/bin/sh`）、gpg。
- **计数口径**：上游测试总数 = 137（gtest）+ 300（集成）= **437**；
  可运行口径仅 gtest（119 过 / 18 环境失败），与 test_package/MANIFEST.yml
  `upstream_test_total: 437`、`upstream_test_gaps: [{count: 300, category: ohos_feature}]` 一致。

## 交付物

| 文件 | 说明 |
|------|------|
| patches/0001-0020 | 20 个 OHOS 适配补丁（行号已按 patch_ng 严格匹配重生成） |
| conanfile.py | Conan 2.x CMake 配方（cmake 构建，静态库） |
| conandata.yml | 源码 sha256 + 20 补丁清单 |
| test_package/ | 消费者测试：真实调用 libapt-pkg API + __OHOS__ 分支验证 |
| reports/ | conan-verify 日志与报告 |

### conanfile.py 关键配置

- `requirements()`（12 个运行期/编译期库）：libdb/5.3.35、zlib/1.3.1、bzip2/1.0.8、
  liblzma/5.8.1、lz4/1.9.4、libgcrypt/1.11.0、xxhash/0.8.2、libzstd/1.5.7、
  gnutls/3.8.10、systemd/261、libseccomp/2.5.5、eudev/3.2.14（eudev 提供 libudev）。
- `build_requirements()`（构建期工具）：triehash/0.3.1（apt CMake `find_program(TRIEHASH)` 硬性要求）、
  perl/5.42.2（`find_package(Perl)` 硬性要求）。**注意必须用 `build_requirements()` 方法名，
  Conan 2 没有 `tool_requires()` 方法**（实测报 `Wrong 'tool_requires' definition`）。
- `generate()`：`PkgConfigDeps` + `CMakeToolchain`。**PkgConfigDeps 必填** —— apt 的
  `CMake/FindLZMA.cmake`、`FindLZ4.cmake`、`FindZSTD.cmake`、`FindGCRYPT.cmake`、
  `FindXXHASH.cmake`、`FindSystemd.cmake`、`FindSECCOMP.cmake`、`FindUdev.cmake` 全部走
  `pkg_check_modules`，缺 .pc 时 configure 找不到任何库。
- `options/default_options`: `shared=False`（R26 静态）；`tc.variables`：`BUILD_SHARED_LIBS`、
  `CMAKE_BUILD_TYPE=Release`、`WITH_TESTS=OFF`。
- `package_info()`：`self.cpp_info.libs = ["apt-pkg"]`（静态库；CMakeDeps 会把 12 个
  requires 的链接链传给消费者）。
- 20 个补丁经 `export_conandata_patches`/`apply_conandata_patches` 随配方打包并按序打入。

## 注意事项

- test_package 使用真实 libapt-pkg API（pkgInitConfig/pkgInitSystem/pkgCacheFile 等），
  并含 `#ifdef __OHOS__` 鸿蒙特有断言，非空壳打印。
- 上游测试需在 conanrunenv（LD_LIBRARY_PATH 指向 conan lib）下运行，否则缺 libzstd/libsystemd/libgcrypt 运行库。
- 补丁 0007 被 0009 演进替代（同区域改写）；0001-0020 按序在 pristine 源码上用 patch_ng 可干净打入（实测全过）。

## `_system` 全局指针赋值机制（test_package pkgCacheFile 崩溃根因，R40 深层适配）

### 上游原貌（无需补丁）
- `pkgSystem *_system = 0;`（apt-pkg/pkgsystem.cc:24）—— 上游源码里**确实没有** `_system = Sys;` 这类显式赋值。
- 真实赋值机制：`pkgInitSystem(Configuration &Cnf, pkgSystem *&Sys)`（apt-pkg/init.cc:343）的
  第二参数是 **“指针的引用”**（`pkgSystem *&`）。apt-get/apt-cache 等二进制在
  `ParseCommandLine(..., &_system, ...)` → `pkgInitSystem(*_config, *_system)` 时把**全局
  `_system` 本身**传入；函数内部 `Sys = pkgSystem::GlobalList[I]`（init.cc:372）经引用
  **写回全局 `_system`**。`debSystem::Initialize()` 只设配置（Dir::State::status、
  Dir::Bin::dpkg 等），不碰 `_system`；`pkgCacheFile` 只**读** `_system` 不赋值。
- 结论：**上游原貌如此 → 属 a) 情况，按上游用法正确初始化即可，无需补丁。**

### 崩溃证据（实测）
- 错误用法：test_package/旧 test.cpp 用**局部变量** `pkgSystem *Sys` 调 `pkgInitSystem(*_config, Sys)`，
  全局 `_system` 仍为 0。随后 `pkgCacheFile::GetPkgCache()` 全链路：
  `BuildCaches()`（cachefile.cc:85）→ `pkgCacheGenerator::MakeStatusCache()`（pkgcachegen.cc:1686）
  → `_system->AddStatusFiles(Files)`（pkgcachegen.cc:1690）—— `_system==nullptr` 空指针解引用 → SIGSEGV。
- 实测 probe5（局部 Sys）backtrace：`pkgCacheFile::BuildCaches(+0xcc)` ← `pkgCacheFile::GetPkgCache(+0x28)`
  ← `main(+0x1a8)`，EXIT=1。
- 修复后 probe6（直接传全局 `_system`）：`pkgInitSystem ok=1 _system=0x… label="Debian dpkg interface"`，
  `GetPkgCache=0x… PackageCount=1`，EXIT=0。test_package/test.cpp 15/15 断言全过。
- 注意：apt-pkg 是静态库，若消费者传局部变量，链接器不会因此报错（`_system` 符号始终存在，
  只是值保持 0），所以该崩溃只有运行时才能暴露。

## conan-verify 最终结果（G0-G4 + L2/L4/L5 八道门禁全绿）

2026-10-06 重新执行 `python3 scripts/ohc-run.py conan-verify apt-pkg 2.7.14`（ohos-aarch64 profile），
`conan create` 全程成功（含 test_package 实跑），八道门禁全部 PASS：

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 预构建风险 | ✅ | cmake 构建系统，E092（CMake 不识别 HarmonyOS 平台）已在配方处理 |
| G1 配方完整性 | ✅ | name/version/source/build/package/package_info/export_sources/补丁应用/R26/test_package/MANIFEST 全齐 |
| G2 conan create | ✅ | 干净构建 + test() 实跑 14/14 断言全过（`apt-pkg test_package: OK (0 failures)`）|
| G3 系统同名库隔离 | ✅ | 无 .so 输出到系统路径，R26 通过（0014/0015 静态化）|
| G4 产物完整性 | ✅ | libapt-pkg.a 等产物在位 |
| L2 平台 smoke test | ✅ | 纯库包，无 bin/，跳过 |
| L4 静态安全扫描 | ✅ | 无 bin/，跳过 |
| L5 产物基线 | ✅ | 无 bin/，跳过 |

产物：`archives/a/apt-pkg/2.7.14/.conan-verified`（`verified_at=2026-10-06T19:14:58`）、
`reports/conan-verify-report.md`（Verdict: PASS）、`reports/conan-create.log`（test() 完整日志）。

### G2 修复：test() 运行时环境注入（曾报 Error loading shared library libgnutls.so.30）

- 现象（conan-create.log 285-295 行）：CMake configure/build 均成功，`cmake.test()` 阶段
  CTest 运行 `test_apt-pkg` 报 `Error loading shared library libgnutls.so.30`。LastTest.log 确认
  gnutls .so.30 缺位。知识图谱 E537（SONAME）命中是**误报**——真因是 test() 未注入 conan
  运行时环境（CTest 不带 LD_LIBRARY_PATH）。
- 修复（test_package/conanfile.py）：
  1. `test()` 不再用 `cmake.test()`，改为直接运行二进制：`self.run(f'LD_LIBRARY_PATH="…" "{exe}"')`。
  2. 新增 `_runtime_lib_dirs()`：遍历 `self.dependencies.values()`（含传递依赖），把每个依赖的
     `cpp_info.libdirs`（相对 `package_folder`）绝对化收集，再补 OHOS SDK
     `<sdk>/lib/aarch64-linux-ohos`（二进制 NEEDED `libc++_shared.so`，不在 conan 依赖图里），去重保序。
  3. 为什么必须全量遍历而非 `env="conanrun"`（VirtualRunEnv）：ohpcd 制品仓的 gnutls/3.8.10
     配方把 `LIBRARY_TYPE` 标成 **STATIC** 但包内实际只发 `.so`（无 `.a`），VirtualRunEnv 只收录
     声明 shared 的依赖 lib 目录，因此 conanrun 的 LD_LIBRARY_PATH 漏掉 libgnutls.so.30 所在目录。
     实测生成的 conanrunenv-release-armv8.sh 里 gnutls/nettle/gmp/libunistring 目录全部缺失；
     显式全量遍历后 test() 14/14 断言全过、`conan create` 全绿。
- 修复后实测（conan-create.log 275 行 RUN 命令）：LD_LIBRARY_PATH 覆盖 SDK libc++ + apt-pkg +
  libdb/bzip2/lz4/xxhash/gnutls/nettle/libtasn1/libgcrypt/libgpg-error/gmp/libunistring/systemd/
  liblzma/libzstd/zlib/libseccomp/eudev 全部 lib 目录。

## 鸿蒙特有测试描述

test_package/test.cpp（14 项断言，`#ifdef __OHOS__` 分支）：
1. `pkgInitConfig` 成功、`APT::Architecture` 非空且映射为 `arm64`（验证 0009 内嵌 dpkg 架构表在
   无 /usr/share/dpkg 时仍生效）；
2. `pkgInitSystem(*_config, _system)` 传全局 `_system`（上游原貌，见上节），验证 label
   "Debian dpkg interface"；
3. `debVS.CmpVersion` 四个版本比较断言（epoch 生效）；
4. `APT::String::Strip` 字符串工具；
5. `pkgCacheFile` 全链路：mkstemp 空 status 文件 → `GetPkgCache()` 构建出缓存 → PackageCount==0；
6. `_error->Discard()` 错误栈清理。

验证方式：conan create 的 test() 阶段直接运行二进制，返回码 0；G2 门禁据此判定 PASS。

## 最终状态

COMPLETED — apt-pkg 2.7.14 鸿蒙 aarch64 适配完成：编译 100%、20 补丁、上游测试 119/137（崩溃点证据充分）、
鸿蒙特有测试、conan-verify 8 门禁全过，W4 审计 pass（P0=0 P1=0），已提交 PR。
---

**编译结束**: 2026-10-06 23:28
**最终状态**: built
