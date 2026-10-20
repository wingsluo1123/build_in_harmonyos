# DRAFT-pdl-2.104-ohos-perl-xs-module-packaging

OHOS 上适配 XS 版 Perl 模块的范式

## 使用说明

本条目面向：在 OHOS（HarmonyOS PC / 本仓 CI worker）上把**含 XS(C) 扩展**的 CPAN 模块打成 conan 包。
纯 Perl 模块不需要本条（走仓内既有范式：只把 lib/*.pm 拷进 site-lib 即可，不 require perl、不编译）。

按顺序做六件事：

1. **判定类型**：发行版里有 *.xs / Makefile.PL 会编 C 的，就是 XS 模块。
2. **确认构建期能执行 perl**：取制品仓里与 worker 同 OS 的 perl 包。
   本仓事实：CI worker 本身就是 OHOS 机器，所以 OHOS/armv8 的 perl/5.42.2.3 可直接执行。
   若 worker 与目标不同 OS，此路不通——需要 host 解释器或交叉方案，不要硬编。
3. **取解释器与复刻 PERL5LIB 枚举**：从依赖包目录取 bin/perl；同时枚举 perl 包的
   lib/perl5/{version, site_perl/version, vendor_perl/version}[/archname] 作为 PERL5LIB。
4. **未发布依赖随包（路线 A）**：conandata.yml 逐条固定 url+sha256，
   INSTALL_BASE=<私有 stage> 依序装好，再装本体。
5. **构建树内签名（顺序不能反）**：make 出来后、make install 之前，
   对每个 .so 执行 binary-sign-tool sign；OHOS 拒绝"先进 Conan 包缓存后签名"的 ELF。
6. **跑声明的测试子集**再打包：Test::Harness/prove；测试要加载 XS，所以要在签名之后跑。

## 适用范围

- 含 XS 的 CPAN 模块：JSON::XS、DBI/DBD::*、Text::CSV_XS、File::Map、PDL 等；
- 类比场景：任何"构建期必须执行被适配解释器才能编译扩展"的生态（Ruby mkmf、Python C 扩展）；
- 适用条件：① 制品仓有与 worker 同 OS 的解释器；② 依赖可能未发布；③ 产物含 ELF 需签名。

不适用：纯 Perl 模块；或 worker 与目标 OS 不同的交叉构建（那种情况需要另写 host 解释器方案）。

## 输入输出定义

- 输入：上游 CPAN tarball（url+sha256）、制品仓的 perl 解释器包、未发布依赖的 tarball 集合、
  目标 settings（os/arch/compiler）、可选的工具链配置 tools.build:compiler_executables。
- 输出：conan 包，其中 lib/perl5 下含本体与全部随包依赖的 .pm 与已签名的 .so，
  bin/ 下含脚本；package_info() 通过 PATH 与 PERL5LIB 暴露给消费者。
- 环境契约：消费者只需 conanrun 环境（PERL5LIB/PATH 由 package_info 提供），不额外配置。

## 示例（PDL 2.104，task #9406）

判定：PDL 的核心是 XS，属第二类；仓内 perl-* 全是纯 Perl 先例。

conandata（节选，全部 url+sha256 固定）：

    PDL-2.104.tar.gz:
      url: "https://cpan.metacpan.org/authors/id/E/ET/ETJ/PDL-2.104.tar.gz"
      sha256: "3d646ce3e1caac50c878639406ac27e5283e554daf9021ed86436314b21bf1e4"
    Devel-CheckLib-1.16.tar.gz:
      url: "https://cpan.metacpan.org/modules/by-module/Devel/Devel-CheckLib-1.16.tar.gz"
      sha256: "869d38c258e646dcef676609f0dd7ca90f085f56cf6fd7001b019a5d5b831fca"

构建顺序：

    perl Makefile.PL INSTALL_BASE=<stage>   # 4 个未发布依赖依序，再装本体
    make
    /data/service/hnp/bin/binary-sign-tool sign -i blib/arch/auto/PDL/Core/Core.so -o Core.so.signed
    perl -MTest::Harness -e 'runtests @ARGV' -- t/core.t t/basic.t ...
    make install

消费侧（CI 的 test_package 实测）：

    perl -MPDL -e 'my $a = pdl([[1,2],[3,4]]); print $a x $a;'

## 查重差异表

| 邻近条目 | 它讲什么 | 本条的差异 |
|---|---|---|
| DRAFT-cronutils-1.1-raw-makefile-ohos-cli-signing | 通用 ELF 签名流程（raw Makefile 场景） | 本条覆盖"解释器构建期可执行性 + 依赖闭包 + PERL5LIB 消费"整链，签名只是其中一步，且强调**签名必须在 make install 之前** |
| DRAFT-7640-jkmeter-0.9.0-signed-elf-chmod-eperm-defensive | 签名后 chmod 的 EPERM 防御 | 同属签名周边，本条不涉及 chmod 语义 |
| DRAFT-E077B-ohos-sdk-autocodesign-invalid | SDK 自动签名失效 | 本条不用 SDK 自动签名，用 binary-sign-tool 显式签 |
| DRAFT-jekyll-4.4.1-rubygems-app-ohos-packaging-and-upstream-execution | RubyGems 的闭包与预编译 gem 重标 | 同为"向制品仓提供语言生态包"，但 Perl 侧的隐式契约是 PERL5LIB 而 Ruby 侧是 stub 行；Perl 侧多一个"纯 Perl vs XS 分野"的判定 |
| 仓内 perl-* 配方（如 perl-file-which/1.27） | 纯 Perl：只拷 lib/*.pm | 本条处理 XS，必须真跑 Makefile.PL 与编译，并解决签名与工具链 |

## 验证证据

（全部在 CI worker 上实测取得）

| 环节 | 实测结果 |
|---|---|
| 构建 | 7 个源（PDL + Module-Build + Sub-Exporter-Progressive + Devel-CheckLib + File-Map + Test-Deep + Test-Warn）+ 2 个补丁，conan create 成功 |
| XS 编译 | PDL 自身 XS 模块全部编译通过（`blib/arch/auto/PDL/**`） |
| ELF 签名 | `[pdl] signed 18 XS objects`；构建树内先 `llvm-objcopy --remove-section .codesign`，再 `binary-sign-tool sign -inFile <f> -outFile <f>.signed -selfSign 1`，最后 `os.replace` + `chmod 755` |
| 上游测试 | `All tests successful.` / `Files=6, Tests=1510` / `Result: PASS`；执行的是 `t/core.t t/basic.t t/slice.t t/matrixops.t t/reduce.t t/ufunc.t` |
| test_package | `[ok] L1a: test_package was executed by conan create`；CI 汇总 `Pass rate: 100.0% (1/1)` |
| CI 汇总 | 构建 #90914 `results=0 build successful`；L0/L1/L4/L5 全 pass |

- 任务材料：`tasks/pdl-2.104-2026-10-01/01-DEPENDENCY-ANALYSIS.md`
- 配方：`archives/p/pdl/2.104/conanfile.py`（`_perl5_roots` / `_relocate_perl_config` / `_perl_core_dirs` / `_sign_tree` / `_run_tests`）
- 补丁：`patches/0001-file-map-drop-test-prereqs.patch`、`patches/0002-pdl-nopthread-dummy-versions.patch`
- 关于 L2：CI 源码里该检查明确标注 non-blocking（`[warn] L2: <bin> --version/--help failed (non-blocking)`）。它在**脱离 conan 运行环境**的情况下直接执行 `bin/pdl --version`，缺少 PERL5LIB 必然失败，属测试装置产物，不是打包缺陷。

## XS 落地逐关踩到的坑（均有 CI 日志证据）

| # | 现象 | 根因 | 修法 |
|---|---|---|---|
| 1 | `Can't open perl script "Makefile.PL"` | 该发行版只有 `Build.PL`（Module::Build 系） | 增加 Build.PL 分支：`perl Build.PL --install_base <stage>` + `perl Build` + `perl Build install` |
| 2 | `Can't locate Module/Build.pm in @INC` | `INSTALL_BASE=<stage>` 的模块落在 `<stage>/lib/perl5`，而 PERL5LIB 只放了 `<stage>` | PERL5LIB 必须含 `<base>/lib/perl5` 及其 archname 子目录 |
| 3 | `Undefined subroutine &warnings::register_categories`、`vars.pm BEGIN 失败` | **PERL5LIB 过度扩张**：把模块目录下的一级子目录（如 `<ver>/encoding`）也当模块根放进 @INC，于是 `require warnings` 命中 `encoding/warnings.pm`，核心 warnings 包失效 | PERL5LIB 只放**真正的模块根**：`lib/perl5`、版本目录、含 `-` 的 archname 目录、`site_perl/<ver>[/<arch>]` |
| 4 | `./Build` 报 `Test::Fatal/Test::Warnings is not installed` 后 rc=255 | Module::Build 的前置读自 `Build.PL`（不是 META.json） | 补丁从 `Build.PL` 的 `test_requires` 与 `%fallback_build_requires` 去掉 test 期前置（保留 runtime 依赖） |
| 5 | `Error: no compiler detected to compile lib/File/Map.c` | perl 的 `Config.pm` 里 `cc=/bin/sh /data/service/hnp/bin/clang`，CBuilder 按 shell 拆分后执行 `sh <ELF>`，试编译必然失败 | `ExtUtils::CBuilder::Base.pm:40` 认 `$ENV{CC}`：把 CC/LD 规范化成单个真实存在的编译器路径（CI 的 PATH 不含 `/data/service/hnp/bin`，须绝对路径） |
| 6 | `Failed to opendir '/lib/perl5/.../CORE' to find header files` | 本仓 perl 包**不可重定位**：Configure 用 `-Dprefix=/`，`Config.pm` 的 `archlibexp` 等被写死成 `/lib/perl5/...`，实际文件在 `<perl包>/lib/perl5/...` | 把修正过路径的 `Config.pm`/`Config_heavy.pl` 放进 stage（PERL5LIB 优先于内置路径）；XS 头文件再用 `CPATH` 指向真实 CORE 目录兜底 |
| 7 | XS 加载报 `pthread_setcanceltype: symbol not found` | PDL 的 pthread 支持直接调用该 libc 符号，而 OHOS libc 不导出；且仓内 sysroot 的 `libpthread.a` 是空占位，使 `check_lib` 探测**假阳性**，于是照常链接 `-lpthread` 并定义 `PDL_PTHREAD` | 置空 `POSIX_THREADS_LIBS`，走上游文档化的「without POSIX thread support」配置 |
| 8 | 关闭 pthread 后又报 `pdl_pthread_realloc_vsnprintf` / `pdl_pthread_free: symbol not found` | 上游 `pdlmagic.c` 的 `#else`（`/* Dummy versions */`）只补了 4 个 pthread 助手里的 2 个，另两个仍被未加保护的代码调用 | 补丁补齐这两个 dummy（调用点在无 pthread 时运行期不可达，行为不变） |
| 9 | 签名后 `signed 0`（全部失败） | 参数名用错（`-i/-o`） | 用权威参数：`binary-sign-tool sign -inFile <f> -outFile <f>.signed -selfSign 1`，并先清除旧 `.codesign` |
| 10 | 消费端 `Can't locate File/Which.pm in @INC` | `package_info` 的 PERL5LIB 只含本包与 perl 包，未含其他依赖包 | `package_info` 里遍历所有依赖的 `lib/perl5`（复用 `_perl5_roots`），并同时写入 `buildenv_info` |

> 通用价值：第 3、6、7、8 关是本平台 Perl 生态的**共性缺陷**（@INC 构造、perl 包可重定位性、libpthread 空占位、上游 no-pthread 分支不完整），任何在 OHOS 上打包/编译 Perl 模块的配方都会遇到；第 1、2、4、9、10 关是 Perl 发行版构建系统与 conan 打包契约的差异。
