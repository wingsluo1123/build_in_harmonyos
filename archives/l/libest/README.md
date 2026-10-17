# libest

libest 是 Cisco 的 EST（Enrollment over Secure Transport, RFC 7030）库，
以 C 语言实现，用于安全证书签发流程，兼容 Suite B 及 RSA/DSA 证书。

- 上游仓库: https://github.com/cisco/libest
- 适配版本: 1.0.0 (tag v1.0.0)
- 适配路径: `archives/l/libest/1.0.0/`
- 构建系统: autotools (configure + make, libtool)
- 依赖: openssl/3.5.6.1 (ohpcd 制品仓)
- 平台: HarmonyOS PC (aarch64, aarch64-unknown-linux-ohos)

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.0.0 | published | OpenSSL 3.5.x 公开 API 迁移适配；知识路径 B（OpenSSL3 私有 API/结构迁移草稿） |

## 说明

- 库本体只构建 `src/est`（libest.a / libest.so.1.0.0 + 头文件 include/est/est.h）；
  `example/` 演示程序依赖 libcurl 且含 OpenSSL 1.x 私有 API 写法，不在配方构建范围。
- 上游测试 `test/UT`（CUnit 框架，13 用例）因测试源码使用 OpenSSL 1.x 私有 API、
  与本机 OpenSSL 3.5.6 公开头不兼容而不可运行（详见 notes.md R51 清点与 r02 逐入口台账）。
