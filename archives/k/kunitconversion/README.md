# KUnitConversion

## 软件描述
KUnitConversion 是 KDE Frameworks 6 的单位换算库：`libKF6UnitConversion.so`
（KF6::UnitConversion）提供 Converter / Value / Unit / UnitCategory 四类 API，
覆盖内置单位表的全部换算与格式化，以及 ECB 汇率表的下载与本地缓存。

Upstream: https://invent.kde.org/frameworks/kunitconversion

## 功能概述
- **换算 API**：`Converter::convert` / `Value::convertTo`（字符串与引用单位）、
  `Value::toSymbolString` 格式化、非法类别/单位/换算的处置
- **内置单位表**：Length / Temperature / Mass / Velocity / BinaryData 等静态表
  全量编译进库（22+ 类，含复合单位与符号）
- **货币表**：ECB 汇率表在线下载 + 本地缓存解析（OHOS CI 无出网——下载路径用例
  原地 QSKIP，离线快照路径全量覆盖）

## OHOS 适配

### 构建方式
- CMake + Conan 2（ohos-aarch64 剖面）；requires `qtbase/6.11.1`、`ki18n/6.26.0`；
  tool_requires `extra-cmake-modules/6.28.0`
- `BUILD_TESTING=ON`：上游 4 个 CTest 项在 build() 内编译并实跑；
  `BUILD_PYTHON_BINDINGS=OFF`（Shiboken6/PySide6 未随仓发布）
- 消费方式：`find_package(KF6 COMPONENTS UnitConversion)` 或 Conan 消费

### 关键攻坚点
1. **KF6 依赖天花板**（`patches/0001`）：`find_package(KF6I18n ${KF_DEP_VERSION})`
   的 6.28.0 地板被在仓 ki18n（最高 6.26.0）的 ConfigVersion 拒绝，降为 6.26.0；
   `ki18n_install(po)` 无需补丁——`KF_SKIP_PO_PROCESSING=ON` 使 KI18N_INSTALL() 早退
2. **E537 裸名链接**（`patches/0002`）：ki18n 6.26.0 的 `libKF6I18n.so` 无
   `DT_SONAME`，imported target 链接会把绝对缓存路径写进 `DT_NEEDED`；剔除 target、
   保留 include 目录、`-lKF6I18n` 裸名链接后制品 5 条 `DT_NEEDED` 全裸
3. **E330 无版本 SO + 显式 SONAME**：HMDFS 用户卷拒 `symlink()`（EPERM），上游
   VERSION/SOVERSION 的后置符号链直接失败构建；`CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`
   （双通道）+ `-Wl,-soname,` 产出单个无版本名 .so，`DT_SONAME` 裸名可重定位
4. **E731 QSKIP 网络边界**（`patches/0003`）：两个 ECB 下载用例在无出网沙箱原地
   QSKIP（验证逻辑保留）；离线货币路径（`valuetest::testCurrencyNotDownloaded`、
   `currencytableinittest` 快照表）全量覆盖；`.qttest` 数据目录预建（`QFile::copy`
   不建父目录）

### 与 Linux 的差异
- 两个 ECB 汇率表在线下载用例 QSKIP（沙箱无出网 HTTPS 路由；测试源码逻辑原样保留）
- HMDFS 无符号链：产出单个无版本名 `libKF6UnitConversion.so`（语义等价，
  `DT_SONAME` 裸名，下游 `DT_NEEDED` 可重定位）

## 依赖关系
- 运行期：`qtbase/6.11.1`、`ki18n/6.26.0`
- 构建期：`extra-cmake-modules/6.28.0`

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 6.28.0 | built | 2026-10-17 | 首次适配（新包）：真机八门禁 Verdict PASS；上游 CTest 4/4 执行项全过（17 个测试函数 15 通过 + 2 项网络 QSKIP）；消费者用例 17/17 + 6/6；`DT_NEEDED` 全裸、`DT_SONAME` 裸名 |

## 目录

```
kunitconversion/
├── manifest.yaml          # 软件级元信息与适配要点
├── README.md
└── 6.28.0/
    ├── conanfile.py       # 主配方（CMake 构建 + 上游 CTest + 运行期环境）
    ├── conandata.yml      # 官方源 + NJU 镜像回退 + sha256 + 3 补丁
    ├── manifest.yaml      # 版本级编译元数据
    ├── notes.md           # 本版适配笔记
    ├── patches/           # 0001 KF_DEP_VERSION / 0002 E537 裸名链接 / 0003 E731 QSKIP
    ├── reports/           # 脱敏八门禁报告（构建日志依平台规则不随档）
    └── test_package/      # Conan L1 消费者测试（17 + 6 检查）
```

## 参考资料
- 上游仓库: https://invent.kde.org/frameworks/kunitconversion
- KDE API 文档: https://api.kde.org/frameworks/kunitconversion/html/
