# DRAFT-7473：INDI 驱动的 GuiderInterface 三段式迁移与 hidapi 依赖显式化

> Contributor: Lee-BX | Status: Draft | Updated: 2026-10-15
> Source: indi-sx 1.16-20221222162728 HarmonyOS PC 适配（`archives/i/indi-sx`）
> 对应：`knowledge/drafts/DRAFT-7473-indi-driver-hidapi-and-guider-interface-migration.kv`
> 相关：DRAFT-7467-indi-3rdparty-driver-indi2-property-api-migration（同族的属性 API 迁移）

## 一、GuiderInterface：INDI 2.x 的三段式改造

### 现象

```text
error: constructor for 'SXAO' must explicitly initialize the base class 'INDI::GuiderInterface'
error: use of undeclared identifier 'initGuiderProperties'
error: use of undeclared identifier 'processGuiderProperties'
error: 'operator&' is a protected member of 'INDI::PropertyBasic<_INumber>'
```

### 根因

| | INDI 1.x | INDI 2.x |
|---|---|---|
| 初始化 | `initGuiderProperties(dev, GUIDE_CONTROL_TAB)` | 构造函数 `GuiderInterface(DefaultDevice*)` + `initProperties(const char *groupName)` |
| 处理 | `processGuiderProperties(name, values, names, n)` | `processNumber(dev, name, values, names, n)` |
| 属性 | `INumberVectorProperty GuideNSNP/GuideWENP` | `INDI::PropertyNumber GuideNSNP/GuideWENP`（基类成员对象） |

### 正确做法（indi-sx 的 AO 驱动实测）

```cpp
SXAO::SXAO() : INDI::GuiderInterface(this) { setVersion(VERSION_MAJOR, VERSION_MINOR); }

bool SXAO::initProperties()
{
    DefaultDevice::initProperties();
    INDI::GuiderInterface::initProperties(GUIDE_CONTROL_TAB);   // 取代 initGuiderProperties(dev, tab)
    ...
}

bool SXAO::updateProperties()
{
    ... isConnected() ? defineProperty(GuideNSNP), defineProperty(GuideWENP)
                      : deleteProperty(GuideNSNP), deleteProperty(GuideWENP);   // 不再 .name
}

bool SXAO::ISNewNumber(const char *dev, const char *name, double values[], char *names[], int n)
{
    ...
    else if (!strcmp(name, GuideNSNP.getName()) || !strcmp(name, GuideWENP.getName()))
    {
        processNumber(dev, name, values, names, n);                  // 取代 processGuiderProperties(...)
        return true;
    }
}
```

注意：`defineProperty(&GuideNSNP)` 这种取址写法在 2.x 会撞上 protected 的 `operator&`；
基类属性一律传对象本身。驱动**自有**的 C 结构体属性（`AONSNP`/`AOWENP`/`CenterP`…）保持 `&` 不变。

## 二、hidapi：从"系统隐式提供"到"配方显式声明"

### 现象

```text
sxwheel.h:34:10: fatal error: 'hidapi.h' file not found
# 头补上之后，链接期：
undefined symbol: hid_open / hid_write / hid_read / hid_close
```

### 根因

驱动用**裸名** `#include <hidapi.h>` 并直接调用 `hid_*`，但上游 `CMakeLists.txt` 的链接行只有
`${INDI_LIBRARIES} ${USB1_LIBRARIES}`（Linux 发行版里 hidapi 的头/库由系统包装好，甚至 hidapi 本身
是 libusb 之上的薄层，所以上游"看起来能编"）。在制品仓 + 私有前缀环境下必须显式化：
头目录布局（`include/hidapi/hidapi.h` vs `include/hidapi.h`）、库名（libhidapi / libhidapi-libusb）、
链接顺序都要自己给。
同一类问题还有 `<libusb-1.0/libusb.h>` 这种**版本前缀 include**：树内 `FindUSB1.cmake` 只把 leaf 目录
（`.../include/libusb-1.0`）放进 `USB1_INCLUDE_DIRS`，而上游从不把它加进 include 路径。

### 正确做法（配方侧，idi-sx 实测）

```python
self.requires("hidapi/0.15.0")

inc = self.dependencies["hidapi"].cpp_info.includedirs[0]
if not os.path.isfile(os.path.join(inc, "hidapi.h")):
    inc = os.path.join(inc, "hidapi")                 # 兼容 include/hidapi/ 布局
tc.extra_cflags.append("-I%s" % inc)
tc.extra_cxxflags.append("-I%s" % inc)

usb_inc = self.dependencies["libusb"].cpp_info.includedirs[0]
if os.path.basename(usb_inc) == "libusb-1.0":
    usb_inc = os.path.dirname(usb_inc)                # 版本前缀 include 需要"根"
tc.extra_cflags.append("-I%s" % usb_inc)

for dep in ("hidapi", "libusb"):                      # 数据驱动，不硬编码库名
    info = self.dependencies[dep].cpp_info
    for d in (info.libdirs or []):
        tc.extra_exelinkflags.append("-L%s" % d)
    for l in (info.libs or []):
        tc.extra_exelinkflags.append("-l%s" % l)
```

## 验证

```text
# indi-sx 实测（conan create）
CREATE_RC=0
[ok] bin/indi_sx_ccd / indi_sx_wheel / indi_sx_ao：AArch64 ELF64
[ok] share/indi/indi_sx.xml 的 SX CCD / SX Wheel / SX AO 与 bin/ 交叉引用一致
[ok] 三个驱动 DT_NEEDED 闭包完整（libindidriver.so.2, libindiAlignmentDriver.so.2, libusb-1.0.so.0）
checks=9 fails=0 skips=3
RESULT: PASS
```

## 反例（禁止）

- 看到 `hidapi.h` 找不到就把滤光轮目标从构建里摘掉 —— hidapi 是制品仓已有的普通依赖，
  显式化即可，摘目标等于交付功能不完整的包。
- 只补 `-I` 不补链接行 —— 头过了、链接期才报 `undefined symbol: hid_open`，白跑一轮。

## 通用化建议

1. 上游"只链接一个库"不代表只需一个库：把驱动源码里所有 `#include <...>` 与 `hid_*/usb_*` 等外部符号
   和 CMakeLists 的链接行逐一对账，缺的在配方里显式补（数据驱动取 `cpp_info`，不要硬编码库名）。
2. 版本前缀 include（`<libusb-1.0/libusb.h>`、`<ncursesw/...>` 等）一律注入 **include 根**，
   而不是树内 finder 给出的 leaf 目录。
3. 迁移 INDI 老驱动时，先查宿主 `libindi` 头目录下对应接口的 2.x 形态（例如
   `indiguiderinterface.h` 的 `initProperties(const char*)` / `processNumber(...)`），
   照抄上游新写法最稳。
