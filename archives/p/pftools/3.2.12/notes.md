# pftools 3.2.12 适配笔记

## 编译环境
- 构建系统: **cmake**（CMakeLists.txt:31 `CMAKE_MINIMUM_REQUIRED(VERSION 3.7)`）
- 编译日期: 2026-10-13
- 目标平台: OHOS / aarch64（`clang -dumpmachine` → `aarch64-unknown-linux-ohos`）
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`）+ **flang-ohos/20.1.0**（Fortran 77 组件）
- 依赖: `pcre2/10.47`、`libfile-slurp-perl/9999.32`（`conan download -r=ohpcd --only-recipe` 均 exit 0）
- 状态: **built**（`conan create` exit 0；上游 CTest 6/6 通过；W3 本地 CI 模拟通过）

## 构建步骤（真实命令）

```bash
# 1. 依赖复核（全新空 CONAN_HOME）
conan download pcre2/10.47 -r=ohpcd --only-recipe            # exit 0
conan download libfile-slurp-perl/9999.32 -r=ohpcd --only-recipe  # exit 0

# 2. init-build（github.com:443 本机不可达，改用 codeload）
python3 scripts/ohc-run.py init-build pftools 3.2.12 \
  --url=https://codeload.github.com/sib-swiss/pftools3/tar.gz/refs/tags/v3.2.12   # exit 0

# 3. 语言预检（R47）
python3 scripts/ohc-run.py lang-preflight pftools 3.2.12 --src …   # exit 0, detected=c

# 4. 真实构建（模式 B 探索：cmake + flang，OHOS aarch64）
cmake <src> -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
  -DCMAKE_Fortran_COMPILER=<flang-ohos>/bin/flang \
  -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY \
  -DUSE_PCRE2=ON -DUSE_AFFINITY=OFF -DUSE_RPATH=OFF \
  -DPCRE2_INCLUDE_DIR=<pcre2>/include -DPCRE2_LIBRARY=<pcre2>/lib/libpcre2-8.a \
  -DCMAKE_C_FLAGS=-ffp-contract=off
make -j4          # exit 0，21 个可执行文件（aarch64 ELF）
make install      # exit 0，bin/ 26 项

# 5. 上游测试（CTest）
ctest --output-on-failure    # 6/6 passed

# 6. 配方与门禁
conan create archives/p/pftools/3.2.12 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64   # exit 0
python3 scripts/ohc-run.py conan-verify pftools 3.2.12                        # exit 0 (G0-G4 + L2/L4/L5)
python3 scripts/ohc-run.py finish pftools 3.2.12 built                        # W3 通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 下载失败 `Remote end closed connection without response` | 本机 **github.com:443 不可达**（curl exit 28），`codeload.github.com` 可达 | conandata.yml 改用 codeload 形式（仓库已有 503 例先例） |
| 2 | `emmintrin.h:14: error: "This header is only meant to be used on x86 and x64 architecture"` | **pftoolsV3 的 C 对齐内核是 x86 SSE2/SSE4.1 专用**：`pfProfile.h:17` 无条件 `#include <emmintrin.h>`，9 个内核文件无标量/NEON 回退 | 新增 `src/C/simd/` 垫片 → **sse2neon**（MIT，SSE→NEON 转译层），顶层 CMakeLists 仅非 x86 生效；配方 `source()` 生成 4 个重定向头并拉取 sse2neon.h |
| 3 | 内核中的 x86 内联汇编（`xorps`/`maxps`/`pmaxsd`/`phaddd`/`movsd`/`movss`/`cvtsi2ss`/`pshufd`）在 aarch64 无法汇编 | 手写 x86 asm，与架构绑定 | 逐处改写为**等价 intrinsic**（水平求和用 `_mm_movehl_ps`+`_mm_shuffle_ps`+`_mm_add_ss` 复现） |
| 4 | `utils/system.c` 的 `cpuid`/`xgetbv`/`bsrq` 无法编译 | CPU 特性/拓扑探测为 x86 专用 | `createMask` 的 `bsrq` → `__builtin_clzll`；cpuid 块与 `GetIntel/AMDTopology` 加 `#if defined(__x86_64__) || defined(__i386__)` 门控，非 x86 分支直接声明 `MM_SSE2\|MM_SSE41` |
| 5 | `system.c:14: #error "GNU EXTENSION not activated."` | OHOS 使用 **musl**，`features.h` 不定义 `__USE_GNU`，而上游在 `USE_AFFINITY` 下强制要求 | `-DUSE_AFFINITY=OFF`（上游 `INSTALL` 记载的官方构型 "Build without affinity (old machines)"） |
| 6 | cmake configure: `No CMAKE_Fortran_COMPILER could be found` | 本机/ohpcd 均无 gfortran（`gcc/9.5.0` 配方是 `--enable-languages=c`） | `tool_requires flang-ohos/20.1.0`（ohpcd 有 OHOS/armv8 binary） |
| 7 | flang try-compile 链接失败（`cannot open Scrt1.o` / `-lc` / `libclang_rt.builtins.a`） | flang-ohos 只带编译器，不带 crt/运行时 | `generate()` 把 OHOS SDK 的 `crtbeginS.o`/`crtendS.o`/`libclang_rt.builtins.a`/`libunwind.a` 注入 flang 的 resource-dir；CMake 侧补 `--sysroot` + `-L` + `libFortranRuntime.a`（同 `archives/a/alfa/2.2`） |
| 8 | `error: Only -std=f2018 is allowed currently.` | `src/Fortran/CMakeLists.txt` 传了 gfortran 专用的 `-std=legacy` | 按 `CMAKE_Fortran_COMPILER_ID` 选择：LLVMFlang 只传 `-fno-automatic` |
| 9 | `fatal Fortran runtime error: fdate is not supported.`（pfmake 崩溃，Signal 6） | LLVM Flang 未实现 `FDATE` 扩展（`pfmake.f:435`） | 改用标准 `DATE_AND_TIME` 构造时间戳 |
| 10 | `psa2msa: Error: Unable to create temporary file.` | Fortran `Open(Status='SCRATCH')` 依赖 `/tmp`，而 **HarmonyOS 的 /tmp 是只读文件系统**（musl `tmpfile()` 亦固定用 /tmp，实测 EACCES） | `psa2msa.f`/`regpr.f`/`pfw.f` 改为 `$TMPDIR` 下的具名工作文件 |
| 11 | 测试脚本 `mkdir: '/tmp/test_V3': Read-only file system` | 上游测试脚本硬编码 `/tmp` | 3 个 `.sh.cmake` 改 `${TMPDIR:-/tmp}`；`tests/examples/CMakeLists.txt` 的 Perl 用例改用构建目录 |
| 12 | `check_output_of_test_V3.sh` 失败：分数末位差 ±1（43/1959 行，如 53.837402 vs 53.837406） | **AArch64 默认启用 FMA 收缩**（clang `-ffp-contract=on`），浮点表达式合并成单条融合运算，与 x86（无 FMA）落点不同 → 1 ULP | C/Fortran 编译加 **`-ffp-contract=off`**，输出与上游参考**逐字节一致**（`diff` 为空） |
| 12b | `ctest` **随机失败**：`test_V3.sh[236]: can't create temporary file /tmp/shXXXXXX.tmp: Read-only file system` | 脚本里的 here-document（`cat > f << EOI`）迫使 shell 自己创建临时文件，而该临时文件固定落在 `/tmp`（与脚本的 `$TMPDIR` 无关）；HarmonyOS `/tmp` 只读 ⇒ 同一条用例时通时不通 | 2 处 here-doc 改为 `printf '%s\n' ... > f`（内容逐字节等价），彻底去掉 shell 对 `/tmp` 的依赖；修复后连跑 5 次 `test_V3.sh` + 2 次 `ctest` 全部通过 |
| 13 | `conan create` 报 `Already installed ... file to download already exists` | conan 缓存里存在残留的 `conan_export.tgz`/`conan_package.tgz` | 删除对应 `~/.conan2/p/<hash>` 目录后重试 |
| 14 | `BadZipFile: File is not a zip file` | `get()` 按 URL 末段命名（`v3.2.12` 无扩展名）；单头文件 `sse2neon.h` 也被当压缩包 | 主源显式 `filename="pftools-3.2.12.tar.gz"`；单头文件改用 `download()` |
| 15 | `finish` 的 W3 在 `JC1/JC5` 失败（8 个 `archives/**.staging-verified`/`.build-closed`） | 分支尚无 commit → junk_check 回退 **full 模式（整仓扫描）**，命中 origin/main 上其他库的 8 个历史状态文件（非本包文件） | 以 PR 文件清单（24 个文件）作为 `JUNK_PR_DIFF` 运行，JC_RESULT=pass（与 CI 实际作用域一致） |

## 源码修改

见 `patches/`（16 个补丁，逐一对应上表 #2–#5、#8–#11；由 `refresh-patch --auto` 生成的逐文件补丁）。
SIMD 垫片头（4 个）由 `conanfile.py` 的 `source()` 生成，不进入补丁（避免新增文件补丁被 `refresh-patch` 覆盖）。

## 依赖版本
- `pcre2/10.47`（默认构型强制，链接 `pfsearchV3`/`pfscanV3`/`pfdump`）
- `libfile-slurp-perl/9999.32`（Perl 脚本运行期，`use File::Slurp;` 2 处）
- `flang-ohos/20.1.0`（构建期 tool_requires，Fortran 77 组件）
- 工具链：clang 15.0.4、cmake 4.1.2、perl 5.42.x

## 验证结果

```bash
# 上游测试套件（CTest，6 个用例）
$ ctest --output-on-failure
1/6 execute_test_V2.sh ..........................   Passed    1.60 sec
2/6 execute_test_V3.sh ..........................   Passed   29.88 sec
3/6 check_output_of_test_V3.sh ..................   Passed   30.01 sec
4/6 execute_test_scan_search.pl .................   Passed   37.19 sec
5/6 execute_test_pfsearchV3_iupac.pl ............   Passed   13.00 sec
6/6 execute_test_pfsearchV3_pattern-regexp.sh ...   Passed    1.12 sec
100% tests passed, 0 tests failed out of 6

# 与上游参考输出逐字节比对（test_V3_output.sh 的核心断言）
$ diff testing/examples/test_V3.out <(sh -ve testing/examples/test_V3.sh 2>/dev/null)
$ echo $?     # 0（1959 行完全一致）

# 消费者视角（conan create 的 test_package）
$ conan create archives/p/pftools/3.2.12 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
# pfsearchV3 hits = 12 / pfscanV3 PS50002 命中 / gtop 可执行 / ps_scan.pl syntax OK
# psa2msa MSA records = 26, scratch file = $TMPDIR/pftools_psa2msa.scr   # 鸿蒙特有用例
# all pftools consumer checks passed
```

## 鸿蒙特有用例（≥1）

`test_package/test_pftools.sh` 第 5 项专测本平台的适配改动：

```sh
"$BIN/pfsearchV3" -n -f -o 4 "$DATA/sh3.prf" "$DATA/sh3.seq" | "$BIN/psa2msa" -du > "$WORK/psa2msa.msa"
# 断言 (1) 产出 MSA；(2) 工作文件落在 $TMPDIR/pftools_psa2msa.scr
```
上游 `psa2msa` 用 `Open(Status='SCRATCH')`（落 `/tmp`），在 HarmonyOS 上必然报
`Error: Unable to create temporary file.`；补丁 0011 改为 `$TMPDIR` 具名工作文件后通过。

## 交付物
- `bin/` 26 项：pftoolsV3 8 个（pfsearchV3 / pfscanV3 / pfcalibrateV3 / pfindex / pfdump / pfpam / pfemit / pfsplit）+ Fortran 2.3 12 个（gtop / htop / ptoh / ptof / pfw / 2ft / 6ft / psa2msa / pfscan / pfsearch / pfmake / pfscale）+ Perl 7 个
- `share/data`（矩阵/校准/反向数据）、`share/examples`（上游示例）、`share/man`、`share/doc`
- 运行时仅依赖 libc（Fortran 运行时静态链接）

## 对话记录

### 对话 #1（2026-10-13）依赖分析 → 架构判定

- 用户要求先只做依赖分析（不编译、不修改）。结论：强制第三方依赖 2 个
  （pcre2/10.47、libfile-slurp-perl/9999.32），**均实测可消费**（conan download exit 0），
  缺口 GAP_N=0；传递依赖 0。
- 首轮适配尝试发现硬阻塞：pftoolsV3 的 C 内核是 x86 SSE2/SSE4.1 专用，
  aarch64 下 `emmintrin.h`/`smmintrin.h` 直接 `#error`。曾按 W0b 建议上报
  `env_unsupported` 并请用户决策。

### 对话 #2（2026-10-13）用户选择方案 A：按 sse2neon 移植

- 用户选择「A. 按 sse2neon 方案继续移植」，并要求：有新知识沉淀进草稿；
  若可进入「路径 C」（知识库扩展）需告知。
- 执行结果：引入 sse2neon 转译层 + 改写 x86 内联汇编 + `system.c` 非 x86 分支 +
  `USE_AFFINITY=OFF` + flang 工具链注入 + `-ffp-contract=off`；
  `conan create` exit 0、上游 CTest **6/6 通过**、`test_V3_output` 与上游参考
  **逐字节一致**、`conan-verify` 全门禁通过、W3 本地 CI 模拟通过。
- 知识沉淀：新增 4 个知识库草稿（sse2neon 转译模式 / FMA 收缩 1 ULP /
  OHOS /tmp 只读与 Fortran SCRATCH / flang-ohos 工具链缺口），见
  `knowledge/drafts/DRAFT-900x-*.kv` + 对应 `.md`。

## 注意事项
- `pfsplit` 是上游唯一「构建但不安装」的程序（`EXECUTABLES` 未包含它），行为与上游一致。
- 本机 `github.com:443` 不可达，源 URL 使用 `codeload.github.com` / `raw.githubusercontent.com`（均为 GitHub 官方端点）。
- 未执行任何 commit / push / PR / 制品上传；`finish` 的 W3 本地 CI 模拟（含真实 `conan create` + L0 门禁）已通过。
---

**编译结束**: 2026-10-13 20:02
**最终状态**: built
