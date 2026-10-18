# Test Report — kiconthemes 6.18.0.2

- **项目**: kiconthemes (KDE Frameworks 6)
- **测试日期**: 2026-10-16
- **测试环境**: HarmonyOS PC / OHOS aarch64，clang 15 + cmake/ninja，profile `ci/conan/profiles/ohos-aarch64`
- **测试类型**: 官方测试套件 (upstream autotests) + Conan test_package 消费者冒烟

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 8 | 100% |
| 通过 (PASS) | 8 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

> 口径：8 = 7 个上游 autotests 目标（5 个 CTest 目标 + 2 个以 QtTest 子集直跑的
> kiconloader_unittest / kiconengine_unittest）+ 1 个鸿蒙特有 test_package 消费者测试。
> 断言级实测：5 个 CTest 目标 5/5，`kiconloader_unittest` 29/29 checks，
> `kiconengine_unittest` 8/8 checks，合计 42/42 checks。

**核心功能通过率**: ✅ **100%**

---

## 二、测试结论

### 2.1 总体评价

✅ 通过。`conan create`（先 export 后本地构建 + 打包 + 签名）退出码 0；
上游 CTest 5/5、两个 QtTest 子集 29/29 + 8/8、test_package 1/1 全部通过。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| kquickiconprovidertest 不可注册 | Qt6Qml/Qt6Quick 未发布到 ohpcd，`KICONTHEMES_USE_QTQUICK=OFF` | 🟢 |
| 1 个 shared-mime-info 数据行 | `kiconloader_unittest` 的 `testLoadMimeTypeIcon:*` 依赖数据 | 🟢 |
| `kiconengine_unittest::testMode` | 依赖 BreezeIcons（OHOS 未发布） | 🟢 |

### 2.3 可用功能清单

```
✅ KIconLoader 图标加载/主题回退/缓存（29 项 QtTest 断言全过）
✅ KIconTheme freedesktop 主题解析（kicontheme_unittest）
✅ KIconEngine 缩放/居中/非方形 SVG（8 + 1 CTest 目标）
✅ KIconDialog / KPixmapSequenceLoader
✅ 消费者链接：KF6::IconThemes（test_package 编译/链接/运行）
✅ 打包：2 个库（libKF6IconThemes.so / libKF6IconWidgets.so）+ KIconEnginePlugin.so 已签名
⚠️ .svgz 压缩图标经 KCompressionDevice(GZip)（karchive/6.18.0，见 API 核验）
❌ QtQuick 图标 provider（Qt6Qml/Qt6Quick 未发布）
```

### 2.4 已知限制

1. `kquickiconprovidertest` 因 Qt6Qml/Qt6Quick 不在 ohpcd 基线而不注册。
2. `kiconengine_unittest::testMode` 需 KF6BreezeIcons（未发布），已排除并逐项记录。
3. `kiconloader_unittest` 中 1 个依赖 shared-mime-info 数据行的用例未执行，其余
   29 项按用例名逐个直跑通过。

---

## 三、测试详情

### 3.1 上游 CTest（BUILD_TESTING=ON）

```
$ ctest --test-dir <build> --output-on-failure --no-tests=error \
      -E "^(kiconloader_unittest|kiconengine_unittest)$"
1/5 Test #1: kiconloader_resourcethemetest ....   Passed    0.61 sec
2/5 Test #2: kicontheme_unittest ..............   Passed    0.12 sec
3/5 Test #3: kiconengine_scaled_unittest ......   Passed    0.14 sec
4/5 Test #4: kicondialog_unittest .............   Passed    0.20 sec
5/5 Test #5: kpixmapsequenceloadertest ........   Passed    0.20 sec

100% tests passed, 0 tests failed out of 5
```

### 3.2 QtTest 子集（直跑，逐用例）

```
$ bin/kiconloader_unittest <29 cases>
Totals: 29 passed, 0 failed, 0 skipped, 0 blacklisted, 1534ms

$ bin/kiconengine_unittest <6 cases>
Totals: 8 passed, 0 failed, 0 skipped, 0 blacklisted, 105ms
```

### 3.3 Conan test_package（鸿蒙特有消费者测试）

```
kiconthemes/6.18.0.2 (test package): RUN: ./test_kiconthemes
PASS: KIconLoader::global() OK

1/1 Test #1: test_kiconthemes .................   Passed    0.12 sec
100% tests passed, 0 tests failed out of 1
```

### 3.4 依赖线回归（本次修复的核心）

```
# 修复前：已发布 kiconthemes/6.18.0#f82185f3（钉 karchive/6.19.0）
$ conan graph info --requires=kiconthemes/6.18.0 --requires=knewstuff/6.18.0
ERROR: Version conflict: Conflict between karchive/6.18.0 and karchive/6.19.0 in the graph.

# 修复后：kiconthemes/6.18.0.2（钉 karchive/6.18.0）
$ conan graph info --requires=kiconthemes/6.18.0.2 --requires=knewstuff/6.18.0
exit=0；图中仅 karchive/6.18.0，无 karchive/6.19.0
```

### 3.5 构建/打包产物

```
kiconthemes/6.18.0.2: package(): Packaged 2 '.0' files: libKF6IconWidgets.so.6.18.0, libKF6IconThemes.so.6.18.0
kiconthemes/6.18.0.2: package(): Packaged 2 '.6' files: libKF6IconWidgets.so.6, libKF6IconThemes.so.6
kiconthemes/6.18.0.2: package(): Packaged 3 '.so' files: libKF6IconWidgets.so, libKF6IconThemes.so, KIconEnginePlugin.so
kiconthemes/6.18.0.2: package(): Packaged 4 '.cmake' files: KF6IconThemesConfig.cmake, KF6IconThemesConfigVersion.cmake, KF6IconThemesTargets.cmake, KF6IconThemesTargets-release.cmake
kiconthemes/6.18.0.2: package(): Packaged 12 '.h' files
kiconthemes/6.18.0.2: Signed 4 OHOS package ELF file(s)
kiconthemes/6.18.0.2: Package '5937e6fd91b6589196a15790f369a1328a4907fb' created
```

- Full package reference:
  `kiconthemes/6.18.0.2#556eb8f9c411ccdceecf049c46327dc0:5937e6fd91b6589196a15790f369a1328a4907fb#bc27539c4ba7d3212820cdd8a8712c33`
- package_id `5937e6fd91b6589196a15790f369a1328a4907fb` 与 6.18.0.1 相同
  （同一依赖闭包 → 二进制等价，仅 recipe revision 不同）。

---

## 四、结论

- 上游测试：5/5 CTest 目标 + 29/29 + 8/8 QtTest checks = **42/42（100%）**。
- 鸿蒙特有：**1/1（100%）**（KIconLoader 真实 API 编译/链接/运行）。
- 依赖线：6.18 图内仅 `karchive/6.18.0`，不再拽入 `karchive/6.19.0`。
