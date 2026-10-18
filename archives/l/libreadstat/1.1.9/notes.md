# readstat 1.1.9 适配笔记

> **第二轮（2026-10-14，分支 `feat/readstat-1.1.9`）复核结论**：
> 配方主体（`conanfile.py` / `conandata.yml`）与制品仓已发布的 `libreadstat/1.1.9`
> 逐字节一致（CI L0j 判据：conanfile.py + conandata.yml 均未改动 → 版本号保持
> `1.1.9`，不递增；本轮变更全部落在 `test_package/` 与 `reports/`，而 CI 用
> `--build="${pkg_name}/*"` 强制重建并跑 test_package，因此新增消费者用例会在 CI 真实执行）。
> 本轮新增内容：
> 1. **鸿蒙消费者回归用例** `test_package/consumer_round_trip.c`（41 条断言）：经公共
>    writer API 用真实 POSIX `write(2)` 在 HMDFS 上落盘 `.sav` 与 zlib 压缩 `.zsav`，
>    再用 `readstat_parse_sav` 从磁盘读回逐值比对（double/int32/string 各 3 行，含
>    `1e300`、`-2147483647` 边界值），并校验变量名、行列计数、`readstat_set_row_limit(1)`
>    行窗口与缺失文件守卫。
> 2. **已打包 CLI 实跑** `test_package/cli_smoke.py`（10 条断言）：对上面产出的 `.sav`
>    运行包内 `bin/readstat`（元数据清单 + CSV 转换到 stdout）并断言输出内容。
> 3. 既有 `test.c` 更名 `consumer_error_paths.c`（内容不变，7 条断言），与新增套件拆成
>    两个可执行文件，失败可归因。
> 4. 证据与统计见 `reports/test-report.md`；真实构建日志 `reports/w3-conan-create.log`
>    （sha256 `b312396bd831b53c50227369f98cf25cd6429db28a1c2c1f8b81702214a67510`）。
>
> **包名变更（2026-10-16）**：conan 包名由 `readstat` 改为 **`libreadstat`**，归档目录随之
> 由 `archives/r/readstat/` 迁移到 `archives/l/libreadstat/`（`git mv` 保留历史），
> `conanfile.py` 的 `name = "libreadstat"`、`commands.json`、软件级/版本级 manifest 同步更新。
> **消费者可见标识一律保持上游原名**：库文件 `readstat`（`libreadstat.a`）、头文件 `readstat.h`、
> CMake `find_package(readstat)` / `readstat::readstat`、pkg-config `readstat`、
> 命令 `readstat` 与 `extract_metadata`（`cpp_info.libs = ["readstat"]` 等未改动）。
> 制品仓此前只有 `readstat/1.1.9`，`libreadstat/1.1.9` 为本包首次发布标识。
>
> 其余章节为第一轮记录，仍然有效。

## 编译环境
- 构建系统: autotools（上游仅有 configure.ac + Makefile.am；VS17/ 为 MSVC 工程，tarball 内无 CMake）
- 编译日期: 2026-09-26（第一轮）/ 2026-10-14（第二轮复核：强制重编 + 上游测试 + test_package）
- 编译器: clang 15.0.4 / clang++（OHOS SDK，`/data/service/hnp/bin/clang`）
- 平台: HarmonyOS PC aarch64（HongMeng Kernel 1.12.0）
- 状态: built

## 编译步骤

上游 tag 归档**不含预生成的 configure**，因此第一步是 bootstrap：

```sh
# 1) bootstrap（tool_requires: automake/1.18 + libtool/2.5.4 + gettext/0.22.5.1）
#    ACLOCAL_PATH 必须含 gettext 的 share/aclocal（AM_ICONV 宏在 iconv.m4）
autoreconf -fi

# 2) configure：config.guess 不认 HarmonyOS → 显式钉 build/host 三元组
./configure --prefix=/ --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu

# 3) 编译 + 上游测试 + 安装
make -j<n>
make check          # TESTS = test_readstat test_dta_days test_sav_date test_double_decimals
make install DESTDIR=<package_folder>
```

配方层面：`generate()` 走 `AutotoolsDeps` + `AutotoolsToolchain`（静态默认 `--enable-static
--disable-shared`，OHOS 加 `--build/--host`，并把 gettext 的 `share/aclocal` 前置进
`ACLOCAL_PATH`、把 `TMPDIR` 指进 build 目录）；`build()` 顺序为
「缺 configure 才 `autoreconf -fi` → HMDFS 临时目录归一 → configure → make → make check」。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` | 上游 config.guess 不认识 `uname` 输出 `HarmonyOS`；且**上游 tarball 根本不含 config.guess/config.sub**（由 automake `--add-missing` 在 autoreconf 时从 automake/1.18 包落入），没有可打补丁的文件——知识条目 E007/E129「应更新 config.guess 而非传 --build/--host」的前提在本包不成立 | 显式传 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`（兼容三元组，同时命中 configure.ac 的 `*linux*` 分支取得 `-lm`；与 epeg/aalib/aldo 同法）。未打 config.guess 补丁、未 vendor 生成文件 |
| 2 | `libtoolize: error: $pkgauxdir is not a directory: '//share/libtool/build-aux'` | libtoolize 的 `@datadir@` 被烤进构建机绝对路径 | 由容器层 `libtool/2.5.4` 配方的 `_lt_pkgdatadir` 环境变量绕开（tool_requires 自动带出）；配方无需处理 |
| 3 | `config.status[1025]: can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 上 autoconf 的 `(umask 077 && mkdir …)` / `mktemp -d "./confXXXXXX"` 落成 2700 目录，属主映射后不可写（E011 同族） | `build()` 在运行 configure 前把生成的 `configure` 中 `umask 077`→`umask 022`、`./confXXXXXX`→`${TMPDIR:-.}/confXXXXXX`、`tmp=./conf$$-$RANDOM`→`${TMPDIR:-.}/conf$$…`，并把 `TMPDIR` 指向 build 目录内；打出 `[hmdfs] applied=N residual_umask077=M` 可 grep 校验 |
| 4 | `error: a function declaration without a prototype is deprecated in all versions of C [-Werror,-Wstrict-prototypes]`（`src/bin/readstat.c:157`、`src/readstat_bits.c:11` 等） | 上游 Makefile.am 给目标钉了 `-Werror -pedantic-errors -std=c99`，而 clang 15 已默认开启 `-Wstrict-prototypes`（上游 CI 的 clang 版本更老） | 不改上游源码：`CFLAGS` 追加 `-Wno-strict-prototypes`（用户 CFLAGS 排在目标 `_CFLAGS` 之后，可关掉该告警）；`-Werror` 其余告警仍然生效 |
| 5 | 关闭 HAVE_ZLIB 会让 `make check` 真实失败 | 测试集把 ZSAV（`RT_FORMAT_SAV_COMP_ZLIB`）算进 `RT_FORMAT_SPSS`，无 zlib 时写读往返不可用 | 显式 `requires("zlib/1.3.1.1")`（制品仓已有 OHOS 二进制），既补齐测试面又避免静默链接 SDK 系统 libz（R26/G3） |
| 6 | 可选依赖 `libxlsxwriter` 在制品仓不存在 | 上游 `AC_CHECK_LIB(xlsxwriter)` 为可选写路径 | 缺省禁用（不影响任何上游测试用例，`RT_FORMAT_*` 不含 xlsx）；`libcsv` 同理保持关闭 |
| 7 | 采信轮第 1 轮 G2 失败：`configure.ac:43: warning: macro 'AM_ICONV' not found` → `error: possibly undefined macro: AM_ICONV` | 制品仓 `gettext/0.22.5` 的**包内容是库形态**（只有 `include/ lib/ share/locale`，既无 `bin/` 也无 `share/aclocal/`），拿不到 iconv.m4；`gettext/0.22.5.1` 才带 `bin/autopoint` + `share/aclocal`（含 iconv.m4/lib-link.m4 等全套）+ `share/gettext` 数据文件 | tool_requires 改为 `gettext/0.22.5.1`（avahi-compat-libdns_sd 同款）；`generate()` 里 `_iconv_macro_dirs()` 收集 conan 包内 `share/aclocal`、`share/gettext/m4` 与 HNP glob（`/data/service/hnp/*/*/share/{gettext/m4,aclocal}`），**任一目录有 iconv.m4 才继续、全无则直接抛带候选清单的 ConanInvalidConfiguration**，并设 `gettext_datadir` 覆盖 autopoint 烤死的 datadir |

## 源码修改

**无补丁文件**（`patches/` 为空，`conandata.yml` 的 `patches: []`）。上表 #3/#4 均为构建期
环境处理（对生成的 `configure` 做字符串归一、`CFLAGS` 追加），不改动上游任何源文件与测试。

## 依赖版本

- 运行/链接: `zlib/1.3.1.1`（显式）、`iconv`（HarmonyOS libc 内置，configure 判定
  `checking for working iconv... yes`）、`m`（configure 按 `*linux*` 给出 `-lm`）
- 构建期 tool_requires: `automake/1.18`、`libtool/2.5.4`、`gettext/0.22.5.1`；`autoconf`
  用 SDK/HNP 自带 2.73（不声明 conan autoconf，避免 §一.23 的 perl ABI 崩溃）
- 未启用的可选依赖: `libxlsxwriter`（制品仓无）、`libcsv`、`ragel`（9 个 `.rl` 的生成产物
  `.c` 已签入源码，`RAGEL=true` 回退不影响构建）

## 验证结果

```bash
# 第一轮：手工编译（Mode B Step 2，$BUILD_SRC_DIR）
AUTORECONF_RC=0 CONFIGURE_RC=0 MAKE_RC=0 INSTALL_RC=0 CHECK_RC=0
# make check 汇总（_build/test-suite.log）
#   # TOTAL: 4   # PASS: 4   # SKIP: 0   # FAIL: 0   # ERROR: 0
#   PASS: test_readstat / test_dta_days / test_sav_date / test_double_decimals
# 安装树清点：7 个文件（bin/readstat、bin/extract_metadata、include/readstat.h、
#             lib/libreadstat.*、share/man/man1/*.1）
# 逐项断言清点见 test_package/MANIFEST.yml（assertion_count=336378
#   = test_readstat 1352（插桩实测 loop_hits）+ test_dta_days 164364
#     + test_sav_date 170651 + test_double_decimals 11）

# 第二轮：强制重编全链路复核（配方未改动，仅新增消费者测试）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    -r=ohpcd --build=readstat/*
# → Building from source（真实重编）
# → make check: # TOTAL: 4  # PASS: 4  # SKIP: 0  # FAIL: 0  # ERROR: 0  （PASS: 4 项同名）
# → test_package: consumer_error_paths 7/7、consumer_round_trip 41/41、cli_smoke 10/10，FAIL=0
# 日志：reports/w3-conan-create.log（sha256 b312396b…a67510）
# 统计与逐项用例：reports/test-report.md
```

## 注意事项

- 上游 `configure.ac` 的 `READSTAT_MICRO_VERSION` 仍是 8（上游 TODO 未同步 1.1.9），因此
  安装产物 soname 为 `libreadstat.so.1.1.8`（`readstat --version` 亦打印 1.1.8）；本配方默认
  静态交付，不受影响，属上游已知问题。
- `extract_metadata` 只认 `<input> <output>` 参数，无参时打印 usage；上游 `src/bin/main.h`
  丢弃 `portable_main()` 的返回值，因此 usage 分支退出码为 0。实测口径有两处，勿混淆：
  CI 的 L2 冒烟（`build_and_test.sh`）实跑 `extract_metadata --version` 并判 OK；
  `conan-verify` 的 L2 因无 cache 路径而记为"跳过"，其报告中的 PASS 不等于跑过冒烟。
- **只读 `/tmp` 与上游 `dump_buffer()`**：本设备 `/tmp` 为只读 `erofs`（实测 `mount` → `erofs (ro)`，
  `touch /tmp/x` → `Read-only file system`）。上游 `Makefile.am` 为 `test_readstat` 钉了
  `-DDEBUG=1`，因此 `src/test/test_readstat.c:37` 的 `/tmp/test_readstat.<ext>` 诊断转储在
  **失败路径**上落地不成功（本设备 libc 为 musl，`fwrite(…, NULL)` 不崩溃，静默丢弃）。
  该转储只用于失败诊断、不参与用例判定，成功路径不触发（实测直跑输出 0 字节、exit 0），
  按 R8“补丁最小化、不夹带平台宏”不改上游源码，如实记录于此。
---

**编译结束**: 2026-10-14 20:09
**最终状态**: built
