# libidn 1.42 - OHOS Adaptation Notes

## Build Summary
- Software: libidn 1.42
- Build System: autotools
- Status: built
- Date: 2026-10-03

## Source Modifications

### 1. E011 - configure umask 077
- libidn-1.42/configure contains `umask 077` twice (mktemp/mkdir for config.status temp dirs)
- HMDFS: 0700-perm temp dirs unwritable by current process -> `subs1.awk Permission denied`
- Fix applied IN RECIPE (build()): rewrite `umask 077` -> `umask 022` before autotools.configure()
- Delivered in recipe code, not as a patch file, so it cannot be lost between exploration and CI

### 2. E012-style config.h backfill
- config.status macro substitution unreliable on OHOS
- _fix_config_h() parses ac_cv_* yes-results from config.log and re-applies them into config.h
- Forced: PROMOTED_MODE_T=mode_t, HAVE_DECL_STRERROR_R=1, HAVE_STRERROR_R=1, STDC_HEADERS=1, PACKAGE_*/VERSION

### 3. config.sub (E007)
- 1.42 ships config.sub 2023 (older than 1.44's) which rejects `aarch64-unknown-linux-ohos`
- patches/0001-config-sub-ohos.patch backports `ohos*` OS + `linux-ohos*-` kernel case from newer config.sub

### 4. sys/types.h guards
- Not needed for 1.42: gl/sys_types.in.h has no blkcnt_t/blksize_t override
  (E119 conflict only affects newer gnulib snapshots as in 1.44)

## Configure Options
- --enable-static --disable-shared (R26)
- --disable-doc
- --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos (requires config.sub patch above)

## Test Results (R51 evidence)
- Upstream tests census: tests/Makefile.am `ctests` = 16 无条件用例 + tst_tld（TLD 启用）= **17**
  （此前 PR 描述写 18 是虚报，评审实测 N=17 正确；本次已按实测口径改正）
- 上游测试**已在 build() 中真实执行**（`make check -j1`），结果直接进 CI 构建日志（L1c 识别）：
  - `tests/`：`# TOTAL: 17  # PASS: 17  # SKIP: 0  # FAIL: 0  # ERROR: 0` → **17/17 = 100%**
  - `fuzz/`：`# TOTAL: 3  # PASS: 1  # SKIP: 2  # FAIL: 0`
    （2 个 fuzzer 由上游 Makefile 自身跳过：本工具链无 libFuzzer/AFL 驱动，非人为掩盖）
- 本地 W3 复验（与 CI 同命令 `conan create` + ohos-aarch64 profile）：PASS，
  日志含 `libidn/1.42: RUN: make check -j1`；16 项 tst_* + tst_tld 逐条 PASS，无 FAIL/ERROR
- test_package 真实运行 test_libidn 二进制：
  `ASCII domain: raksmorgas.example.org` / `test libidn 1.42: OK` → 1/1
- 上游测试代码未被修改。

## COMPLETED
最终状态: built
编译结束
