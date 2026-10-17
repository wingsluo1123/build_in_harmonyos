# E731：Qt 货币/汇率表下载测试的 QSKIP 网络边界守卫（TLS 后端缺失 + 沙箱无外网判定链）

## 错误特征

上游测试断言实时下载 ECB 汇率表（https://www.ecb.europa.eu），在 OHOS CI 环境下两类失败形态：

```
qt.network.ssl: QSslSocket: cannot resolve ...
TLS initialization failed                              ← Qt5Network -no-openssl 无 TLS 后端
qt.network.reply: Network session is not started       ← 沙箱无外网路由
Host www.ecb.europa.eu not found
```

## 根因（判定链）

1. **TLS 后端缺失**：qt5-qtbase/5.15.2.2 供应链线的 Qt5Network 为 -no-openssl 构建——`strings libQt5Network.so | grep -c QSsl` 实测为 0，https 请求在客户端即失败；
2. **沙箱无外网**：CI worker 是站点白名单网络，即使有 TLS 也无法到达 ECB。

网络前提双重不可满足 → **QSKIP 原地守卫**（保留测试函数与断言代码，跳过执行），而非删除测试或改断言。此类测试验证的是网络边界而非换算逻辑。

**Qt5/Qt6 签名差异（编译级陷阱）**：Qt 5.15 的 `QSKIP` 是 `QSKIP(statement, ...)` 变参宏；`SkipSingle`/`SkipAll` 枚举是 Qt 6 引入——Qt5 补丁写 `QSKIP("...", SkipSingle)` 会直接编译失败，必须用单参数形式。先例：kmbox 25.12.3 / kservice 6.x。

## 解法

patch 原地守卫（PR !14840 `patches/0001-ohos-skip-currency-network-autotests.patch`）：

```cpp
void ConverterTest::testCurrency()
{
    // OHOS: Qt5Network from the qt5-qtbase/5.15.2.2 supply is built with
    // -no-openssl (no TLS backend) and the CI sandbox has no outbound
    // network route, so the ECB currency-table download cannot run.
    QSKIP("currency-table network download needs TLS/network, unavailable on OHOS");

    Converter c;
    // ...original assertions preserved below...
}
```

守卫对象：`ConverterTest::testCurrency`、`ConverterTest::testCurrencyConversionTableUpdate`、`CategoryTest::testCurrencyTableUpdate`（三函数同一判定链）。

## 降级方案（数据路径必须真实验证时）

离线快照法（kunitconversion5 currencytableinittest 实证）：`QStandardPaths::setTestModeEnabled(true)` 钉死 GenericDataLocation 到 `$HOME/.qttest/share` → 配方预建 `libkunitconversion/` 缓存目录（QFile::copy 不创建父目录）→ Converter 离线解析 qrc 内嵌 currency.xml 快照（2021-08-24，USD rate 1.1740）并通过 EUR→USD 汇率断言。

## 实证

kunitconversion5 5.116.0（PR !14840，j669539）：17 函数 = 14 PASS + 3 QSKIP + 0 FAIL（CTest 4/4：`100% tests passed, 0 tests failed out of 4`）；3 个 SKIP 均为本条判定链覆盖（环境限制，测试替代）。
