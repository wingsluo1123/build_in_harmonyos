# pkgfile 25 OHOS 适配笔记

> 状态：**真机 shadow CI 单包验证通过**（L0/L1/L2/L4/L5 全 pass，Build Summary 1/1 100%；
> 上游测试 **38/38 全部实跑通过**）。
> 验证提交：`915734921aee0c7055b044a45f7b4e8227cffb36`（真机侧构造内容等价提交；
> 本地 `feat/pkgfile-25` 的配方/补丁/测试内容与之相同，其后仅元数据文案更新）
> 运行目录（真机）：`~/ohpc-ci-shadow/runs/915734921aee-20261014T044650Z-21173`
> （同一内容此前在 `f3f9ee1553cc…` / `16bfd1eb…` 上也全绿；期间上游 `main`
> 由 `06bbd38c` → `d2280019` → `6425af51` 前进，补丁每轮均 clean 应用）

## 1. 库信息

| 项 | 值 |
|----|----|
| 上游 | https://github.com/falconindy/pkgfile |
| 版本 | 25（上游 tag `v25`，commit `fd5cf24576856bf705b320f4f02f3d4d15a3a7da`） |
| 源码 | `https://github.com/falconindy/pkgfile/archive/refs/tags/v25.tar.gz` |
| sha256 | `dc18d7fcb03844bfd9857cb7b05b666d8a3469a38c73d3182da05fd4f8dd6403`（452028 字节） |
| License | MIT |
| 构建系统 | **Meson**（`meson.build` + `meson_options.txt`，meson_version >= 0.56） |
| 语言标准 | C++20（`default_options: ['cpp_std=c++20']`） |
| 产物 | CLI `bin/pkgfile`（上游另有 systemd 守护进程 `pkgfiled`，本适配关闭） |
| 包类型 | `application`（纯可执行文件，无库/头文件导出） |

sha256 取信方式：codeload.github.com 与 gh-proxy.com 两条独立链路下载得到同一 sha256，
且解包后的 `meson.build` 与 raw.githubusercontent.com 单独抓取的 v25 原始文件
逐字节一致（sha256 `3a1bc94a6b5f38982098fec3aaf4a90939befec5036bb6fca690c730836ea858`）。

## 2. 真机环境（实测）

| 项 | 实测值 |
|----|-------|
| 设备 | HarmonyOS aarch64（HongMeng Kernel 1.12.0，Toybox） |
| 编译器 | clang 15.0.4（`~/usr/local/bin/clang-15`），sysroot `~/usr/local/sysroot` |
| C++ 运行库 | libc++ 15.0.4（libcxx-ohos），共享 `libc++_shared.so`；musl（`/lib/ld-musl-aarch64.so.1`） |
| `/bin/sh` | **mksh R59（MIRBSD KSH）** —— 不是 bash/dash |
| `/tmp` | **只读**（`Read-only file system`） |
| conan | 2.29.1（隔离 job 内 `PYTHONUSERBASE` 安装） |
| 网络 | `conan.cnb.cool`、`gitcode.com`、`gh-proxy.com` 可达；**`github.com` 直连超时** |
| CPU | 20 核 |

网络结论对应处置：`conandata.yml` 保持**官方源 URL**（R39），依赖 CI
`build_and_test.sh` 的 “Mirror fallback: rewriting source URLs” 步骤改写为
`gh-proxy.com` 镜像；不改配方 URL、不跳过 sha256 校验。

## 3. W0 依赖发布检查（适配第一步，R36）

检查方式：`conan download <ref> -r=ohpcd --only-recipe`（R35：不用 `conan list` 判二进制）。

| 依赖 | 上游要求 | ohpcd 状态 |
|------|---------|-----------|
| `pcre` | `dependency('libpcre', version: '>= 8.30')` | ✅ `pcre/8.45`（静态） |
| `libarchive` | `dependency('libarchive', version: '>= 3.2.0')` | ✅ `libarchive/3.8.7`（**shared**，产物 `libarchive.so.13`） |
| `curl` | `dependency('libcurl')` | ✅ `curl/8.15.0.1`（shared，`libcurl.so`） |
| `libsystemd` | `dependency('libsystemd')`（**无条件**） | ❌ **ohpcd 0 命中** |
| `gtest` / `gmock` | `dependency('gtest'/'gmock', required: false)` | ✅ `gtest/1.17.0(.1/.2)`、`gmock/1.17.0` |
| 构建工具 | meson / ninja / pkg-config / pod2man | meson ✅`1.11.0`、ninja ✅`1.12.1`、pkgconf ✅`3.0.5`、pod2man ❌（OHOS 无 perl） |

结论与处置：

- `libsystemd` 无制品，但它只被 `pkgfiled`（systemd 专属守护进程）使用；
  上游 `INSTALL` 列出的运行期依赖只有 libcurl / libarchive / pcre / pthreads，
  **不含 libsystemd**。按工作流「可选依赖缺失 → 最小化关闭可选功能」处置，
  不新建依赖库 PR、不把依赖适配混入本 PR。
- `pod2man` 属于 man 页生成，与工具功能无关，同样关闭。
- 真机构建实测：**全部依赖命中 ohpcd 预编译包**（日志 `Skipped binaries` 列出
  libarchive/openssl/pcre/xz/zlib/gmock/gtest/meson/ninja/pkgconf），
  无源码重建，构建为轻量任务。

## 4. 适配问题与处置（共 15 项，全部真机实证）

### 4.1 预分析阶段（源码/构建系统静态分析）发现

| # | 问题 | 根因 | 处置 |
|---|------|------|------|
| 1 | `dependency('libsystemd')` 无条件，configure 必失败 | 上游把守护进程依赖写在顶层；OHOS 无 systemd、制品仓无 libsystemd | **补丁 0001**：新增 meson 选项 `daemon`（默认 true）门控 libsystemd/pkgfiled/systemd units；构建时 `-Ddaemon=false` |
| 2 | `find_program('pod2man')` 为硬要求，configure 必失败 | 上游 man 页用 pod2man 生成；OHOS 无 perl | **补丁 0002**：新增 `man_pages` 选项（默认 true）门控 pod2man 与两个 man custom_target；构建时 `-Dman_pages=false` |
| 3 | 上游 `default_options: cpp_std=c++20` 被静默降级为 C++17 | CI profile `compiler.cppstd=17`；MesonToolchain 用 `compiler.cppstd` 生成 machine file 的 `cpp_std`，优先级**高于**项目 `default_options` | `configure()` 内 `self.settings.compiler.cppstd = "20"`（apache-arrow/24.0.0 同口径）。真机日志确认 `compiler.cppstd=20` 生效 |
| 4 | `std::format` 在 OHOS SDK 上不可用（6 文件 44 处） | clang 15 + libc++ **15004** 的 `<format>` 头存在但 `std::format` 默认不暴露 | OHOS 上追加 `_LIBCPP_ENABLE_EXPERIMENTAL` 与 `-lc++experimental`（asyncpp/0.2.4、libpqxx/8.0.1 同口径）。真机编译链接全通过 |
| 5 | 上游 `dependency('libpcre')` 找不到 | pcre 配方未声明 `pkg_config_name`，PkgConfigDeps 默认只生成 `pcre.pc` | 消费侧 `PkgConfigDeps.set_property("pcre","pkg_config_name","libpcre")`，**不改上游 meson.build** |
| 6 | `find_program('pkg-config')` 需可用 | 上游当硬要求用 | `tool_requires("pkgconf/3.0.5")`（另见 #12 真机追加处置） |
| 7 | `update.cc` 在 `TMPDIR` 未设时回落 `/tmp` | OHOS 沙箱 `/tmp` 只读（E002） | test_package 脚本显式设 `TMPDIR`/`TMPPREFIX`（另见 #15 真机追加处置） |
| 8 | `meson add_install_script` 在 DESTDIR 下建 `/var/cache/pkgfile` | 上游编译期默认缓存目录 | `package()` 内删除包内空 `var/` 树。真机实测包树确认 `var removed OK` |
| 9 | 产物脱离 `LD_LIBRARY_PATH` 时 `pkgfile --version` 起不来 → CI L2 失败 | Conan 的 `MesonToolchain` 只注入 `-Wl,-rpath-link`（链接期），不写运行期 rpath；而 `ci/conan/build_and_test.sh:1680` 与 `scripts/ohc/conan_verify.py:816` 都是裸执行 `bin/pkgfile --version` | `generate()` 内为全部 host 依赖补 `-L` + `-Wl,-rpath,<libdir>`（akku/1.1.0、bsdtar/3.7.7 同款）。真机 `L2: pkgfile --version OK`；`llvm-readobj` 确认 RUNPATH 含各依赖 lib 目录 |

### 4.2 真机构建过程中实测新增

| # | 现象（真机原始报错） | 根因 | 处置 |
|---|--------------------|------|------|
| 10 | `ERROR: Unknown linker(s): [['llvm-ar-15'],['llvm-ar'],['ar'],['gar']]`（四个裸名全部 ENOENT） | OHOS 上 **posix_spawn 不搜索 PATH**：meson 探测静态归档器用裸名 exec，即使 `ar` 确实在 PATH 中也报 “No such file or directory”；pkgfile 用 `static_library()` 构建 libcommon.a，归档器是必需项 | 新增 `_abs_tool()`：按 PATH → `~/usr/local/bin` → `/data/service/hnp/bin` 解析绝对路径，写入 `tc.binaries["ar"/"as"/"strip"/"nm"/"ranlib"]`（appstream/1.2.0 同款） |
| 11 | `ERROR: Could not get define 'ARCHIVE_FILTER_ZSTD'` | 上游 `meson.build:18` 用 `cpp.get_define('ARCHIVE_FILTER_ZSTD', args:['-include','archive.h'])` 探测，**只带 args、不带 dependency() 的 include 路径**；libarchive 在 OHOS 是 conan 包，`archive.h` 不在系统搜索路径。上游把该探测写在 `dependency('libarchive')` 之前，无法就地复用 | 把依赖 include 目录补进 `tc.extra_cxxflags`（与 .pc 提供的 `-I` 相同，不改变语义；appstream 对同类 configure 期探测的处置）。真机日志：`Fetching value of define "ARCHIVE_FILTER_ZSTD" : 14` + `Configuring config.hh` |
| 12 | `Dependency lookup for libpcre with method 'pkg-config' failed: Pkg-config for machine host machine not found` | OHOS 无系统 pkg-config；ohpcd 的 `pkgconf/3.0.5` 包内**只落了 `bin/pkgconf`**（配方里的 `pkg-config` 别名未真正生成，真机包目录实测只有 pkgconf） | 新增 `_pkg_config_binary()`：PATH → 常见目录 → `tool_requires` 包内 `bin/` 解析绝对路径，写入 `tc.pkgconfig`（machine file 的 `pkgconfig`/`pkg-config` 两项）。真机日志：`Found pkg-config: YES (.../pkgconf) 3.0.5`，随后 `libpcre found: YES 8.45` |
| 13 | `ERROR: C++ shared or static library 'stdc++fs' not found` | 上游 `cpp.find_library('stdc++fs')`，meson 的 `find_library` **默认 required: true**；`libstdc++fs` 是 GCC libstdc++ 的 `<filesystem>` 支撑库，libc++ 把 `std::filesystem` 内建其中、没有该库 | **补丁 0003**：改为 `required: false`，未找到时退化为空 `declare_dependency()`（两处 `dependencies:` 列表均可用） |
| 14 | `error: no matching function for call to 'construct_at'` + `error: object of type 'const pkgfile::Database::Entry' cannot be compared because its 'operator<=>' is implicitly deleted`（`src/db.cc`） | (a) clang 15 **未实现 C++20 P0960 括号聚合初始化**，`repos.emplace_back(a, b)` 对聚合类型 `Entry` 无法构造；(b) libc++ 15 的 `std::string` **没有 `operator<=>`**，`Entry` 的 `auto operator<=>(...) = default` 被隐式删除，`std::sort` 无法实例化 | **补丁 0004**：`db.cc` 改 `push_back(Entry{...})`（花括号聚合初始化，取值不变）；`db.hh` 把默认化 `<=>` 改为等价的显式字典序 `operator<`。上游用例与断言零改动 |
| 15 | `can't create temporary file /tmp/sheXXXX.tmp: Read-only file system`（test_package） | 三重叠加：(a) `mktemp -d`（无模板）在 GNU/Toybox 实现下**不使用** `$TMPDIR`、固定落 `/tmp`；(b) OHOS 的 `/bin/sh` 是 **mksh**，here-doc 需要一个临时文件；(c) mksh 在**启动时**读取并缓存 `TMPDIR`，脚本内部再 `export TMPDIR` 已经太晚 | test 脚本：改为在 `TMPDIR`/`HOME`/`PWD` 中挑可写基目录并用 `mkdir` 建工作区（不依赖 mktemp）；`pacman.conf` 改用 `printf` 生成（去掉 here-doc）。test_package conanfile：用 `EnvVars.apply()` 在**启动被测脚本之前**注入可写的 `TMPDIR`/`TMPPREFIX`。真机日志：`version: pkgfile v25` → … → `PASS` |
| 16 | 27 个上游 python 集成用例中 **11 个失败**（`AssertionError: 255 != 0`） | 测试夹具 `tests/pkgfile_test.py` 的 `Pkgfile()` 给被测进程构造**固定最小环境**（只有 `LC_TIME/LC_COLLATE/TZ/PATH`），不含 `TMPDIR`；OHOS 的 `/tmp` 只读 → 所有基于 `pkgfile -u` 的用例在 `update.cc:OpenTmpfile` 处失败：`error: failed to create temporary file for download: Read-only file system`，退出码 255。**隔离实证**：同一命令带可写 `TMPDIR` 时 `rc=0` 全通；`TMPDIR=/tmp` 时复现 `rc=255`。 | **补丁 0005**：把运行环境的 `TMPDIR`/`TMPPREFIX` 透传给子进程（`/tmp` 可写主机上是 no-op，断言与期望值零改动）；`build()` 由按名点跑 `unit_tests` 改为跑**完整** `meson test`。真机结果：5/5 测试目标 OK，38/38 用例通过 |
| 17 | PR CI 上 27 个集成用例中 **13 个失败**（`AssertionError: 1 != 0`），而本机 shadow run 38/38 全绿 | `db.cc` 与 `repo.cc` 各有一份 `FilenameHasRepoSuffix`，对**整条路径**数点号（`std::count(path.begin(), path.end(), '.') != 2` 即判无效）。`db.cc` 的调用点传入的是 `fs::directory_iterator` 给出的**绝对路径**，因此父目录里只要有一个点，所有 `<repo>.files.NNN` 缓存分片都被过滤 → 缓存被判为空 → `error: No repo files found` 退出 1。CI 的 conan 缓存是 `$HOME/.cache/conan2/...`（路径含 `.cache`、`.conan2` 两个点），而本机 shadow run 的隔离路径不含点，故此前未暴露 | **补丁 0006**：只在**最后一个路径分量**上判断点号/后缀/位数。真机按「父目录带点」复现失败（`No repo files found`），并按 `~/.cache/conan2/...` 形态验证修复后 `-l`/`-s` 均 `rc=0` 正常 |

### 4.3 环境/BUG 复核（非本库缺陷，记录备查）

- **本地 shadow runner 的 `settings.yml` 过窄**：`run-ohos-shadow-ci-local.sh` 写入的
  settings.yml 只含 `os: OHOS/Linux`，而 `curl/8.15.0.1`、`pkgconf`、`gtest`、`gmock`
  等配方都有 `if self.settings.os == "Windows":`（Conan 的 `settings` 比较会校验右值，
  见知识库 `DRAFT-tayga-0.9.2-settings-os-compare-str`），于是图计算阶段直接
  `Invalid setting 'Windows' is not a valid 'settings.os' value`。
  **真实 CI 不受影响**：`ci/conan/build_and_test.sh` 不写 settings.yml，用的是
  OHOS 适配版 conan 生成的默认枚举表（含 Windows）。
  本机复现真实 CI 行为的方式：用「conan 默认 settings.yml（19 个 os 枚举）+ 注入
  `OHOS: version ["6.0"]`」这一份 settings.yml 跑同一套
  `setup.sh` + `build_and_test.sh`；除这一处 settings.yml 内容外与共享 runner 完全一致。
  该问题不是 pkgfile 配方缺陷，也未因此修改任何配方。
- **真机 `github.com` 不可达**：直连超时（`ConnectTimeoutError`），`gh-proxy.com` 可达。
  CI 的镜像改写步骤已覆盖，配方保持官方 URL（R39）。
- **libarchive 是 shared 而非 static**：`archives/l/libarchive/3.8.7` 配方无 `options`，
  但 autotools 默认产出共享库；真机 `llvm-readobj` 确认产物 NEEDED `libarchive.so.13`。
  因此 #9 的 rpath 处置必须覆盖**全部** host 依赖（当时按「只有 curl 是 shared」写的
  注释已按实测修正）。

## 5. 补丁设计原则

六个补丁都只做「把上游写死的 Arch/systemd/GCC 专属能力改为可关闭或可选，或修正上游在
特定路径形态下才暴露的缺陷」，默认行为与上游 Linux 一致，**不含任何 `#ifdef __OHOS__`、
stub 或空壳实现**：

| 补丁 | 内容 | 默认值 |
|------|------|--------|
| 0001 | `libsystemd` / `pkgfiled` / systemd units 由 `daemon` 选项门控 | `true`（Linux 行为不变） |
| 0002 | `pod2man` 与两个 man 页 target 由 `man_pages` 选项门控 | `true` |
| 0003 | `cpp.find_library('stdc++fs')` 改 `required: false` + `declare_dependency()` 兜底 | 找得到时行为不变 |
| 0004 | `src/db.hh` 显式字典序 `operator<`；`src/db.cc` 花括号聚合初始化 | 语义/取值与原实现等价 |
| 0005 | `tests/pkgfile_test.py` 把 `TMPDIR`/`TMPPREFIX` 透传给被测子进程（见 #16） | `/tmp` 可写主机上为 no-op |
| 0006 | `FilenameHasRepoSuffix`（`db.cc` + `repo.cc`）只在最后一个路径分量上判断 `.files.NNN`（见 #17） | 路径父目录无点时行为不变 |

六个补丁均由纯净 v25 源码用 `git diff` 生成，并已验证在纯净源码上**顺序 `git apply` 全部
clean**（0003 的上下文包含 0001 改写后的行，顺序不可调换）。

## 6. 上游测试

`meson.build:180-229` 注册两套测试，**共 38 例，真机全部实跑通过**：

| 套件 | 用例数 | 真机结果 |
|------|-------|---------|
| `unit_tests`（gtest 协议，`filter_test.cc` 10 + `repo_test.cc` 1） | 11 | ✅ `1/5 pkgfile:unit_tests OK 0.07s`；`Ok` 计数来自 gtest |
| `pkgfile_database_integration_test`（tests/database.py） | 3 | ✅ `Ran 3 tests ... OK` |
| `pkgfile_list_integration_test`（tests/list.py） | 8 | ✅ `Ran 8 tests ... OK` |
| `pkgfile_search_integration_test`（tests/search.py） | 8 | ✅ `Ran 8 tests ... OK` |
| `pkgfile_update_integration_test`（tests/update.py） | 8 | ✅ `Ran 8 tests ... OK` |
| **合计** | **38** | **`Ok: 5 / Fail: 0`（meson 目标级）** |

首次真机运行时 27 个集成用例有 11 个失败。**当时的判断（"multiprocessing / 端口监听 /
x86_64 数据 / PATH 假设导致结构性不可运行"）经复测证明是错的**：真机上
`multiprocessing`（fork）可用、`/dev/shm` 可写、loopback 可绑定，`Architecture = x86_64`
只是 URL 里的路径片段、与宿主架构无关。真正且唯一的根因是夹具不透传 `TMPDIR`
（见 §4.2 问题 #16）。修正夹具后集成套件全绿，无需任何豁免。

`upstream_tests_passed` 现为 **38/38**，无跳过项。

## 7. 真机验证结果（shadow CI 单包）

运行：`ohos-test-runner.sh --user pkgfile --lib pkgfile --task shadow-ci-final --mode heavy --try-lock`
→ `run-ohos-shadow-ci-local.sh archives/p/pkgfile/25`（隔离 HOME/CONAN_HOME/TMPDIR）

```
G0_RESULT=pass            # 知识图谱完整性
KC_RESULT=pass            # 知识库质量门禁（含 index.tsv 一致性）
JC_RESULT=pass            # 杂项文件拦截
L0_RESULT=pass: all checks passed      # 含 L0i 依赖可用 / L0j 版本 / L0k commands.json / L0m 目录结构
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: pkgfile --version OK   # 裸执行，验证了 rpath 处置
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content

━━━ Build Summary ━━━
  Total:   1
  Success: 1
  Failed:  0
  Pass rate: 100.0% (1/1)
[step] All packages built and tested successfully ✅
```

上游单测 + 集成套件（配方 `build()` 内 `meson test`，全部目标）：

```
pkgfile/25: RUN: meson test -C "<build>" --print-errorlogs
1/5 pkgfile:unit_tests                                      OK              0.07s
2/5 integration - pkgfile:pkgfile_database_integration_test OK              1.11s
3/5 integration - pkgfile:pkgfile_list_integration_test     OK              2.14s
4/5 integration - pkgfile:pkgfile_search_integration_test   OK              2.26s
5/5 integration - pkgfile:pkgfile_update_integration_test   OK              2.61s

Ok:                5
Fail:              0
```

（集成套件逐个 `Ran 3 / 8 / 8 / 8 tests ... OK` → 27 例；加 11 个 gtest 用例共 **38/38**。）

test_package（离线端到端，16 项断言）：

```
version: pkgfile v25
[options] / Architecture = x86_64 / [demo] Server = file://...
:: Updating 1 repos...
  download complete: demo   [ 10.0 KiB ]
:: waiting for 1 repo to finish repacking...
search demo-tool -> demo/demo
search /usr/bin/helper-ctl -> demo/helper
list demo:
demo/demo	/usr/bin/demo-tool
demo/demo	/usr/share/demo/hello.txt
search -v -> demo/demo 1.2.3-1	/usr/bin/demo-tool
PASS: pkgfile 25 消费者测试全部通过
```

产物（真机实测）：

| 项 | 值 |
|----|----|
| 包引用 | `pkgfile/25#09b455870f8dbe37819bbf639e6e8376:cd547c6b82d4467c15dacde1fb660e88f36a9d92#17acdc1facf005bf65a6536d60d3f703` |
| `bin/pkgfile` | 338432 字节，sha256 `a32f83b24425b22624caeb025844e032720557add09b060db2caf60ae327ab14`，ELF 64-bit LSB arm64 dynamic (musl) |
| NEEDED | `libarchive.so.13`、`libcurl.so`、`libc++_shared.so`、`libc.so` |
| RUNPATH | 含 pcre/libarchive/xz/curl/zlib/gmock/gtest 各包 `lib` 目录 |
| 包树 | `bin/pkgfile`、`share/doc/pkgfile/command-not-found.{bash,zsh,fish}`、bash/zsh 补全、`share/licenses/pkgfile/LICENSE`；空 `var/` 已清理 |
| 裸执行 | `pkgfile --version` → `pkgfile v25`（rc=0）；`pkgfile --help` 正常 |

## 8. test_package 设计（R34：实质调用被测二进制）

pkgfile 不导出库，只能驱动可执行文件。`test_package/test_pkgfile.sh` 做的是
**完全离线的端到端闭环**，共 16 个断言点：

1. `pkgfile --version` → 必须精确等于 `pkgfile v25`（校验 `config.hh` 注入的 PACKAGE_NAME/VERSION）；
2. `pkgfile --help` → 必须列出 `--search` / `--update` / `--cachedir`（校验链接的是真实 CLI）；
3. 空缓存目录 → 必须非 0 退出且 stderr 含 `Database version file not found`（`db.cc` 版本校验路径）；
4. 端到端：`testdata/alpm/`（**纯文本**成员）在测试运行时由 `tar` 现场组装成最小
   alpm `.files` tar → 由 libcurl 经
   **`file://`** URL 读取 → `pkgfile -u` 转换为本地缓存（断言写出 `.db_version` 与
   `demo.files.000`）→ `pkgfile -s demo-tool` 断言 `demo/demo` →
   `pkgfile -s /usr/bin/helper-ctl` 断言 `demo/helper` → 未命中必须非 0 退出 →
   `pkgfile -l demo` 断言含 `/usr/bin/demo-tool`、`/usr/share/demo/hello.txt` 且不含
   `helper` 内容 → `pkgfile -l packagedoesntexist` 非 0 退出 →
   `pkgfile -s -v /usr/bin/demo-tool` 断言含 `demo/demo 1.2.3-1`。

选用 `file://` 而不是 HTTP 的依据：`update.cc:344` 的失败判据是
`msg->data.result != CURLE_OK || resp >= 400`，`file://` 传输 `resp = 0`，走正常成功分支，
因此无需起 HTTP 服务即可覆盖 libcurl → 转换 → 缓存 全链路。真机已实测成功。

`testdata/alpm/<pkg>/files` 的格式依据：上游 `tests/golden/alpm/x86_64/testing/testing.files`
实测为**未压缩 tar**，每个包一个成员 `<pkgname>-<pkgver>-<pkgrel>/files`，
内容为 `%FILES%\n` + 每行一个不带前导斜杠的路径；
`archive_converter.cc:WriteCpioEntry` 丢弃首行、给每行加 `/` 前缀后重打包。

## 9. 残留风险 / 未覆盖项

| # | 项 | 说明 |
|---|----|------|
| R1 | `pkgfiled` 守护进程未适配 | 有意关闭（依赖 systemd/libsystemd）。若业务需要，须先独立适配 `libsystemd` 并单独提交依赖库 PR |
| R2 | RUNPATH 为构建机绝对路径 | 由 #9 引入，用于满足 CI 裸执行 smoke test；运行时 `LD_LIBRARY_PATH`（Conan `conanrun`）优先级高于 RUNPATH，换机器/换缓存路径时由 runenv 兜底 |
| R3 | `pcre/8.45` 的 `libs` 声明为 `["pcre","pcrecpp","pcreposix"]` | 生成的 `libpcre.pc` 会带三个 `-l`；真机链接通过，未触发缺库 |
| R4 | 补丁 0005 修改了上游测试夹具 | 仅透传 `TMPDIR`/`TMPPREFIX`，不改断言与期望值；已按 积分赛 PR 模板「上游测试用例修改说明」逐条披露 |
| R5 | 未做 `conan upload` | 发布由平台 release 流水线在 PR 合入后执行；本轮做到 `built` 级别的真机验证 |

**测试口径**：38/38 上游用例均为真机实跑结果（`meson test` 全目标 OK）；
`MANIFEST.yml` 的 `upstream_tests_passed` 与之一致，无跳过项、无估填。
