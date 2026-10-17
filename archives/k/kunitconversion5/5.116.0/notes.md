# kunitconversion5 5.116.0 适配笔记

## 编译环境
- 构建系统: cmake (KDE Extra CMake Modules)
- 编译日期: 2026-10-06
- 编译器: clang 15 (aarch64-linux-ohos)
- 状态: built

## 编译步骤

conan create archives/k/kunitconversion5/5.116.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | package() 阶段 cmake.install() 报 Error 127 + 大量 libc++ relocation 失败 | /data/service/hnp/bin/cmake 裸跑时 LD_LIBRARY_PATH 无兼容 libc++（build()/test() 阶段有 _runtime_env 包装所以正常） | package() 的 cmake.install() 与签名同用 with self._runtime_env().vars(self).apply() 包装 |
| 2 | 三个货币测试函数断言实时 ECB HTTPS 下载 | qt5-qtbase/5.15.2.2 线 Qt5Network 系 -no-openssl 构建（无 TLS 后端，strings 实测无 QSsl 符号）；CI 沙箱无外网路由 | 补丁 0001：单参数 QSKIP 原地守卫（Qt5.15 签名 QSKIP(statement, ...)，Qt6 才有 SkipSingle；kmbox/kservice 先例） |
| 3 | currencytableinittest 依赖 QFile::copy 写缓存目录 | QStandardPaths::setTestModeEnabled(true) 钉死 GenericDataLocation 到 $HOME/.qttest/share；QFile::copy 不创建父目录 | _deploy_currency_table_test_data() 预建 $HOME/.qttest/share/libkunitconversion/ 目录；Converter 随后离线解析 qrc 内嵌 currency.xml 快照（2021-08-24，USD rate 1.1740）通过 EUR->USD 断言 |
| 4 | find_package(Qt5 CONFIG REQUIRED Core Network) 解析 | CMakeDeps 小写配置会遮蔽 qt5-qtbase 原生聚合 Qt5Config | deps.set_property("qt5-qtbase", "cmake_find_mode", "none") + paths 文件写入 qt prefix（kitemviews5/kconfig5 先例） |
| 5 | autotests 是 QTEST 对象需 moc；上游无显式 AUTOMOC 设置 | ECM/KDECMakeSettings 默认开 CMAKE_AUTOMOC，但 CMakeDeps 不导出 Qt5::moc/rcc | tc.variables 注入 CMAKE_AUTOMOC_EXECUTABLE / CMAKE_AUTORCC_EXECUTABLE 指向 qt5-qtbase bin/ |
| 6 | Qt5CoreConfigExtrasMkspecDir.cmake 硬编码 <pkg>/../b/mkspecs/linux-clang | 打包缓存条目从未有构建树路径 | _prepare_qt_mkspec_compat 把包内 mkspecs 整树拷到预期位置（kitemviews5 先例） |
| 7 | ki18n5 (transitively gettext) 的 ki18n_install(po) 注册 pofiles 构建目标需要 msgfmt | 沙箱 PATH 无 msgfmt | GETTEXT_MSGFMT/MSGMERGE_EXECUTABLE 显式注入（kpeople5 先例；KF_SKIP_PO_PROCESSING=ON 双保险） |

## 上游测试三步法实测结果

- 清点：autotests/ BUILD_TESTING=ON 实际注册 **4 个 CTest 条目**（valuetest / categorytest / convertertest / currencytableinittest）。
- 函数级口径：**17 个测试函数 = 14 通过 + 3 QSKIP + 0 失败**：
  - valuetest: 7 PASS（initTestCase + 5 测试函数含 testCurrencyNotDownloaded + cleanupTestCase）
  - categorytest: 6 PASS + 1 SKIP（testCurrencyTableUpdate）
  - convertertest: 6 PASS + 2 SKIP（testCurrency / testCurrencyConversionTableUpdate）
  - currencytableinittest: 3 PASS（testCategoryInit 离线汇率表解析）
- 3 个 SKIP 均有具体技术原因（环境限制：Qt5Network -no-openssl 无 TLS 后端 + CI 沙箱无外网路由，ECB 汇率表无法下载）。
- CTest 汇总：100% tests passed, 0 tests failed out of 4。

## test_package 结果

- 14 断言全过（TEST_PACKAGE_RESULT pass=14 fail=0）：
  (1-3) Converter::convert 真实乘数跨类换算 km->m / C->F / kg->lb；
  (4-5) Value toSymbolString / convertTo 往返；
  (6-10) 类目查询五查（名称解析/默认单位/hasUnit/未知类目/未知单位）；
  (11) 类目计数 ≥20；
  (12-14) R53 ELF 三查（解析/DT_SONAME/DT_RUNPATH）。

## 本地预验证

- build1（修复前）：build+ctest 全绿，package() 因 cmake relocation 失败 → 定位问题 1。
- build2（修复后）：**rc=0 全绿**，证据 ~/huawei/tmp/kunitconv5/build2.log + build2.rc（值 0）。
- 干净重跑（conan remove + 重建）：见 PR 正文验证结果段。
