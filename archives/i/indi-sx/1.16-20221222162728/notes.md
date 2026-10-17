# indi-sx 1.16-20221222162728 适配笔记

## 编译环境
- 构建系统: CMake（Debian main pool orig tarball）
- 编译日期: 2026-10-15
- 编译器: clang 15.0.4 / clang++（aarch64 OHOS，musl）
- 目标: HarmonyOS PC / aarch64（`ci/conan/profiles/ohos-aarch64`）
- 状态: built

## 版本说明
- 上游: https://github.com/indilib/indi-3rdparty（`indi-sx/` 子目录），LGPL-2.1-or-later
- 源码: `https://deb.debian.org/debian/pool/main/i/indi-sx/indi-sx_1.16+20221222162728.orig.tar.gz`
  sha256 `3adf4821e1a2c89918120163be360a0f3812fc7b459a6e164843310f0b90ed7e`（68108 字节，R39）
- 版本号沿用平台任务号 `1.16-20221222162728`（= 上游快照时间戳 `1.16+20221222162728`，`+`→`-`）
- URL 的 `+` 写字面量（`%2B` 会触发 CI pre-download 的 file:// 路径不一致）

## 编译步骤
```bash
# build(): apply_conandata_patches → cmake.configure → cmake.build（-j2）
tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"          # E092
tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
tc.variables["INDI_ROOT"] = <libindi/2.2.2.1 包目录>
tc.extra_cflags += ["-I<libusb include 根>", "-I<hidapi include>"]   # 见问题 3/4
tc.extra_exelinkflags += hidapi/libusb 的 -L/-l（数据驱动，见问题 3）
conan create archives/i/indi-sx/1.16-20221222162728 -pr:h/…-pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案
| # | 问题（报错原文） | 根因 | 解决方案 |
|---|------------------|------|----------|
| 1 | `failed to detect INDI version` | 2022 版 FindINDI 正则不认 INDI 2.x 的 `INDI_VERSION "2.2.2"` 引号形式 | 补丁 0001（与 indi-fli/fishcamp/gpsnmea/beefocus byte-identical） |
| 2 | `Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(VERSION 3.0)` | 补丁 0003 抬到 3.16（并传 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 兜底） |
| 3 | `sxwheel.h:34: 'hidapi.h' file not found`；链接期缺 `hid_*` 符号 | `sxwheel.cpp` 直接调 hidapi（`hid_open/hid_write/hid_read`），而上游 CMakeLists 只链接 USB1；制品仓有 `hidapi/0.15.0` | `requirements()` 加 `hidapi/0.15.0`；`generate()` 注入其头目录（兼容 `include/` 与 `include/hidapi/` 两种布局），并把 hidapi + libusb 的 libdir/libs 追加到 `extra_exelinkflags` |
| 4 | `sxccdusb.h:43: 'libusb-1.0/libusb.h' file not found` | 头文件用版本前缀目录 include，而 FindUSB1 只把 leaf 目录放进 `USB1_INCLUDE_DIRS`，上游又从不把它加进 include 路径 | 注入 libusb 的 **include 根**（basename 为 `libusb-1.0` 时取 dirname），与 libfli 配方同款处理 |
| 5 | udev 规则被写进宿主 `/lib/udev/rules.d/` | 上游 `set(RULES_INSTALL_DIR "/lib/udev/rules.d/")` 是绝对路径 | 补丁 0003 改为本包相对路径 `lib/udev/rules.d`（R49；同 libfli 的 `UDEVRULES_INSTALL_DIR` 处理） |
| 6 | 设备描述符安装位置错误 | 树内 FindINDI 会把 `INDI_DATA_DIR` 定成 **libindi 包**的数据目录 | 补丁 0003 在 `find_package(INDI)` 之前把它设为本包 `share/indi` |
| 7 | `use of undeclared identifier 'TemperatureN' / 'FilterSlotN'`、`'operator&' is a protected member of 'INDI::PropertyBasic<_INumber>'`、`no member named 's' in 'INDI::PropertyNumber'` | 驱动是 INDI 1.x 写法（基类属性是 C 结构体） | 补丁 0004：`TemperatureNP[0].setValue/getValue`、`FilterSlotNP[0].setMin/getMin/getMax`、`setState/getState`、`P.apply()`、`BayerTP[2].setText()` |
| 8 | `constructor for 'SXAO' must explicitly initialize the base class 'INDI::GuiderInterface'`；`use of undeclared identifier 'initGuiderProperties' / 'processGuiderProperties'` | INDI 2.x 的 GuiderInterface 改成三段式（构造传 DefaultDevice*、`initProperties(group)`、`processNumber(...)`） | 补丁 0004：`SXAO::SXAO() : INDI::GuiderInterface(this)`、`INDI::GuiderInterface::initProperties(GUIDE_CONTROL_TAB)`、`processNumber(dev, name, values, names, n)`；`defineProperty(GuideNSNP)`、`deleteProperty(GuideNSNP)`、`GuideNSNP.getName()` |
| 9 | `ld.lld: warning: unknown -z value: nodump` | 树内 CMakeCommon 的 GNU ld 专用加固旗标 | 非缺陷：lld 忽略并继续（上游遗留） |

## 源码修改
| 补丁 | 内容 | 行数 |
|------|------|------|
| `0001-FindINDI.cmake.patch` | 版本正则兼容 INDI 2.x | 12 |
| `0002-CMakeCommon-cxx17.patch` | `CMAKE_CXX_STANDARD` 14 → 17 | 12 |
| `0003-CMakeLists-ohos.patch` | CMake 4 兼容 + `RULES_INSTALL_DIR`/`INDI_DATA_DIR` 归本包 | 27 |
| `0004-sx-indi2-api.patch` | sxccd/sxwheel/sxao 的 INDI 2.x 迁移（含 GuiderInterface） | ~110 |

## 依赖版本
| 依赖 | 版本 | 说明 |
|------|------|------|
| libindi | 2.2.2.1 | 驱动框架 |
| cfitsio | 4.6.4 | CCD 写 FITS |
| libusb | 1.0.27 | CCD 走 libusb 直连；sxccdusb.h 需要 include 根 |
| hidapi | 0.15.0 | 滤光轮走 hidapi（hid_open/hid_write/hid_read） |

## 验证结果
```bash
$ conan create archives/i/indi-sx/1.16-20221222162728 -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64
# CREATE_RC=0；交付 bin/indi_sx_{ccd,wheel,ao}、bin/sx_ccd_test、share/indi/indi_sx.xml、lib/udev/rules.d/99-sx.rules
[ok]   bin/indi_sx_ccd: AArch64 ELF64, 113152 bytes
[ok]   bin/indi_sx_wheel: AArch64 ELF64, 47616 bytes
[ok]   bin/indi_sx_ao: AArch64 ELF64, 64000 bytes
[ok]   share/indi/indi_sx.xml: indi_sx_ccd ('SX CCD') -> bin/indi_sx_ccd
[ok]   share/indi/indi_sx.xml: indi_sx_wheel ('SX Wheel') -> bin/indi_sx_wheel
[ok]   share/indi/indi_sx.xml: indi_sx_ao ('SX AO') -> bin/indi_sx_ao
[ok]   indi_sx_ccd/wheel/ao: DT_NEEDED closure complete (libindidriver.so.2, libindiAlignmentDriver.so.2, libusb-1.0.so.0)
[skip] ×3: host refused to start the OHOS binary: [Errno 1] Operation not permitted
checks=9 fails=0 skips=3
RESULT: PASS
```

### 上游测试清点（R51）
```text
$ grep -n "enable_testing\|add_test" CMakeLists.txt     # 无命中
$ ls sxccdtest.cpp                                      # 交互式 USB 诊断工具（安装为 bin/sx_ccd_test），非自动化测试
```
结论：**上游确无测试套件**，已按赛事要求补 `test_package/check_driver.py` 的消费者校验，`upstream_test_pass_rate` 如实填 N/A。

## 注意事项
1. `sx_ccd_test` 是上游交互式诊断工具，随包交付但**不参与**消费者断言（它需要真实 USB 设备与人工交互）。
2. 驱动需要真实 SX 硬件（USB / 串口），本沙箱无外设且宿主不允许 `exec` OHOS 未签名 ELF，故不做实机联调。
3. libindi 静态优先发布 → `package_info()` 已声明 `LD_LIBRARY_PATH`（同 indi-aok/talon6/fli）。
