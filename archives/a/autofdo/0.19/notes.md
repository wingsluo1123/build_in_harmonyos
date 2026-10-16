# autofdo 0.19 适配笔记（HarmonyOS PC / OHOS aarch64 原生 build=host）

## 基本信息
- 上游：https://github.com/google/autofdo  tag `0.19`（commit `492384d08687b8b5bdbd2c49aa3436ac69380de3`）
- 源码 tarball：`https://github.com/google/autofdo/archive/refs/tags/0.19.tar.gz`
  sha256 `2ab3a16a8966b6e9a877fddb15ee39e627646fcf8d0df17c19de013da36c27d0`
- 构建系统：autotools（本地 native，非交叉编译，**不使用 --build/--host/--target**）
- 产物：CLI 工具 `create_gcov` `dump_gcov` `sample_merger` `profile_merger`
  `profile_diff` `profile_update` `create_llvm_prof`
- 编译器：clang 15（`/data/service/hnp/bin/clang{,++}`），libc++

## 上游结构的两个关键事实（决定适配方案）

1. **tag tarball 不含 git 子模块内容**（E150）：
   `third_party/protobuf`、`third_party/perf_data_converter` 只有空目录 + `.gitmodules`。
   子模块 pin（`git ls-tree 0.19 third_party/` 读出）：
   - `third_party/protobuf` @ `a72da27f5a46844e1a70725bb4362c2e51d7195d`（protobuf 3.5.2）
   - `third_party/perf_data_converter` @ `d9ef70b46e63ebaec6d2d296aa178e332c6e5f58`
   处理：`perf_data_converter` 按 E150（manual-download）单独下载源码，放入
   `third_party/perf_data_converter`（只取 `src/quipper/*`，跳过约 100MB testdata）；
   `third_party/protobuf` 改用 **Conan 制品 `protobuf/3.17.3`**（含 `protoc` + `libprotobuf`）。

2. **tag tarball 不含生成的 autotools 产物**：只有 `configure.ac` / `Makefile.am` /
   `config.h.in`，**没有** `configure` / `Makefile.in` / `aclocal.m4` / `config.guess`
   等（但含自带的 `base/`、`glog/`、`gflags/`、`symbolize/` 源码）。故 `build()` 必须先
   自举（aclocal/autoconf/autoheader/automake）。

## 适配方案（conanfile.py）

- `requires`：`protobuf/3.17.3`、`openssl/3.5.6`、`libelf/0.8.13.1`。
- `tool_requires`：`autoconf/2.72`、`automake/1.18`（本机 `/data/service/hnp/bin` 无
  automake）。**不使用** `libtool`（autofdo 的 configure.ac 不依赖 libtool；树内
  bundled protobuf 已被 Conan protobuf 取代）。
- **子模块的真实依赖（实测；configure.ac 的 `AC_CHECK_LIB` 看似"可选探测"，实为必需）**：
  `third_party/perf_data_converter` 的 quipper 代码真实使用
  - `openssl`：`quipper/binary_data_utils.cc` `#include <openssl/md5.h>` + `MD5()`；
  - `libelf`：`quipper/dso.cc` `#include <libelf.h>`/`<gelf.h>`，调用
    `elf_version/elf_begin/gelf_getshdr/elf_getdata/gelf_getnote/elf_end` 等。

  缺 openssl → 编译期 `openssl/md5.h file not found`；缺 libelf → 编译期
  `libelf.h not found` + 链接期缺 `-lelf`。故二者必须显式 `requires`。
  configure.ac 的 `AC_CHECK_LIB([crypto],[MD5])` / `([z],[gzopen])` 分别由
  openssl(`-lcrypto`)/zlib(`-lz`，protobuf 传递) 满足；zlib 源码未直接用。
  **libelf 必须用本仓 OHOS 移植版 `libelf/0.8.13.1`**（0.8.13 的头经 `elf_repl.h`
  自带 Elf32_/Elf64_ typedef，会与 SDK `<elf.h>` 冲突，见补丁/问题表）。
- `build()` 用 **make 变量覆盖** 绕过树内 bundled protobuf 子构建：
  `make -j1 PROTOC=<conan protoc> PROTOBUF_DEP=`
  （`LIBELF` **不再置空**：`dso.cc` 真实用 libelf，需 `-lelf`，由 libelf 依赖经
  AutotoolsDeps 注入。不改 `Makefile.am`——`.am` 改动需 automake 重生成
  `Makefile.in`，且 `Makefile.in` 是生成文件（R6））。
- **LLVM（create_llvm_prof）**：ohpcd 的 `llvm/15.0.4` 二进制包服务器端损坏，不能作
  `requires`；改用平台 SDK 自带 `llvm-config`（15.0.4，build=host 即本机原生 LLVM），
  configure 以 `--with-llvm=<llvm-config>` 指定，链接 `-lLLVM-15`（见补丁 0004）。
  但 autofdo 0.19 的 `llvm_profile_writer.{h,cc}` 写的是 **LLVM 7 时代 SampleProf API**，
  与 LLVM 15 不兼容，需补丁 0002/0003（见下）。

## 补丁（8 个，全部 `portability`）

| 补丁 | 目标文件 | 作用 |
|---|---|---|
| 0001-base-port.h.patch | `base/port.h` | OHOS/musl 的 `<byteswap.h>` 提供 `bswap_16/32/64` **宏**；原码只在 `__GLIBC__/__CYGWIN__` 分支 include 它，OHOS 落入 `#else` 自定 `static inline bswap_16` 与宏冲突（`redefinition of '__bswap_16'`）。把 `__OHOS__` 并入该 include 分支 |
| 0002-llvm_profile_writer.cc.patch | `llvm_profile_writer.cc` | LLVM 15 SampleProf API：`SampleProfileMap` 以 `SampleContext` 为键；`FunctionSamplesMap` 以 `std::string` 为键。按 `LLVM_VERSION_MAJOR >= 15` 守卫改键构造与 `.str()` |
| 0003-llvm_profile_writer.h.patch | `llvm_profile_writer.h` | 同上（头文件侧）：`AutoFDOProfileMap` 别名（LLVM>=15 为 `SampleProfileMap`，否则 `StringMap<FunctionSamples>`），`ConvertProfiles()/GetProfiles()/profiles_` 统一用该别名 |
| 0004-m4-ax_llvm.m4.patch | `m4/ax_llvm.m4` | OHOS SDK 的 LLVM 只有单一共享库 `libLLVM-<major>.so`（无分组件共享对象）；shared 分支改为链接整库 `-lLLVM-<major>`（由 `llvm-config --version` 取主版本），（探测 `-lLLVM<Part>` 失败的错误信息不再进入 `LIBS`） |
| 0005-profile_creator.cc.patch | `profile_creator.cc` | OHOS/musl `<string.h>` 无 GNU `basename`；`__OHOS__` 下用等价实现取路径最后一段 |
| 0006-sample_reader.cc.patch | `sample_reader.cc` | 同上：`MatchBinary` 的 `basename` 按 `__OHOS__` 走等价实现 |
| 0007-symbolize-elf_reader.cc.patch | `symbolize/elf_reader.cc` | OHOS/musl 不定义 `__WORDSIZE`（glibc 专有）；`#if __WORDSIZE == 32/64` 全假 → `#error "Invalid word size"`；`__OHOS__` 下取 `Elf64` |
| 0008-third_party-perf_data_converter-src-quipper-dso.cc.patch | `third_party/.../quipper/dso.cc`（子模块） | 该文件按 glibc/elfutils 语义用 libelf：Riepe libelf 无 `ELF_C_READ_MMAP`（其 `ELF_C_READ` 即 mmap 读），且 0.8.13.1 已实现但未声明 `gelf_getnote`；`__OHOS__` 下补等价别名与函数声明 |

## 遇到的问题与解决

| # | 现象 | 根因 | 解决 |
|---|------|------|------|
| 1 | Release tarball 的 `third_party/{protobuf,perf_data_converter}` 为空 | GitHub archive 不含子模块（E150） | 单独下载 perf_data_converter 到树内；protobuf 用 Conan 制品 |
| 2 | `configure: inaccessible or not found` | conan `get()` 默认 `keep_permissions=False`，丢掉可执行位 | `get(..., keep_permissions=True)` |
| 3 | 无 `configure`（tarball 不含） | tag tarball 未提供生成物 | `build()` 自举 aclocal/autoconf/autoheader/automake |
| 4 | automake 报 `Can't load .../Cwd.so: Perl_my_cxt_init: symbol not found` | conan automake 的 perl 脚本 shebang 指向**系统 perl 5.42.0**；conanbuild 的 `PERL5LIB` 指向 conan perl 5.42.2 的 XS 模块，版本不符 | 自举时把 `PERL5LIB` 收窄为 automake 纯 perl 模块目录 `share/automake-1.18` |
| 5 | aclocal 调 conan `autom4te` 报 `Can't locate strict.pm` | conanbuild 把 `AUTOM4TE/AUTOCONF/AUTOHEADER` 指向 conan autoconf（走 conan perl），与收窄后的 PERL5LIB 冲突 | 自举时 `unset AUTOM4TE AUTOCONF AUTOHEADER ...`，统一用系统 autoconf（`/data/service/hnp/bin` 在 PATH 首） |
| 6 | `config.status: ./confXXXXXX/subs1.awk: Permission denied` → `could not setup config files machinery` | E114：鸿蒙安全框架拦截 config.status 在**新建**临时目录写文件 | 预建可写目录并设 `TMPDIR`，把生成的 `configure` 的 `ac_tmp` 指到该目录、去掉退出删除的 trap（`_fix_ac_tmp()`） |
| 7 | `could not detect LLVM version 5 (or higher) libraries` | OHOS SDK 的 LLVM 只提供单一共享库 `libLLVM-<major>.so`，而 `llvm-config --libs <component>` 报告的 `-lLLVM<Part>` 全不存在 | 补丁 0004（shared 分支改链整库） |
| 8 | `No rule to make target '.../perf_data_converter/src/quipper/perf_data.proto'` | conan `get(pattern=...)` 对**解压前**成员路径（含顶层目录）做 fnmatch，`src/quipper/*` 匹配不到 | 改为 `pattern="*/src/quipper/*"` |
| 9 | `openssl/md5.h file not found`（`quipper/binary_data_utils.cc`） | 子模块真实依赖 openssl，原配方误判为"可选探测" | `requires("openssl/3.5.6")` |
| 10 | `libelf.h file not found`（`quipper/dso.cc`） | 子模块真实依赖 libelf，原配方误判为未使用 | `requires("libelf/...")` + 保留 `-lelf` |
| 11 | `typedef redefinition ... 'struct Elf32_Ehdr' ...`（`libelf/elf_repl.h` vs SDK `<elf.h>`） | 0.8.13 的 `sys_elf.h` 未被 configure 指向系统 `elf.h`，回退到自带 `elf_repl.h` | 换本仓 OHOS 移植版 **`libelf/0.8.13.1`**（sys_elf.h 用系统 `<elf.h>`，并补 `GElf_Nhdr/GElf_Versym/gelf_getnote`） |
| 12 | `redefinition of '__bswap_16'`（`base/port.h`） | OHOS/musl 的 `<byteswap.h>` 用宏提供 `bswap_16`，与 port.h 的 `#else` 分支函数定义冲突 | 补丁 0001 |
| 13 | `use of undeclared identifier 'gelf_getnote'` / `ELF_C_READ_MMAP`（`quipper/dso.cc`） | Riepe libelf 无 `ELF_C_READ_MMAP`；0.8.13.1 实现了 `gelf_getnote` 但 gelf.h 未声明 | 补丁 0008 |
| 14 | `#error "Invalid word size"`（`symbolize/elf_reader.cc`） | OHOS/musl 不定义 `__WORDSIZE` | 补丁 0007 |
| 15 | `no viable conversion ... SampleProfileMap` / `no viable overloaded operator[] ... FunctionSamplesMap`（`llvm_profile_writer.cc`） | autofdo 0.19 写的是 LLVM 7 时代 SampleProf API，与 LLVM 15 的 `SampleContext` 键/`std::string` 键不兼容 | 补丁 0002/0003 |

## 依赖版本
- protobuf/3.17.3（Conan，protoc + libprotobuf；zlib 由其传递）
- openssl/3.5.6（Conan；quipper 的 MD5）
- libelf/0.8.13.1（Conan，本仓 OHOS 移植版；quipper 的 elf_*/gelf_*）
- perf_data_converter @ d9ef70b（源码，`third_party/perf_data_converter`）
- LLVM 15.0.4（平台 SDK `llvm-config`；ohpcd 的 llvm/15.0.4 二进制包服务器端损坏，见下）

## 已知平台/基础设施问题（不是本配方能修的）
- **ohpcd 的 `llvm/15.0.4` 二进制包在服务器端损坏**：
  `Recipe llvm/15.0.4:<pkg> is corrupted in the server, it doesn't contain a conan_package.t file`。
  故无法作为 `requires`；`create_llvm_prof` 改用平台 SDK 自带 `llvm-config`（15.0.4）。

## 验证结果（设备真机，OHOS/aarch64 原生 build=host）

### A. 构建（conan create）
- 入口：`porting run --workspace <wt> --expect-branch feat/autofdo-0.19 -- ohc-run.py
  conan-verify autofdo 0.19 --profile <根仓库 ci/conan/profiles/ohos-aarch64>`
- 结果：**PASS**（G0/G1/G2/G3/G4/L2/L4/L5 全绿）
- 报告：`reports/conan-verify-report.md`；完整日志 `reports/conan-create.log`
- 7 个 CLI 全部编译+链接成功：`create_gcov` `dump_gcov` `sample_merger`
  `profile_merger` `profile_diff` `profile_update` `create_llvm_prof`

### B. 测试计数（同一张表用同一单位：断言数）
| 来源 | TOTAL | PASS | FAIL | SKIP | NOT_RUN |
|---|---|---|---|---|---|
| 上游测试（autotools，无 TESTS/check-local） | 0 | 0 | 0 | 0 | 0 |
| 消费者测试 test_package（7 工具 × 2 调用 × 2 断言） | 28 | 28 | 0 | 0 | 0 |
| CI 同构 L2 烟测（7 个二进制 `--version`） | 7 | 7 | 0 | 0 | 0 |
| 鸿蒙特有测试 | 0 | 0 | 0 | 0 | 0 |

上游测试：`TOTAL=0`（无 `TESTS`/`check_PROGRAMS`/`check-local`，清点见下节），非"跳套件"。
消费者测试逐项 `ok:` 行（14 行）见 `reports/conan-create.log`；`create_llvm_prof`
是真实构建产物（`-lLLVM-15` 链接平台 SDK LLVM 15.0.4）。

### C. CI 同构（`ci/conan/build_and_test.sh`）
- 入口：`porting run ... -- env CI_PACKAGES=archives/a/autofdo/0.19
  CI_REPO_ROOT=<wt> CONAN_PROFILE=<根仓库 profile> CI_BRANCH=feat/autofdo-0.19
  zsh <framework>/ci/conan/build_and_test.sh`（`JUNK_PR_DIFF` 指向本 PR 文件清单）
- 结果：**PASS**（exit 0）
  - L0：全通过（G0 pass / KC pass / JC pass / L0i 依赖全部 in registry
    〔autoconf/2.72 automake/1.18 libelf/0.8.13.1 openssl/3.5.6 protobuf/3.17.3〕/
    L0j version not in registry yet（首发布）/ L0k commands.json valid (type=tool)/
    L0m 结构 valid / L0n 分支 `feat/autofdo-0.19` 精确匹配 `autofdo-0.19`）
  - L1：pass（test_package executed）；L1e 反向破坏测试 **确认 test 真实依赖被测包**
  - L2：pass（7 个二进制 `--version` 全部 OK）
  - L4：pass（patches clean）；L5：pass（bin/ has content）
  - Build Summary：Total 1，Success 1，Failed 0，Pass rate 100%

### 未验证 / 限制
- **未做平台写入**（push / PR / 提审 / 合入 / 制品上传）——按流程由主会话执行；
  本结果只支持 `status: built`，不支持 `published`（release upload 未做）。
- 独立审查（W4/R52）未在本 attempt 执行（本 attempt 只负责实现+门禁）。
- `reports/` 内容与 `.conan-verified` 标记为 gitignored 本地证据，不随 PR 提交。

## 上游测试
autofdo 0.19 的 autotools 工程**没有** `TESTS` / `check_PROGRAMS` / `check-local`
目标（清点：`grep -nE 'check_PROGRAMS|TESTS|check-local' Makefile.am configure.ac` 无输出），
即无上游自动化测试可跑（R51 清点证据）。门禁依赖 `test_package` 对每个 CLI 的真实调用。

## test_package（消费者测试）
真实 exec 7 个 CLI，逐工具 `--help`（断言 exit=1 —— bundled gflags 的文档化行为，
且 gflags 帮助里 flag 以**单破折号**列出 —— 并断言输出含该工具自身 flag）与
`--version`（断言 exit=0 且输出含工具程序名），共 7×2=14 次调用、28 项断言；
经 `VirtualRunEnv`/`conanrun` 注入包 bin，用 bash 运行（OHOS `/system/bin/sh` 执行
ELF 不可靠）。详见 `test_package/MANIFEST.yml`。
