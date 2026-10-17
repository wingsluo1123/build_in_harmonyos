# libest 1.0.0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make, libtool)
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤

```bash
# 官方 v1.0.0 tag tarball (sha256 301ebc8b...b57c8ce)
python3 scripts/ohc-run.py init-build libest 1.0.0 --url=https://github.com/cisco/libest/archive/refs/tags/v1.0.0.tar.gz
python3 scripts/ohc-run.py lang-preflight libest 1.0.0   # detected=c

cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX --with-ssl-dir=$DEFAULT_PREFIX
make -C src -j1        # 配方只构建库本体 (src/est), example/ 为演示程序不打包
make -C src install

# 配方验证
python3 scripts/ohc-run.py conan-verify libest 1.0.0    # G1-G4 + L2/L4/L5 全通过
python3 scripts/ohc-run.py finish libest 1.0.0 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess: cannot guess build type | 2012 版 config.guess 无 HarmonyOS 分支 (E007/E072) | patches/0001: 增加 HarmonyOS 分支输出 aarch64-unknown-linux-ohos |
| 2 | config.sub: machine not recognized | 2012 版 config.sub 无 ohos 三元组与 aarch64-unknown 机器识别 | patches/0002: ohos-linux/linux-ohos 识别 |
| 3 | configure/config.status: can't create ./confXXXXXX/subs1.awk: Permission denied | HMDFS 平台 umask 077 临时目录组写被禁 (E011/E052/E060/E112/E125) | patches/0003: configure 临时目录 umask 077→002 |
| 4 | OpenSSL 3.x 移除内部 API: c2i_ASN1_OBJECT / FIPS_mode / BIO_s_file_internal / EVP_MD_CTX 栈分配 / X509 等私有结构不透明 | libest 2014 年代码直访 OpenSSL 1.x 私有 API (E162 系同类) | patches/0004-0012: 全量迁移到公开 API (d2i_ASN1_OBJECT / EVP_MD_CTX_new / X509_get0_signature / X509_REQ_get_pubkey / X509_ATTRIBUTE_get0_type / DH_set0_pqg / EVP_default_properties_is_fips_enabled / BIO_s_file) |
| 5 | ld.lld: duplicate symbol e_ctx_ssl_exdata_index | est_locl.h 头文件非 extern 全局变量定义被多 TU 包含 (-fno-common) | patches/0010: 头文件改 extern, 定义保留在 est_client.c |
| 6 | test.c 无法 include openssl/ssl.h (from est.h) | openssl 包 CMakeDeps 元数据不导出 include 目录 | test_package/CMakeLists.txt: find_package(OpenSSL) + include openssl_PACKAGE_FOLDER/include + 链接 OpenSSL::SSL/Crypto/openssl::openssl |

## 源码修改

见 patches/0001-0012（12 个补丁）：config.guess/config.sub/configure 平台适配 +
src/est 与 example 的 OpenSSL 3.x 公开 API 迁移。

## 依赖版本

- openssl/3.5.6.1 (ohpcd 制品仓；libest 通过 --with-ssl-dir 指向 conan openssl 包)

## 验证结果

```bash
# conan-verify: G1/G0/G2(clean create)/G3/G4/L2/L4/L5 全过
# test_package: est_get_version / est_get_api_level / est_init_logger 3 断言全部通过
# W3 本地 CI: build_and_test.sh L0 pass (all checks passed)
# .ci-result.json exit_code=0
```

## 上游测试清点 (R51)

- 上游测试位于 `test/UT/`：CUnit 框架的 runtest 主程序 + 13 个用例目录
  (US748, US893-US903, US1005)，另有 test/util/ 的 st_server/st_proxy/curl_utils 支撑代码。
- **未在本环境运行的具体技术原因**：runtest 链接依赖 `-lcunit -lcurl`；本执行环境
  无 cunit 的 OHOS 预编译库（制品仓仅 recipe、系统无 CUnit 头/库），libcurl 开发库
  同样不可用，且上游未注册 automake TESTS/check 目标（无法 `make check` 触发）。
  已在 test_package/MANIFEST.yml 如实声明。
- 消费者视角验证由 test_package 独立完成（调用公开 API 3 项断言）。

## 交付物

- 源码 + 配方 PR-only：conanfile.py / conandata.yml / patches/ (12) / test_package/ /
  manifest.yaml / notes.md（Conan create 产物由制品仓发布流水线另行处理）
- 知识路径 B 草稿对：knowledge/drafts/DRAFT-libest-1.0.0-openssl3-private-api-migration.{kv,md}

## 注意事项

- 库本体只构建 src/est（libest.a + est.h → include/est）；example/ 演示程序依赖
  libcurl 且含 OpenSSL 1.x 私有 API 写法，不在配方构建范围。
- 本环境 /tmp 只读 (E002) 与 HMDFS 权限固定 (E046) 为平台限制，已记录不阻塞。
- upstream check 依赖 cunit/curl 未发布属依赖/基础设施缺口，记录为 R51 具体技术原因，
  非当前库缺陷。
---

**编译结束**: 2026-09-29 15:22
**最终状态**: published
