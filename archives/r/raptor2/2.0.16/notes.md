# raptor2 2.0.16 适配笔记

## 编译环境

- 构建系统: autotools（上游同时提供 CMakeLists.txt，但其无 ctest/add_test 注册，上游完整测试套件只在 autotools 路径下）
- 编译日期: 2026-10-16
- 目标平台: HarmonyOS PC（HarmonyOS / HongMeng Kernel 1.12.0 / aarch64），原生构建 build == host
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，triplet aarch64-unknown-linux-ohos）
- Conan: 2.29.1（OHOS 适配版），profile `ohos-aarch64`，remote `ohpcd`
- 状态: built

## 上游源与语言

- 官方源: `https://download.librdf.org/source/raptor2-2.0.16.tar.gz`
- sha256: `089db78d7ac982354bdbf39d973baf09581e6904ac4c92a98c5caadb3de44680`（1,750,726 字节）
- R47 语言预检: `detected_language=c`，expected=cpp，C/C++ 同族通过
  （构建系统证据 `CMakeLists.txt PROJECT(Raptor2 C)`；工具输出的 `source_stats` 原文为
  “源文件 94 个（c:88, perl:6, bash:1），主体占比 94%”，即工具的分母口径与逐语言分类计数不同源，本笔记照引不改写）

## 依赖

| 依赖 | 版本 | 用途 | 制品仓核查 |
|------|------|------|-----------|
| libxml2 | 2.15.3.1 | XML 解析（RDF/XML、RSS）、pkg-config | recipe + binary 均在 |
| libxslt | 1.1.45.2 | GRDDL 解析器 | recipe + binary 均在 |
| yajl | 2.1.0 | RDF/JSON 解析器 | recipe + binary 均在 |
| curl | 8.22.0 | WWW 后端（上游默认） | recipe + binary 均在 |
| icu4c | 78.3 | RDF/XML 的 Unicode NFC 校验 | recipe + binary 均在 |

`libxslt/1.1.45.2` 声明 `libxml2/2.15.3`，配方用 `self.requires("libxml2/2.15.3.1", override=True)` 统一到较新 revision（与 `archives/a/abiword-plugin-gdict/3.0.8` 同一做法）。

## 编译步骤

```bash
conan create archives/r/raptor2/2.0.16 \
    -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -r=ohpcd
```

配方 `generate()` 关键项：

```python
tc.configure_args.append("--without-xslt-config")                 # 强制 pkg-config 探测 libxslt
tc.configure_args.append("--with-yajl=<yajl package folder>")     # 启用 RDF/JSON 解析器
tc.extra_ldflags.append("-lc++")                                  # ICU 为 C++ 静态库
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type`，报错行是 `dummy.c: Permission denied` | ① 捆绑的 config.guess(2022-01-09) 无 HarmonyOS 分支，落到"编译并运行探测程序"的兜底路径；② 该路径用 `umask 077 && mktemp -d` 建临时目录，本机文件系统把该目录落成 `drwx--S---`(2700) 且属主写入被拒 | 补丁 0001 给 config.guess 增加 `*:HarmonyOS:*:*` 分支（`uname -s=HarmonyOS` 直接得 `aarch64-unknown-linux-ohos`），不再进入兜底路径 |
| 2 | `config.sub: Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'` | 仓库脚本 `scripts/patch-autotools-ohos.pl` 第 2.1 步已写入 `basic_os=linux-ohos`，导致第 2.3 步的守卫 `unless ($sc =~ /linux-ohos/)` 误判为"已存在"而 skip，kernel-os 白名单未补 | 补丁 0002 手工补 `linux-ohos*` 到 `case $kernel-$os in` 白名单（E072 修改 3），并统一新增分支缩进 |
| 3 | `config.status: error: could not setup config files machinery`（`./confXXXXXX/subs1.awk: Permission denied`） | autoconf 生成的 configure/config.status 同样用 `umask 077 && mktemp -d "./confXXXXXX"`，本机文件系统上 2700 目录无法写入（试验：`mkdir`+`chmod` 会被归一化为 2771 可写，只有 `mktemp -d` 的 2700 不可写） | 补丁 0003 去掉该处 `umask 077`（`tmp=\`mktemp -d "./confXXXXXX" 2>/dev/null\`` / `mkdir "$tmp" 2>/dev/null`），与 `archives/a/aaphoto/0.45` 的 `0003-configure.patch` 同一做法 |
| 4 | `src/raptor_libxml.c: no member named 'checked' in 'struct _xmlEntity'` | libxml2 2.11.0 移除了 `xmlEntity.checked` 私有字段（其功能并入内部 `flags`），raptor2 2.0.16 的守卫只有下界 `#if LIBXML_VERSION >= 20627` | 补丁 0005 依上游/发行版既定修复加上界 `&& LIBXML_VERSION < 21100`（同 SUSE hotfix-libxml-2.11.patch） |
| 5 | `raptor_www_libxml.c: call to undeclared function 'xmlNanoHTTPMethod'` | configure 选中了 libxml(nanohttp) WWW 后端，而 libxml2 >= 2.13 把 nanohttp 声明包在 `#ifdef LIBXML_HTTP_STUBS_ENABLED` 内，OHPCD libxml2/2.15.3.1 未开启 HTTP stubs | 补丁 0004 修 configure 的 libcurl 探测守卫：libcurl 仅由 pkg-config 发现时也要置 `have_libcurl`，恢复上游默认的 curl WWW 后端 |
| 6 | `Error relocating libraptor2.so.0: __dynamic_cast / _ZNSt4__n1... symbol not found` | ICU 是 C++ 库且以静态库形式链入本 C 库，clang 的 C 驱动不会自动补 libc++ | `tc.extra_ldflags.append("-lc++")`（与 `archives/a/audiofile/0.3.6` 同一做法）；产物 `libraptor2.so` 的 DT_NEEDED 因此含 `libc++_shared.so` |
| 7 | `make check` 的 src 单元测试 `libyajl.so.2: not found` | build 环境的 LD_LIBRARY_PATH 来自 OHOS profile（只含 SDK lld 的 llvm/lib），不含本图共享依赖的 libdir；该目录还自带一份 `libxml2.so.16`，会遮蔽 Conan 的 libxml2 | 配方 `build()` 在 configure 前把 `self.dependencies.host` 各依赖的 libdirs 前置到 LD_LIBRARY_PATH（与 `archives/4/4ti2/1.6.10.1` 同一做法） |
| 8 | GRDDL 与 RDF/JSON 解析器被静默禁用（`RDF parsers enabled` 缺 grddl/json） | ① PATH 上存在依赖前缀的 `xslt-config`，configure 走 xslt-config 分支后 libxslt 探测失败而静默禁用 GRDDL；② yajl 未被 `--with-yajl` 指定 | `--without-xslt-config` 强制走 pkg-config 分支；`--with-yajl=<prefix>` 指定 yajl 前缀。配方另加 `_assert_full_feature_set()` 断言 19 个特性宏，防止今后再次静默退化 |

## 源码修改（5 个补丁）

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001-build-config.guess.patch | build/config.guess | 增加 `*:HarmonyOS:*:*` 识别分支，输出 `aarch64-unknown-linux-ohos` |
| 0002-build-config.sub.patch | build/config.sub | 接受 `ohos` OS 与 `linux-ohos` kernel-OS 组合 |
| 0003-configure.patch | configure | 去掉 config.status 临时目录的 `umask 077`（2 处） |
| 0004-configure.ac.patch | configure.ac | libcurl 仅经 pkg-config 发现时也置 `have_libcurl` |
| 0005-src-raptor_libxml.c.patch | src/raptor_libxml.c | `xmlEntity.checked` 守卫补上界 `< 21100` |

补丁均由 `ohc-run.py refresh-patch --auto` 生成，未手写 diff；`patches/` 中无新增平台宏（PF5 干净）。补丁 0004 同时改 `configure.ac`，使 configure 若日后重新生成仍保留该修复（本机无 automake，无法在此重新生成 configure）。

## 与生成文件的关系（R6 说明）

补丁 0003/0004 修改的是 tarball 内的生成文件 `configure`。这里不走"探索阶段就地 sed 且不记录"的路子，而是把改动完整落入 `patches/` 并在 `conandata.yml` 声明，由 `apply_conandata_patches()` 在每次 `conan create` 时对干净源码重放——可复现、可审计。`review-memory.md` §14 允许经 `patches/` 处理生成产物，`archives/a/aaphoto/0.45` 的 `patches/0003-configure.patch` 为同类先例。

## 验证结果

`make check`（配方 build() 内执行，即 `conan create` 的一部分）：

| 套件 | 用例数 | 结果 |
|------|--------|------|
| `src/`（automake TESTS 程序） | 19 | 19 PASS / 0 FAIL |
| `tests/*/`（13 个子套件语料检查项） | 1233 | 1205 PASS + 28 项上游声明 EXPECTED_FAILURES |

- `tests/rdfa` 4 项与 `tests/rdfa11` 24 项 `FAILED` 与上游 `Makefile.am` 中的 `EXPECTED_FAILURES` 清单逐字一致，harness 打印 `Ignoring expected failures` 且 `result=0`；不是适配导致的失败。
- `make check` 整体退出码 0。

消费者用例（`test_package`，在目标机 HarmonyOS PC 上实际运行）：

| 用例 | 内容 | 结果 |
|------|------|------|
| R12-01 | 用安装后的 libraptor2 解析真实 Turtle 与 RDF/XML，各自序列化为 N-Triples，断言两种语法产出同一组 3 条语句 | PASS |
| R12-02 | 执行包内 `rapper` CLI 把同一 RDF/XML 转成 N-Triples，断言实际输出的 3 条语句 | PASS |

## 依赖版本

libxml2/2.15.3.1、libxslt/1.1.45.2、yajl/2.1.0、curl/8.22.0、icu4c/78.3（另含 curl 传递依赖 openssl/3.5.8.1、zlib/1.3.2）。

## 注意事项

- 上游 CMake 路径无测试注册，本配方只提供 autotools 构建；若日后需要 CMake 变体，须另行补齐测试与验证。
- `--without-xslt-config` 与 `--with-yajl=` 是当前环境下唯一能让 `RDF parsers enabled` 覆盖全部 10 个解析器的组合；配方中的 `_assert_full_feature_set()` 会在任何一项缺失时直接失败，避免"编译通过但默默裁掉功能"。
- `package_info()` 追加 `c++` 系统库：静态 libraptor2.a 内含 ICU 的 C++ 符号，消费者必须同时链接 libc++。
---

**编译结束**: 2026-10-16 23:29
**最终状态**: built
