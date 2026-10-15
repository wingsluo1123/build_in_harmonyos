# dnsfunnel 0.0.3.2 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15.0.4 (OHOS SDK)
- Conan 2.29.1, profile `ohos-aarch64`

## Verification

- `preflight_check.sh dnsfunnel/0.0.3.2`: exit 0 —— `s6-dns/2.4.1.0`、`skalibs/2.15.1.0` 均已在制品仓发布；版本号未被占用
- `conan-verify dnsfunnel 0.0.3.2`: exit 0 —— G0/G1/G2/G3/G4 全部 PASS；L2/L4/L5 按平台规则跳过（无可对比基线）
- W3 本地 CI 模拟（`ci/conan/setup.sh` + `ci/conan/build_and_test.sh`）: exit 0（`.ci-result.json` 的 `exit_code=0`）
- 上游 `make check`: exit 0，注册用例 0（`package/targets.mak` 的 `TEST_BINS` 为空、`src/tests/` 目录不存在）
- staging 树执行探针: 2 个二进制全部真实启动（`.staging-verified`: verified=2 failed=0）

## test_package

`test.sh` 直接运行包内真实安装的二进制，共 5 条断言：

1. `dnsfunneld` 非法选项 → 上游 usage 文本 + 退出码 100
2. `dnsfunnel-translate` 解析 resolv.conf → 写出 `caches`（9.9.9.9 / 8.8.8.8 / 1.1.1.1，回环地址按默认规则剔除）
3. `dnsfunnel-translate` 输入缺失 → 退出码 111
4. `dnsfunneld` 在非特权回环端口绑定并发出 `-1` 就绪信号
5. 端到端真实 DNS 转发：`dig +noedns` 经 `127.0.0.1:<port>` 取回 A 记录（外网 DNS 探针不可达时显式 `[skip]` 并在输出说明原因）

- Test cases: 5
- Passed: 5
- Failed: 0
- Skipped: 0（本机实测 5/5 全通过，耗时 2.5s；仅当外网 DNS 探针不可达时第 5 条显式跳过）

## Result

PASS
