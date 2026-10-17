# indi-sbig 2.1 适配笔记

## 编译环境
- 构建系统: CMake（Debian contrib pool orig tarball）
- 编译日期: 2026-10-15
- 编译器: clang 15.0.4 / clang++（aarch64 OHOS，musl）
- 目标: HarmonyOS PC / aarch64（`ci/conan/profiles/ohos-aarch64`）
- 状态: built

## 版本说明
- 上游: https://github.com/indilib/indi-3rdparty（`indi-sbig/` 子目录），LGPL-2.1-or-later
- 源码: `https://deb.debian.org/debian/pool/contrib/i/indi-sbig/indi-sbig_2.1+20221220234924.orig.tar.gz`
  sha256 `54535a116c3305ab7e6b5e27cddfca2830379ec1e06cf06f44ffc9f0a61b3938`（82435 字节，R39）
- 配方版本号沿用平台任务号 `2.1`（Debian 版本为 `2.1+20221220234924-5`）

## 编译步骤
```bash
# build(): apply_conandata_patches → cmake.configure → cmake.build（-j2）
tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"      # E092
tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
tc.variables["INDI_ROOT"] = <libindi/2.2.2.1 包目录>
tc.extra_cflags += ["-I<libusb include 根>"]     # sbig_ccd.h 用 <libusb-1.0/libusb.h>
conan create archives/i/indi-sbig/2.1 -pr:h/…-pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案
| # | 问题（报错原文） | 根因 | 解决方案 |
|---|------------------|------|----------|
| 1 | `CMake Error at cmake_modules/FindINDI.cmake:215: failed to detect INDI version` | 2022 版正则不认 INDI 2.x 的 `INDI_VERSION "2.2.2"` 引号形式 | 补丁 0001（与 indi-fli/sx/fishcamp/gpsnmea/beefocus byte-identical） |
| 2 | `Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(VERSION 3.0)` | 补丁 0003 抬到 3.16（并传 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`） |
| 3 | 设备描述符被装进 libindi 包 | 树内 FindINDI 把 `INDI_DATA_DIR` 定成依赖包的数据目录 | 补丁 0003 在 `find_package(INDI)` 之前设为本包 `share/indi` |
| 4 | `use of undeclared identifier 'TemperatureN' / 'FilterSlotN' / 'FilterNameT'`、`no member named 's' in 'INDI::PropertyNumber'`、`'operator&' is a protected member of 'INDI::PropertyBasic<_INumber>'` | 驱动是 INDI 1.x 写法（基类属性是 C 结构体） | 补丁 0004：`TemperatureNP[0].setMin/setMax/setValue/getValue`、`FilterSlotNP[0].*`、`setState/getState`、`P.apply()`、`TemperatureNP.updateMinMax()`、`BayerTP[2].setText()`、`FilterNameTP.count()/getName()`、`defineProperty(FilterSlotNP)`/`deleteProperty(FilterSlotNP)` |
| 5 | `sbig_ccd.h:34: 'libusb-1.0/libusb.h' file not found`（首轮） | 头文件用版本前缀目录 include，树内 FindUSB1 只给 leaf 目录且上游从不加进 include 路径 | 配方 `generate()` 注入 libusb 的 include **根**（同 libfli / indi-sx） |
| 6 | `ld.lld: warning: unknown -z value: nodump` | 树内 CMakeCommon 的 GNU ld 专用旗标 | 非缺陷：lld 忽略并继续 |

## 源码修改
| 补丁 | 内容 | 行数 |
|------|------|------|
| `0001-FindINDI.cmake.patch` | 版本正则兼容 INDI 2.x | 12 |
| `0002-CMakeCommon-cxx17.patch` | `CMAKE_CXX_STANDARD` 14 → 17 | 12 |
| `0003-CMakeLists-ohos.patch` | CMake 4 兼容 + `INDI_DATA_DIR` 归本包 | 21 |
| `0004-sbig-indi2-api.patch` | sbig_ccd.cpp 的 INDI 2.x 迁移 | ~180 |

## 依赖版本
| 依赖 | 版本 | 说明 |
|------|------|------|
| libindi | 2.2.2.1 | 驱动框架 |
| libsbig | 4.9.9 | SBIG 厂家库（静态） |
| cfitsio | 4.6.4 | CCD 写 FITS |
| zlib | 1.3.1.1 | 图像压缩路径（上游 find_package(ZLIB REQUIRED)） |
| libusb | 1.0.27 | 驱动直连 USB；`sbig_ccd.h` 需要 include 根 |

## 验证结果
```bash
$ conan create archives/i/indi-sbig/2.1 -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64
# CREATE_RC=0；交付 bin/indi_sbig_ccd（305664 B）+ share/indi/indi_sbig.xml
[ok]   bin/indi_sbig_ccd: AArch64 ELF64, 305664 bytes
[ok]   DT_NEEDED closure complete (libindidriver.so.2, libindiAlignmentDriver.so.2, libusb-1.0.so.0)
[skip] host refused to start the OHOS binary: [Errno 1] Operation not permitted
[ok]   share/indi/indi_sbig.xml: declares 'SBIG CCD' / 'SBIG ST-I' -> bin/indi_sbig_ccd
checks=4 fails=0 skips=1
RESULT: PASS
```

### 上游测试清点（R51）
```text
$ grep -n "enable_testing\|add_test" CMakeLists.txt   # 无命中（只有 add_executable + install）
```
结论：**上游确无测试套件**；已补 `test_package/check_driver.py` 的消费者校验，`upstream_test_pass_rate` 如实填 N/A。

## 注意事项
1. XML 里两个设备（`SBIG CCD` / `SBIG ST-I`）共用同一个驱动名 `SBIG CCD` 与同一个可执行文件 —— 消费者校验按 `label=` 判别，并按驱动名核对。
2. 驱动含 macOS 专有分支（`loadFirmwareOnOSXifNeeded()` 用 kext 路径、`ezusb.c` 仅在 APPLE 下参与编译），Linux/OHOS 路径不受影响。
3. 驱动需要真实 SBIG 硬件；本沙箱无外设且宿主不允许 `exec` OHOS 未签名 ELF，故不做实机联调。
4. libindi 静态优先发布 → `package_info()` 声明 `LD_LIBRARY_PATH`（同 indi-fli/sx/aok/talon6）。
