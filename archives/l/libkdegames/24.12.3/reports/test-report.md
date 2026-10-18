# libkdegames 24.12.3 测试报告（OHOS aarch64）

> 全部数据来自本机实跑，非推断。上游测试清点 → 实跑 → 结果回填（R51 三步法）。

## 1. 上游测试用例清点

上游 24.12.3 的 `src/private/tests/` 与 `tests/` 合计 **3 个测试目标**，但进入 ctest 的只有 **2 个**：

| 位置 | 注册方式 | 进 ctest | 断言数 | 说明 |
|------|---------|---------|--------|------|
| `src/private/tests/kgamesvgdocumenttest` | `ecm_add_test` | 是 | 113 | 自动化用例 |
| `src/private/tests/kgamepropertytest` | `ecm_add_test` | 是 | 11 | 自动化用例 |
| `tests/kgamepopupitemtest` | `ecm_mark_as_test(...)` | **否** | **0** | 手工 GUI 演示程序 |
| **合计** | — | **2** | **124** | `ctest --show-only` 实测只列出 2 条 |

### 第 3 个目标为什么不进 ctest（实测证据）

1. `ecm_mark_as_test()` 在 `BUILD_TESTING=ON` 时只作用于 `add_test` 已注册的目标；
   `tests/kgamepopupitemtest` 是 `add_executable` 直接创建、未 `add_test`，
   因此目标会被构建但**从不注册为 ctest 用例**（`ctest --show-only` 无该条目）。
2. 其源码 `tests/kgamepopupitemtest.cpp` **零断言**（无 `QCOMPARE`/`QVERIFY`/`QTEST_*`），
   `main()` 创建 `QGraphicsView` + `KGamePopupItem` 后直接 `app.exec()` 进入事件循环等待人工观察。
3. 无头环境下 `offscreen`/`minimal` 平台插件无显示后端，二进制启动即挂起；本机无 `xvfb`；
   `-v1` 类参数不被该程序接受。

结论：**本包上游自动化用例数为 2，不是 3**；第 3 个是手工演示程序，不构成可判定的自动化用例。

## 2. 上游自动化用例实跑结果

```
$ ctest --test-dir <build>/Release --show-only
  Test #1: libkdegamesprivate-kgamesvgdocumenttest   (113 断言)
  Test #2: libkdegamesprivate-kgamepropertytest       (11 断言)

$ ctest --test-dir <build>/Release --output-on-failure
  100% tests passed, 2 tests passed out of 2
```

- 通过率：**2/2（100%）**
- 断言总数：**124**，全部通过
- `ctest --output-on-failure --no-tests=error` 返回 0（确认用例真实存在且执行，非空跑）

## 3. 鸿蒙侧补测（test_package）

上游对 `KGamePopupItem` **无任何自动化用例**（唯一相关目标为零断言手工演示程序，见 §1），
故在 `test_package/test.cpp`（125 行）中补鸿蒙侧覆盖，实测 **PASS**（`conan create` 内执行）：

| 被测类 | 覆盖点 |
|--------|--------|
| `KGameClock` | `timeString()` 非空；`setTime()` → `seconds()` 往返一致（int 与 QString 两种重载） |
| `KGameTheme` | `identifier()` 一致；`setName()`/`name()` 往返；`setLicense()`+`setAuthor()` → `license()`/`author()` 往返；不存在的文件被拒绝 |
| `KGamePopupItem` | 默认 `hidesOnMouseClick()`；`setHideOnMouseClick()` 往返；`setSharpness(Sharp/Soft)` → `sharpness()` 往返；`forceHide(InstantHide)` 可调用 |

> 说明：`showMessage()` 的动画路径依赖 `QTimeLine` + 活动场景视图，无事件循环时
> 会在动画启动处段错误（实测 rc=139），因此补测只覆盖无头安全的 getter/状态机路径，
> 不伪造动画断言。

## 4. 结论

| 项目 | 结果 |
|------|------|
| 上游自动化用例 | **2/2 通过（124 断言）** |
| 上游第 3 个目标 | 零断言手工 GUI 演示程序，不可无头运行（原因见 §1） |
| 鸿蒙侧补测 | PASS（`KGamePopupItem` 等 3 类 getter 往返覆盖） |
| `conan create`（W3 / CI 同源） | exit_code=**0**；L0/L1/L4/L5 pass，L2 **skip**（纯库无 `bin/`，冒烟检查按设计跳过） |

### 4.1 L5 可重定位性门禁（首轮 fail → 已修复转 pass）

首轮 W3 实测为 `L5_RESULT=fail: soname_gate_failed`（5 项）：两个库缺 `DT_SONAME`；
`DT_NEEDED` 记录了依赖包绝对路径与 `../../bin/libKDEGames6.so` 相对路径；
`KDEGames6Targets-release.cmake` 带 `IMPORTED_NO_SONAME TRUE`。根因是 CMake 未加载
HarmonyOS 平台模块（日志 `System is unknown to cmake, create: Platform/HarmonyOS`），
`CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG` 未定义，链接期不带 `-soname`。

**修复（本轮已落地并在配方中）**：

1. `generate()` 在 OHOS 下显式设置 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` 与
   `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` / `..._CXX_FLAG="-Wl,-soname,"`，链接期补上 soname。
2. `package()` 调 `_sanitize_needed_entries()`：对 `lib/*.so` 做**原位 .dynstr 字节改写**，
   把路径形式的 `DT_NEEDED` 改为裸基名（只改写比目标更长的字符串，ELF 其余结构一字节不动），
   随后用 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`
   重签，避免改写后因签名失效被加载器拒绝（不用 `patchelf --replace-needed`：它会重写
   程序头表，产物被 OHOS musl 加载器拒绝）。

**修复后实测**（W3 日志 `reports/w3-local-ci.log`）：

```
NEEDED sanitized in libKDEGames6.so: 14
NEEDED sanitized in libKDEGames6Private.so: 12
DT_NEEDED entries sanitized: 26
L5_RESULT=pass: lib/ has content
```

产物复核：`readelf -d lib/libKDEGames6.so` → `SONAME` 存在，`DT_NEEDED` 中路径形式条目
计数为 **0**。`L0_RESULT/L1_RESULT/L4_RESULT` 同为 pass。

> 早期草稿曾把本项写成"门禁全绿"，经 W4 审计指出后按实测更正；随后按审计结论完成上述修复。
