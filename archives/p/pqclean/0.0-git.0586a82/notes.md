# pqclean 0.0-git.0586a82 OHOS PC 适配笔记

## Upstream

- Repository: https://github.com/PQClean/PQClean
- Fixed commit: `0586a824fc0d49df0b6b6e9179d8d15d06d0974f` (master HEAD snapshot)
- License: CC0 / Public Domain (per-scheme LICENSE files)
- Language: C99
- Third-party dependencies: none

## 打包范围（裁剪说明）

PQClean 上游包含数十种后量子算法实现，本包按任务卡裁剪打包两个 NIST
标准化算法的 clean 实现：

- **ML-KEM-768**（Kyber，FIPS 203，KEM，NIST level 3）：
  crypto_kem/ml-kem-768/clean/，9 个源文件
- **ML-DSA-65**（Dilithium，FIPS 204，签名，NIST level 3）：
  crypto_sign/ml-dsa-65/clean/，8 个源文件
- **common/ 共享源**（两算法 Makefile 的 -I../../../common 依赖）：
  aes.c sha2.c fips202.c nistseedexpander.c sp800-185.c randombytes.c

未打包算法（falcon、sphincs、其余参数集等）不进入本包；依赖方需要时
另行打包。裁剪理由：单包聚焦两个标准化算法，避免全量打包体积与符号
冲突（上游各算法独立命名空间本可共存，但任务卡明确指定两算法范围）。

## Build

PQClean 无统一构建系统（根目录无 CMakeLists/顶层 Makefile，各算法目录
自带 Makefile）。配方按 smaz 0.0-git 先例直接编译：23 个 .c 源
（KEM 9 + SIGN 8 + common 6）以 OHOS Clang `-std=c99 -O3 -Wall -Wextra`
编译，`-I<scheme_dir> -I<common>`，llvm-ar 归档为单静态库 libpqclean.a。

randombytes.c 平台分支：OHOS clang 预定义 `__linux__`（且无 glibc），
走 `SYS_getrandom` syscall 分支，编译探测通过；/dev/urandom 可读作
兜底路径，两分支在本机均可用。

## Upstream tests

上游测试体系为 pytest 驱动的 test/Makefile 套件（functest/testvectors/
nistkat 等），其中 functest 为纯 C 功能测试。本包按上游 wiring 编译并
真跑两个 functest（源码零修改，仅按上游 Makefile 传命名空间宏）：

- `ml-kem-768 functest`：`-DPQCLEAN_NAMESPACE=PQCLEAN_MLKEM768_CLEAN
  -DNTESTS=1`，含 test_keys（keypair/enc/dec 往返+canary 校验）、
  test_invalid_sk_a、test_invalid_ciphertext 共 3 个测试函数
- `ml-dsa-65 functest`：`-DPQCLEAN_NAMESPACE=PQCLEAN_MLDSA65_CLEAN
  -DNTESTS=1`，含 test_sign、test_sign_detached、test_wrong_pk、
  test_func_ptrs 共 4 个测试函数

与上游差异：上游 CFLAGS 含 `-Werror -Wpedantic -Wvla`，本机 OHOS clang
对这些标志的额外诊断会阻断编译，配方保留 `-std=c99 -O3 -Wall -Wextra`
其余不变；测试源码本体未改。pytest 套件（lint/format/metadata 类）
非功能性测试，不在打包范围。

## Consumer test

test_package 一个可执行 9 断言：ML-KEM-768 keypair/enc/dec 返回码+
共享密钥一致+篡改 ct 不复现密钥；ML-DSA-65 keypair/签名/验签返回码+
签名长度界内+篡改消息验签拒绝。

## 验证结果

```bash
$ conan create . -pr:h=~/.conan2/profiles/ohos-aarch64 --build=missing
...
ML-KEM-768                    # kem functest: puts(CRYPTO_ALGNAME)
ml-kem-768 functest passed
ML-DSA-65                     # sign functest
ml-dsa-65 functest passed
pqclean 0.0-git.0586a82 OHOS test_package: all assertions passed
```
