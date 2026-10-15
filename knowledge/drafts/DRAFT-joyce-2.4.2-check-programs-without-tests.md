# DRAFT-joyce-2.4.2-check-programs-without-tests
> 上游 Makefile.am 仅声明 check_PROGRAMS 而无 TESTS 时 make check 只编译不运行，需显式执行测试二进制并产出确定性上游回归计数

## 问题特征（真实日志片段/标记）
- 上游测试统计恒为零：`discovered:0/executed:0`，`HMBS_UPSTREAM_TEST_RESULT` 中 `"status":"no_tests"`。
- automake 只构建不运行：`LibDsk/tools/Makefile.am` 声明 `check_PROGRAMS = check1 check2 check3`，却无 `TESTS = $(check_PROGRAMS)`。
- 同任务真机还伴随 autotools 场景的通用构建报错（证据 excerpts）：
  - `config/missing: Unknown '--is-lightweight' option`、`.conan-configure: WARNING: 'missing' script is too old or missing`
  - `.conan-configure: error: libxml needed` / `checking for libxml - version >= 2.0.0... no` / `*** The test program failed to compile or link`
  - `checking for png_init_io in -lpng... no` → `libpng not found - aborting`
  - `.conan-configure: error: cannot run C++ compiled programs.`
  - `config.status: error: could not setup config files machinery` / `can't create ./confhCdJhA/subs1.awk: Permission denied`
  - `bin/JoycePcwTerm.cxx:142:2: error: ISO C++17 does not allow 'register' storage class specifier [-Wregister]`
  - `TypeError: copy() got an unexpected keyword argument 'delete'`
- CI 反空壳门禁：`L0c` `no_test_sources`（test_package 无测试源文件）与 `L0d` `stub_test_method`（test() 无 self.run）。

## 根因
automake 的 `make check` 只运行登记在 `TESTS` 里的目标；`check_PROGRAMS` 仅保证这些程序被构建。joyce 的 `LibDsk/tools/Makefile.am` 声明了 `check_PROGRAMS = check1 check2 check3` 却漏写 `TESTS = $(check_PROGRAMS)`，于是 `make check` 只编译不执行，配方抓不到 `# TOTAL`/`PASS:` 行，上游计数恒为 `discovered:0/executed:0`，被证据门禁判为零证据。

同任务其余失败点属 autotools 通用模式：`AutotoolsToolchain` 只给工具链文件、不含依赖旗标，`AC_CHECK_LIB` 链接探针需要 `AutotoolsDeps` 聚合的 `-I/-L/-l`；conan 依赖不安装 `*-config` 程序（libxml2/sdl12-compat），需自建 `xml2-config`/`sdl-config` shim；musl 加载器的 el1 毒路径使 configure 的 C++ conftest 无法运行；`unsafe_local_mktemp` 使 config.status 临时目录不可写；C++17 已移除 `register`。

## 修复方案（rec）
1. 显式执行上游测试：在 `archives/j/joyce/2.4.2/conanfile.py` 重写 `_run_upstream_check()`，先构建整棵树，再定位 `LibDsk/tools/check1 check2 check3` 等 `check_PROGRAMS` 对应二进制逐个执行，按退出码汇总 passed/failed 与 discovered/executed，输出确定性上游回归计数（与 test_package 结果分列）。
2. 补齐依赖旗标：`generate()` 增加 `AutotoolsDeps(self).generate()`，把整张依赖图（含传递依赖 zlib/lzma/iconv 等）的 `-I/-L/-l` 注入 conanbuild 的 `CPPFLAGS/LDFLAGS/LIBS`，使 `AC_CHECK_LIB(png, png_init_io)` 等链接探针通过。
3. 自建 `*-config` shim：`_xml2_config_shim()` 的 `--cflags` 输出带 `-I` 前缀的 `<prefix>/include` 与 `<prefix>/include/libxml2`，`--libs` 收集传递 `-L/-l`，`--version` 读 `LIBXML_DOTTED_VERSION` 完成版本对拍；`_sdl_config_shim()` 的 `--cflags` 同时输出父目录与 `SDL` 子目录以解析 `<SDL/SDL.h>`。
4. 清洗 musl loader 毒路径：`_sanitize_ld_library_path()` 剔除 `/data/storage/el1/bundle` 段，前置含 `libc++_shared.so` 的 SDK llvm/lib 目录并追加依赖 lib 目录，使 configure 的 C++ conftest 可运行。
5. 修 config.status 临时目录：对运行副本做 `umask 077 → 022` 文本补丁（替代失效的 mktemp shim），使 `confXXXXXX` 落到 0755。
6. C++17 兼容：`generate()` 追加 `-Wno-register`/`-Wno-error=register`（及 `-Wno-error=dynamic-exception-spec`）。
7. 修 `package()` 的 `copy(..., delete=True)` TypeError，改用 `Path(package_folder/lib).rglob()` + `unlink()`。
8. 补 test_package：新增 `test_package/test.sh`（真实内容级断言，输出唯一 `RESULT: N passed, M failed`），`test()` 用 Conan `self.run` 执行并只从 RESULT 行解析计数，`MANIFEST.yml` 的 `test_package_tests` 指向该脚本，同时通过 L0c/L0d。

## 禁止策略
- 禁止在上游存在 `check_PROGRAMS` 却未真实执行的情况下，以 `discovered:0` 标记 `status:"passed"` 的零证据放行（forbid_1）。
- 不得把 demo 改造或新增的 test_package 用例计入上游测试总数。

## 与相近条目的边界（查重）
- DRAFT-ccrtp-1.0.0-demo-as-upstream-regression：上游无 formal make check 时把 demo 提升为回归测试；本条是上游已有 check_PROGRAMS 但缺 TESTS，需显式执行既有测试二进制，边界不同。
- DRAFT-libb64-2.0.0-upstream-make-test-missing-library-target：测试目标缺库目标；本条是测试程序未被 TESTS 登记。
- 机械查重命中的通用平台样板（musl el1、unsafe_local_mktemp、*-config shim 等）与本条新增的上游测试 marker/测试提升零重叠。

## 适用判断
上游为 autotools 且 `Makefile.am` 用 `check_PROGRAMS` 声明测试程序但未写入 `TESTS`，导致 `make check` 只构建不运行、上游计数为 0 的 C/C++ 库；若同时伴随 `AC_CHECK_LIB` 探针失败或依赖缺 `*-config`，按上述步骤 2/3 一并处理。
