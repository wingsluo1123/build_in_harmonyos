# DRAFT-7472：INDI FilterInterface 迁移与厂家静态库的 libusb 头路径

> Contributor: Lee-BX | Status: Draft | Updated: 2026-10-15
> Source: indi-sbig 2.1 HarmonyOS PC 适配（`archives/i/indi-sbig`）
> 对应：`knowledge/drafts/DRAFT-7472-indi-filter-interface-and-vendor-static-lib.kv`
> 相关：DRAFT-7467（属性 API 迁移总表）、DRAFT-7473（GuiderInterface 与 hidapi）

## 一、FilterInterface：`FilterNameT` 在 INDI 2.x 已不存在

### 现象

```text
error: use of undeclared identifier 'FilterNameT'
error: no member named 'name' in 'INDI::PropertyNumber'
error: 'operator&' is a protected member of 'INDI::PropertyBasic<_INumber>'
```

### 根因对照

| 用途 | INDI 1.x | INDI 2.x |
|---|---|---|
| 判断滤光片名是否已加载 | `if (FilterNameT != nullptr)` | `if (FilterNameTP.count() > 0)` |
| 比对属性名 | `strcmp(name, FilterNameTP->name)` | `strcmp(name, FilterNameTP.getName())` |
| 注销 | `deleteProperty(FilterNameTP->name)` | `deleteProperty(FilterNameTP)` |
| 孔位 | `FilterSlotN[0].min/.max/.value` + `FilterSlotNP.s` | `FilterSlotNP[0].setMin/setMax/setValue` + `setState/apply` |

### 正确做法

```cpp
if (FilterNameTP.count() > 0)              // 取代 if (FilterNameT != nullptr)
    deleteProperty(FilterNameTP);          // 取代 deleteProperty(FilterNameTP->name)

else if (!strcmp(name, FilterNameTP.getName()))   // 取代 FilterNameTP->name
    ...

FilterSlotNP[0].setMax(cfwResult2);
FilterSlotNP[0].setValue(cfwPosition);
if (FilterSlotNP[0].getValue() < FilterSlotNP[0].getMin())
    FilterSlotNP[0].setValue(FilterSlotNP[0].getMin());
FilterSlotNP.setState(IPS_ALERT);
FilterSlotNP.apply();
```

（`INDI::FilterInterface::processNumber()` 仍是 2.x 的正确入口，不需改。）

## 二、厂家静态库 + 版本前缀 libusb 头

```text
sbig_ccd.h:34:10: fatal error: 'libusb-1.0/libusb.h' file not found
```

驱动链接 `${SBIG_LIBRARIES}`（静态 libsbig.a）与 `${USB1_LIBRARIES}`，但头文件用的是
**版本前缀**路径 `<libusb-1.0/libusb.h>`；树内 `FindUSB1.cmake` 只把 leaf 目录
（`.../include/libusb-1.0`）放进 `USB1_INCLUDE_DIRS`，上游 CMakeLists 又从不把它加进 include
路径（Linux 发行版靠 `/usr/include` 恰好满足）。在 Conan 包布局下必须注入 include **根**：

```python
usb_inc = self.dependencies["libusb"].cpp_info.includedirs[0]
if os.path.basename(usb_inc) == "libusb-1.0":
    usb_inc = os.path.dirname(usb_inc)
tc.extra_cflags.append("-I%s" % usb_inc)
tc.extra_cxxflags.append("-I%s" % usb_inc)
```

## 验证（indi-sbig 实测）

```text
CREATE_RC=0
[ok]   bin/indi_sbig_ccd: AArch64 ELF64, 305664 bytes
[ok]   DT_NEEDED closure complete (libindidriver.so.2, libindiAlignmentDriver.so.2, libusb-1.0.so.0)
[ok]   share/indi/indi_sbig.xml: declares 'SBIG CCD' / 'SBIG ST-I' -> bin/indi_sbig_ccd
checks=4 fails=0 skips=1
RESULT: PASS
```

## 反例（禁止）

```cpp
if (FilterNameTP != nullptr)        // ✗ 2.x 是对象，空指针判断恒假
deleteProperty(FilterNameTP->name); // ✗ 对象没有 ->name
```

## 通用化建议

1. 迁移 INDI 老驱动时，把 `*N`（元素数组）与 `*NP`（属性对象）当成两套命名空间来对照替换，
   数组的"存在性/空值"判断在 2.x 统一变成属性对象的 `count()`/`getName()`。
2. 只要驱动的头文件里出现 `<libusb-1.0/libusb.h>`、`<ncursesw/...>` 这类版本前缀 include，
   就要检查树内 finder 给的是 leaf 还是 root —— 一律注入 **include 根**。
