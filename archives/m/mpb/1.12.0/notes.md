# mpb 1.12.0 适配笔记

## 编译环境
- 构建系统: autotools（官方 release tarball 自带 `configure`；设备无 automake，不能 autoreconf）
- 平台: OHOS aarch64 原生 build=host（不使用 --build/--host/--target）
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 日期: 2026-10-15

## 依赖
- fftw/3.3.10.3（FFTW3 双精度，`-lfftw3`，必需）
- lapack/3.12.1（静态，内含 reference BLAS；AX_BLAS/AX_LAPACK 必需，否则 configure 报错）
- libctl/4.5.1（guile 驱动；提供 share/libctl/base/{ctl.scm,main.c}、utils/{geom.c,geom.scm}、bin/gen-ctl-io）
  - 传递 guile/2.2.7.1 + gc/gmp/libffi/libunistring

## configure 选项
```
--disable-dependency-tracking   # HMDFS: make depfiles 管道执行 bash 被拒
--without-hdf5                  # 可选输出；见"遇到的问题"
--without-openmp
--without-mpi
--with-libctl=<libctl pkg>/share/libctl
```

## 上游测试申报表（R51）
清点依据：`tests/Makefile.am`（noinst_PROGRAMS + check-local）、`mpb/Makefile.am`（check-local）。

| # | 测试 | 来源 | 是否由 `make check` 运行 |
|---|------|------|--------------------------|
| 1 | blastest | tests/blastest.c | 是（diff vs blastest.real.out） |
| 2 | maxwell_test（两次配置） | tests/maxwell_test.c | 是 |
| 3 | malloctest | tests/malloctest.c | 否（仅构建，noinst_PROGRAMS） |
| 4 | eigs_test | tests/eigs_test.c | 否（仅构建） |
| 5 | normal_vectors | tests/normal_vectors.c | 否（仅构建，需 libctlgeom） |
| 6 | examples/check.ctl | examples/check.ctl | 是（`mpb examples/check.ctl` 两次） |

实测结果见 `reports/`（构建后回填逐项 PASS/FAIL）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` | `uname -s` 返回 `HarmonyOS`，config.guess 不识别，回落到编译探测且 HMDFS 上写 dummy.c 被拒 | 补丁 0001/0002：config.guess 增加 HarmonyOS 分支（→ aarch64-unknown-linux-ohos），config.sub 接受 linux-ohos 三元组（E007/E072） |
| 2 | `configure: error: BLAS was not found!` | 设备无 Fortran 编译器，`AC_F77_FUNC` 名字修饰探测得 "unknown"，AX_BLAS/AX_LAPACK 去查符号 "unknown" | build() 导出 `ac_cv_f77_mangling="lower case, underscore"`（参考 BLAS/LAPACK 由 flang 构建，符号为小写加单下划线；E064 允许的 cache 覆盖） |
| 3 | `libtool: error: cannot find the library '//lib/libltdl.la'` | ohpcd 依赖包以 `prefix=/` 构建，`.la` 携带 `libdir='//lib'` 与 `dependency_libs='… //lib/libltdl.la …'`（含迁移前的旧缓存 -L 路径） | E236/E522/E544：build() 建立私有目录 `ohpcd-libs/`，复制依赖共享库并写净化 `.la`（libdir 指向私有目录、dependency_libs 置空），置于链接行 `-L` 首位；不改 Conan 缓存 |
| 4 | 运行期 scheme 路径错误 | mpb 把 `$(pkgdatadir)/mpb.scm` 与 libctl 路径编译进二进制（CTL_DEFS/SPEC_SCM） | `--prefix=<package_folder>` + `make install` 不带 DESTDIR，使编译期路径与最终安装位置一致 |
| 5 | guile/libctl 解释器不在 PATH | mpb 内嵌 guile，configure 需要 `guile`/`guile-config`/`gen-ctl-io` | build() 注入 guile/bin 与 libctl/bin 到 PATH，并设 GUILE_CONFIG=sh <guile-config> |
| 6 | HMDFS 上 autoconf 临时目录失败 | `umask 077 && mktemp -d ./confXXXXXX` 在共享挂载上被拒 | build() 内改写生成的 `configure`（umask 077→022），同 fftw/libctl 先例 |
| 7 | make 依赖跟踪管道失败 | HMDFS 拒绝 `sed | make -f -` 中执行 bash | `--disable-dependency-tracking` |
| 8 | HDF5 C++ 库污染 C 链接 | AutotoolsDeps 把 hdf5 的 C++ 库加入 LIBS，autoconf conftest 加载失败 | 本次 `--without-hdf5`（HDF5 为上游可选输出；核心求解不受影响） |

## 源码修改（补丁）
- `patches/0001-config.guess.patch`：`*:HarmonyOS:*:*` 分支 → `aarch64-unknown-linux-ohos`（E007）
- `patches/0002-config.sub.patch`：接受 `linux-ohos` 内核/OS 组合与 `ohos` OS（E007/E072）
- 其余 HMDFS/guile/la 相关处理在 `conanfile.py` 的 `build()` 内以文本改写实现（与 fftw/libctl 配方一致，可复现）

## 验证结果

### conan-verify（G0-G4 + L2/L4/L5）
`python3 $F/scripts/ohc-run.py conan-verify mpb 1.12.0 --profile <根仓库 ohos-aarch64> --project-dir <worktree>`
- 结果：**Verdict PASS**（G0 PASS / G1 PASS / **G2 conan create PASS** / G3 PASS / G4 PASS；L2/L4/L5 因工具未定位到包 ID 而跳过）
- 证据：`reports/conan-verify-report.md`、`reports/conan-create.log`

### 上游测试（`make check`，R51）
`make check` 实际运行（同一 conan create 内）：

| 测试 | 结果 |
|------|------|
| `tests/blastest`（对比 tests/blastest.complex.out 的 diff） | PASS（"PASSED tests."） |
| `tests/maxwell_test`（-e -k 0.4 -n 1 及基础两配置） | PASS |
| `mpb/examples/check.ctl`（普通） | PASS（"PASSED all tests."） |
| `mpb/examples/check.ctl`（force-mu?=true） | PASS（"PASSED all tests."） |
| 断言级：`check-freqs: PASSED` ×17、`check-almost-equal: PASSED` ×18 | 35 项断言全通过 |

`tests/malloctest`、`tests/eigs_test`、`tests/normal_vectors` 为 noinst_PROGRAMS：随 `make check` 编译成功但不执行（上游 check-local 未运行它们）。

### 消费者测试（test_package）
`test.sh` 运行已安装的 `mpb` 二进制：
- `mpb --version` → `mpb 1.12.0 ... Using libctl 4.5.1 and Guile 2.2.7.`
- 2D 方形介质柱晶格 TE 模式，k=(0,0) 4 条能带计算 → `0 0.561945 0.780843 0.780846`，与上游 `examples/check.ctl` 参考值一致（容差 1e-4）
- 输出 `MPB_CONSUMER_PASS`，`conan create` 的 test_package 阶段整体 PASS

### CI 同构门禁（`ci/conan/build_and_test.sh`）
`porting run ... -- env CI_PACKAGES="archives/m/mpb/1.12.0" CI_REPO_ROOT=<worktree> CONAN_PROFILE=<根仓库 profile> JUNK_PR_DIFF=<本包 pr.diff> zsh <framework>/ci/conan/build_and_test.sh`
- 结果：**exit 0**，`Pass rate: 100.0% (1/1)`，`All packages built and tested successfully`
- `L0_RESULT=pass`（R36/R37/L0k/L0m 依赖可用、版本未占用、commands.json 合法）
- `L1_RESULT=pass`（L1a/L1b/L1c：test_package 执行 + 上游 `make check` 在构建阶段执行）
- `L2_RESULT=skip`（`mpb --version` 等 smoke 未注入依赖 `LD_LIBRARY_PATH`/guile 环境，非阻断；真实消费者测试已覆盖）
- `L4_RESULT=warn`（config.guess 补丁命中"危险函数"正则，误报，非阻断）
- `L5_RESULT=pass`（bin/ 有内容）
- 说明：JC 门禁需以 `JUNK_PR_DIFF` 限定到本包变更；否则会全仓扫描并命中**其他包既有**的 8 个被跟踪运行时状态文件（cloog/kics/libbfio/libdazzle/oscpack/reflex/thc），与本 PR 无关。

### 已知非致命告警
- `GC Warning: Failed to find PT_GNU_RELRO segment inside PT_LOAD region`（boehm-gc 在 OHOS 上的运行时告警，不影响功能；libctl 4.5.1 亦记录同类告警）
- `matrixio: cannot output "rods-epsilon" (compiled without HDF)`——因本次 `--without-hdf5`，属预期。


## 注意事项
- 运行期 scheme 定位依赖编译期绝对路径，消费者的 Conan 缓存包目录需保持稳定（记录为限制）。
