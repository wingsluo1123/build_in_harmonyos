# nettle 3.10.2 适配记录

**日期**: 2026-07-27
**状态**: 本地 Windows Conan 预审通过，等待远端 OHOS Conan CI

## 适配范围

- Autotools 构建 `libnettle` 和 `libhogweed`。
- 显式声明 `gmp/6.3.0` 依赖，避免 `hogweed` 在 configure 或消费端链接阶段缺失 GMP。
- 保留 HarmonyOS `config.guess` / `config.sub` 目标识别补丁。
- 禁用 shared library 和文档生成，降低交叉构建中的动态链接、Texinfo 工具依赖风险。
- 为 Autotools configure/config.status 强制设置包内私有 `TMPDIR`，对应 CI #1236 的
  `./conf*/subs1.awk: Permission denied` 临时文件权限失败。

## 本地测试与限制

- 本地 Windows native `conan create archives/n/nettle/3.10.2 --build=missing` 通过。
- 新增 `test_package` 消费测试覆盖 SHA-256 digest、hash 元数据查询、`hogweed` RSA public key 初始化和 GMP `mpz_t` 操作；本地结果为新增消费测试 1/1 通过，4/4 断言通过。
- 本地静态预审包含 Python 语法检查、YAML 解析、`git diff --check` 和敏感/占位符扫描。
- Buildbot #1236 日志已落盘到 `pipeline_logs/pr1874_conan-build-test_1236_20260712.json` 供本地排查；该目录不属于提交内容。
- 上游 `make check` 未在本地执行；本机官方 Conan 2.31.1 不含项目定制 `OHOS` settings，因此 OHOS profile 图预审停在 `Invalid setting 'OHOS'`。完整 OHOS aarch64 构建仍需远端 CI 的项目定制 Conan/settings 验证。
