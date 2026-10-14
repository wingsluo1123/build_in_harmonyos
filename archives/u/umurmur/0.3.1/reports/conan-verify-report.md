# Conan Verify Report — umurmur 0.3.1

**Verdict**: PASS
**Reference**: `umurmur/0.3.1@ohpcd/stable`
**Profile**: `ohos-aarch64`
**Date**: 2026-10-12T16:38:09Z

## 实际执行结果

| 门禁 | 状态 | 说明 |
|---|---|---|
| G0 | PASS | 预构建风险查询完成 |
| G1 | PASS | 配方、来源、补丁和 `test_package` 完整性通过 |
| G2 | PASS | 干净 `conan create` 完成，消费者测试退出码为 0 |
| G3 | PASS | 系统同名库隔离检查通过 |
| G4 | 未执行完整 | 生成器输出 PASS，但同时注明未定位 package ID |
| L2 | SKIP | 生成器因未定位 cache 路径跳过 |
| L4 | SKIP | 生成器因未定位 cache 路径跳过 |
| L5 | SKIP | 生成器因未定位 cache 路径跳过 |

官方 `conan-verify` 命令整体退出码为 0。随后 `finish` 的 W3 本地 CI 模拟也以退出码 0 完成，日志 SHA256 为 `73b2823d1e9642a5623ff90c53d10748658223bb9ee5c90206a69eaa1284294d`。本地交叉执行明确设置 `QEMU_LD_PREFIX` 指向 AArch64 musl rootfs；这不替代同版本真机验证。这里保留生成器的真实边界，不把 G4 的诊断性 PASS 或 L2/L4/L5 的跳过写成“实际执行通过”。

## 独立补充覆盖

- `test_package` 检查最终 ELF 恰有一个 `.codesign`，且无 `RPATH/RUNPATH`、`.conan2`、本项目构建目录或 package folder。
- 消费者从无关工作目录不带 `-c` 运行配置校验，证明默认配置按可执行文件位置解析。
- HarmonyOS PC 真机完成 TLS、Protobuf-C、会话绑定 OCB UDP、公共 UDP、负例和守护进程生命周期闭环。
- 最终真机 ELF SHA256：`1eaa9a201fcae673b44b42c6537c57cd11b650a16af5e4427d7e159e2e9fd188`。

原始 Conan/W3 日志含本机构建缓存路径，不纳入提交；本报告仅保留脱敏结果、执行/跳过边界和可复核哈希。
