# vile 9.8za 测试报告

> **项目**: vile  
> **测试日期**: 2026-10-01  
> **测试环境**: OHOS cross-build simulation (aarch64-linux-ohos, clang 15.0.4)  
> **测试类型**: Conan package verification + HarmonyOS ABI checks

## 测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 5 | 100% |
| 本地通过 | 3 | 60% |
| 失败 | 0 | 0% |
| 待 CI 执行 | 2 | 40% |

**本地可执行验证通过率**: 3/3。两个 runtime smoke 检查项由 `can_run()` 门控，将在 HarmonyOS CI worker 上执行。

## 测试结论

✅ **本地可执行部分通过；完整 runtime 结论待 CI**

- 上游 `make check`: 0 个批量测试（上游明确输出 `Sorry, no batch tests available.`）
- `conan create`: PASS
- ABI 检查: 3/3 PASS
- Runtime smoke: 2 项待 HarmonyOS CI 执行

## 测试详情

| 测试项 | 类型 | 本地结果 |
|--------|------|------|
| A1 ELF64 + EM_AARCH64 | HarmonyOS ABI | PASS |
| A2 OHOS musl interpreter | HarmonyOS ABI | PASS |
| A3 static ncurses linkage | HarmonyOS ABI | PASS |
| F1 `vile -V` version output | Runtime smoke | 待 CI |
| F2 `vile -x` usage output | Runtime smoke | 待 CI |

## 验证命令

```bash
python3 scripts/ohc-run.py conan-verify vile 9.8za --profile ohos-local
python3 scripts/ohc-run.py finish vile 9.8za built
python3 archives/v/vile/9.8za/test_package/ohos_abi_check.py --binary <package>/bin/vile
```

## 已知限制

- 本机为 macOS cross-build simulation，不能执行 aarch64-linux-ohos ELF。
- 上游没有正式批量测试套件，适配后补全 5 个独立检查项。
- F1/F2 必须在真实 HarmonyOS worker 上执行后才能形成最终通过率。
