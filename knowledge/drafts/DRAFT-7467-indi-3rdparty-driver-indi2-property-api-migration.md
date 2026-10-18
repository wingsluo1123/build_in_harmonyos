# DRAFT-7467：INDI 1.x 驱动的属性 API 在 INDI 2.x 下必须整体迁移

> Contributor: Lee-BX | Status: Draft | Updated: 2026-10-15
> Source: indi-fli 1.5-20221225141318 HarmonyOS PC 适配（`archives/i/indi-fli`）
> 对应：`knowledge/drafts/DRAFT-7467-indi-3rdparty-driver-indi2-property-api-migration.kv`
> 相关：DRAFT-10718-conan-package-type-drives-autotools-shared-static-flags（同类"上游契约变化引发成片改造"）

## 现象

拿一份 2022 年的 indi-3rdparty 驱动源码（`indi-fli`、`indi-gphoto`、`indi-beefocus`…）
配 INDI 2.x 的 `libindi` 编译，会得到一大片看似"缺成员"的错误：

```text
fli_pdf.cpp:262:5: error: use of undeclared identifier 'FocusAbsPosN'; did you mean 'FocusAbsPosNP'?
fli_pdf.cpp:266:20: error: 'operator&' is a protected member of 'INDI::PropertyBasic<_INumber>'
fli_pdf.cpp:335:26: error: no member named 's' in 'INDI::PropertyNumber'
fli_cfw.cpp:235:5: error: use of undeclared identifier 'FilterSlotN'; did you mean 'FilterSlotNP'?
fli_ccd.cpp:425:9: error: use of undeclared identifier 'TemperatureN'; did you mean 'TemperatureNP'?
```

配置期还可能先撞上两堵墙：

```text
CMake Error: failed to detect INDI version        # 树内 2022 版 FindINDI.cmake
error: no type named 'any' in namespace 'std'     # CMakeCommon 钉死 C++14，2.x 头用 std::any
```

## 根因

INDI 2.x 把**基类自带属性**从 C 结构体改成了 C++ 包装对象：

| | INDI 1.x | INDI 2.x |
|---|---|---|
| 属性本体 | `INumberVectorProperty FocusAbsPosNP;` | `INDI::PropertyNumber FocusAbsPosNP {1};` |
| 元素数组 | `INumber FocusAbsPosN[1];`（驱动源码里直接操作） | 不存在；用 `FocusAbsPosNP[i]` 得到的 `PropertyView` |
| 元素字段 | `FocusAbsPosN[0].min/.max/.step/.value` | `setMin/setMax/setStep/setValue`、`getMin/getMax/getValue` |
| 状态字段 | `FocusAbsPosNP.s` | `setState()/getState()` |
| 下发 | `IDSetNumber(&FocusAbsPosNP, …)` | `FocusAbsPosNP.apply(…)` |
| 极值重算 | `IUUpdateMinMax(&FocusAbsPosNP)` | `FocusAbsPosNP.updateMinMax()` |
| 注册/注销 | `defineProperty(&P)` / `deleteProperty(P.name)` | `defineProperty(P)` / `deleteProperty(P)` |

所以报错是"成组"出现的：只要驱动里有基线属性（温度/曝光/滤光片/调焦位置），
这五类写法必然同时存在。**驱动自己定义的** `ISwitch PortS[]` + `ISwitchVectorProperty PortSP`
之类仍走 C API，2.x 依旧支持——这部分**不要**动。

两个前置条件也属同一类"契约变化"：
1. `indiversion.h` 在 2.x 写成 `#define INDI_VERSION "2.2.2"`（带引号），
   2022 版 `FindINDI.cmake` 的正则 `INDI_VERSION ([0-9]+)…` 匹配不到 → 配置期直接 FATAL_ERROR；
2. INDI 2.x 的基类头（`defaultdevice.h`）使用 `std::any`，而驱动树内 `CMakeCommon.cmake`
   钉死 `CMAKE_CXX_STANDARD 14`。

## 正确做法

按"同一语义一一对应"批量替换（本仓 `indi-fli` 的 `patches/0004-fli-indi2-api.patch` 即此式，
与上游 2.2 源逐行一致）：

```cpp
// ① 元素读写
FocusAbsPosNP[0].setMin(1);
FocusAbsPosNP[0].setMax(FLIFocus.max_pos);
FocusAbsPosNP[0].setValue(FLIFocus.current_pos);
if (targetTicks > FocusAbsPosNP[0].getMax()) { … }

// ② 状态
switch (TemperatureNP.getState()) { … TemperatureNP.setState(IPS_IDLE); … }

// ③ 下发 / ④ 极值
TemperatureNP.updateMinMax();
TemperatureNP.apply();
TemperatureNP.apply("FLIGetCoolerPower() failed. %s.", strerror(-err));

// ⑤ 注册（仅基类属性）
defineProperty(FocusAbsPosNP);
deleteProperty(FocusAbsPosNP);

// ⑥ 前置条件：FindINDI 正则 + C++17
//    CMakeCommon.cmake: set(CMAKE_CXX_STANDARD 17)
```

## 验证

```sh
# 迁移后编译（indi-fli 实测只剩一条与迁移无关的告警）
ld.lld: warning: unknown -z value: nodump        # 树内 CMakeCommon 的 GNU ld 遗留旗标，lld 忽略

# 驱动真链接框架（消费者侧断言）
$ llvm-readelf -d <pkg>/bin/indi_fli_ccd | grep NEEDED
libindidriver.so.2
libindiAlignmentDriver.so.2
libusb-1.0.so.0

# conan create（含 test_package/check_driver.py）
checks=9 fails=0 skips=3
RESULT: PASS
```

同族实测：本仓 `indi-fishcamp`（1.1）、`indi-gpsnmea`（0.2）、`indi-beefocus`（0.1）、
`indi-gphoto`（3.2）、`indi-pentax`（1.0）、`indi-aok`/`indi-talon6` 都用了同一套迁移与
同一份 FindINDI 正则补丁（`0001` 在多个包里 byte-identical）。

## 反例（禁止）

```cpp
// ✗ 只改报错的那一行，漏掉状态/下发/注册，下一轮编译或运行期才炸
FocusAbsPosNP[0].setValue(pos);          // 正确改了
IDSetNumber(&FocusAbsPosNP, nullptr);    // 仍用旧的下发方式 → 编译错或运行期不更新
```

## 通用化建议

1. 遇到"基类成员成片找不到"的报错，先确认**宿主框架的代数**（`grep INDI_VERSION <libindi>/include/libindi/indiversion.h`），
   再去上游 master 找同一驱动目录的新写法——上游通常已经迁移过，照抄最省事、也最不容易引入行为差异。
2. 迁移时严格区分"框架自带属性"（必须换 API）与"驱动自有属性"（保持 C API），
   后者一起改只会放大回归面。
3. 这类"上游把结构体换成对象"的改造，验证必须是**编译 + 消费者侧动态/静态断言**两手：
   漏调 `apply()` 这类错误编译期查不出来。
