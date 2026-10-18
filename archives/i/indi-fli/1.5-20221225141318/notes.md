# indi-fli 1.5-20221225141318 适配笔记

## 编译环境

- 构建系统: CMake（源码来自 Debian main pool 的 indi-fli orig tarball）
- 编译日期: 2026-10-15
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`）、clang++（aarch64 OHOS 目标）
- 目标: HarmonyOS PC / aarch64（`ci/conan/profiles/ohos-aarch64`，os.version 6.0，musl）
- 状态: built

## 版本说明

- 上游: https://github.com/indilib/indi-3rdparty（`indi-fli/` 子目录），LGPL-2.1-or-later
- 源码: `https://deb.debian.org/debian/pool/main/i/indi-fli/indi-fli_1.5+20221225141318.orig.tar.gz`
  sha256 `b8956302d74e944dfdba95cae510df4d86d4aecaee3745617b10a48510c000e2`（Debian main pool，R39）
- 版本号沿用平台任务号 `1.5-20221225141318`（= 上游子目录快照时间戳 `1.5+20221225141318`，Conan 版本串把 `+` 规范化为 `-`）
- URL 里的 `+` 写成字面量（**不要**写成 `%2B`）：CI 的 pre-download 步骤用 URL 末段拼 file:// 路径再 percent-decode，
  写成 `%2B` 时磁盘上按字面 `+` 查找、而缓存文件名保留 `%2B` → `FileNotFoundError`（与 libfli / indi-gpsnmea 同注）

## 编译步骤

```bash
# 配方内部（build()）：apply_conandata_patches → cmake.configure → cmake.build
tc.variables["CMAKE_SYSTEM_NAME"]  = "Linux"     # E092：CMake 无 HarmonyOS 平台
tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
tc.variables["INDI_ROOT"] = <libindi/2.2.2.1 包目录>   # 树内 FindINDI.cmake 的提示变量
tc.blocks["prefer_config_off"] = PreferConfigOffBlock  # 让树内 Find*.cmake 生效
cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
cmake.build(cli_args=["-j2"])                    # R9 保守并行
cmake.install()                                  # bin/indi_fli_{ccd,wheel,focus} + share/indi/indi_fli.xml

conan create archives/i/indi-fli/1.5-20221225141318 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题（报错原文） | 根因 | 解决方案 |
|---|------------------|------|----------|
| 1 | `CMake Error: failed to detect INDI version` | 树内 2022 版 `cmake_modules/FindINDI.cmake` 用 `MATCHES ".*INDI_VERSION ([0-9]+)…"` 匹配 `indiversion.h`；INDI 2.x 写的是 `#define INDI_VERSION "2.2.2"`（**带引号**），正则失配 | 补丁 0001：正则改为 `INDI_VERSION[ ]+"?([0-9]+)\.([0-9]+)\.([0-9]+)"?`（回移上游 master 修复，与 indi-fishcamp/indi-gpsnmea/indi-beefocus 的 0001 byte-identical） |
| 2 | `CMake Error: Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(VERSION 3.0)`，CMake 4.x 不再兼容 3.5 以下 | 补丁 0003 把声明抬到 3.16；build() 同时传 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 兜底 |
| 3 | `no type named 'any' in namespace 'std'` | 树内 `CMakeCommon.cmake` 钉死 `CMAKE_CXX_STANDARD 14`，而 INDI 2.x 基类头（`defaultdevice.h`）使用 `std::any` | 补丁 0002 抬到 17（回移上游 master 同一处改动） |
| 4 | 链接期 `undefined symbol: libusb_*`（libfli.a 的 USB 后端） | 驱动链接的是**静态** `libfli.a`（制品仓默认 shared=False），归档里的 `libfli-usb-sys.o` 引用 libusb-1.0 符号，而 2022 快照的 CMakeLists **没有 FindUSB1 wiring**；上游靠系统 `/usr/include`+`-lusb-1.0` 隐式带上 | 补丁 0003：`find_library(USB1_LIBRARY NAMES usb-1.0)` 并加入三个可执行文件的链接行。制品上体现为 `DT_NEEDED` 含 `libusb-1.0.so.0`（test_package 已把这一点做成断言） |
| 5 | 设备描述符被装进**依赖包**（`share/indi/indi_fli.xml` 落到 libindi 包目录） | 树内 `FindINDI.cmake` 的 `find_path(INDI_DATA_DIR … share/indi)` 在 `INDI_ROOT`(= libindi 包) 下找到了数据目录，而 `install(FILES … DESTINATION ${INDI_DATA_DIR})` 直接用它 | 补丁 0003：`set(INDI_DATA_DIR "share/indi")`（相对路径，R49 不写别人/系统的前缀） |
| 6 | 编译期大量 `use of undeclared identifier 'TemperatureN'` / `'FilterSlotN'` / `'FocusAbsPosN'`；`'operator&' is a protected member of 'INDI::PropertyBasic<_INumber>'`；`no member named 's' in 'INDI::PropertyNumber'` | 驱动是 2022 年的 INDI **1.x** 写法：基类的 `TemperatureN`/`FilterSlotN`/`FocusAbsPosN`/`FocusRelPosN`/`FocusSpeedN` 与 `TemperatureNP`/`FocusAbsPosNP` 等都是 C 结构体；INDI 2.x 把它们换成了 `INDI::Property*` 对象（`operator&` 受保护、没有 `.s`/`.min` 字段） | 补丁 0004：按上游 2.2 源的同一套写法迁移（`[i].setMin/setMax/setValue`、`getMin/getMax/getValue`、`setState()/getState()`、`P.updateMinMax()`、`P.apply(...)`；基类属性 `defineProperty(P)`/`deleteProperty(P)`）。驱动**自有**的 C 结构体属性（`PortSP`/`CoolerNP`/`HomeSP`/`TurnWheelSP`…）保持原样 |
| 7 | `ld.lld: warning: unknown -z value: nodump` | 树内 `CMakeCommon.cmake` 给可执行文件加了 GNU ld 专用加固旗标 `-Wl,-z,nodump`，lld 不识别该值 | **不是缺陷**：lld 仅告警并忽略，链接产物正常（属上游构建脚本遗留，本包不改） |

## 源码修改

| 补丁 | 内容 | 行数 |
|------|------|------|
| `0001-FindINDI.cmake.patch` | `cmake_modules/FindINDI.cmake` 版本号正则兼容 INDI 2.x 引号形式 | 12 |
| `0002-CMakeCommon-cxx17.patch` | `cmake_modules/CMakeCommon.cmake` 的 `CMAKE_CXX_STANDARD` 14 → 17 | 12 |
| `0003-CMakeLists-ohos.patch` | `cmake_minimum_required` 3.0 → 3.16；补 `find_library(usb-1.0)` 并加入三条链接行；`INDI_DATA_DIR` 指向本包 `share/indi` | 22 |
| `0004-fli-indi2-api.patch` | `fli_ccd.cpp` / `fli_cfw.cpp` / `fli_pdf.cpp` 由 INDI 1.x 属性 API 迁移到 INDI 2.x | 42 |

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| libindi | 2.2.2.1 | INDI 驱动框架（`libindidriver.so.2` / `libindiAlignmentDriver.so.2`） |
| libfli | 2.0-20221221182632 | FLI 相机/滤光轮/调焦器控制库（静态 `libfli.a`） |
| cfitsio | 4.6.4 | CCD 驱动写 FITS 用（`find_package(CFITSIO REQUIRED)`） |
| zlib | 1.3.1.1 | FLI CCD 的图像压缩/解压路径 |
| libusb | 1.0.27 | 静态 libfli.a 的 USB 后端运行期依赖（补丁 0003 加入链接行） |

## 验证结果

```bash
$ conan create archives/i/indi-fli/1.5-20221225141318 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 编译: CREATE_RC=0（包 indi-fli/1.5-20221225141318）
# 交付: bin/indi_fli_ccd、bin/indi_fli_focus、bin/indi_fli_wheel、share/indi/indi_fli.xml

# 消费者用例（test_package/check_driver.py，9 项校验）
[ok]   bin/indi_fli_ccd: AArch64 ELF64, 211456 bytes
[ok]   bin/indi_fli_focus: AArch64 ELF64, 154112 bytes
[ok]   bin/indi_fli_wheel: AArch64 ELF64, 150016 bytes
[ok]   share/indi/indi_fli.xml: indi_fli_ccd ('FLI CCD') -> bin/indi_fli_ccd
[ok]   share/indi/indi_fli.xml: indi_fli_focus ('FLI PDF') -> bin/indi_fli_focus
[ok]   share/indi/indi_fli.xml: indi_fli_wheel ('FLI CFW') -> bin/indi_fli_wheel
[ok]   indi_fli_ccd: DT_NEEDED closure complete (libindidriver.so.2, libindiAlignmentDriver.so.2, libusb-1.0.so.0)
[skip] indi_fli_ccd: host refused to start the OHOS binary: [Errno 1] Operation not permitted
[ok]   indi_fli_focus: DT_NEEDED closure complete (...)
[skip] indi_fli_focus: host refused to start the OHOS binary: [Errno 1] Operation not permitted
[ok]   indi_fli_wheel: DT_NEEDED closure complete (...)
[skip] indi_fli_wheel: host refused to start the OHOS binary: [Errno 1] Operation not permitted
checks=9 fails=0 skips=3
RESULT: PASS
```

### 上游测试清点（R51，留证）

```text
$ ls indi-fli-1.5+20221225141318/            # 16 个文件 + cmake_modules/
AUTHORS CMakeLists.txt INSTALL README config.h.cmake fli_ccd.cpp fli_ccd.h
fli_cfw.cpp fli_cfw.h fli_pdf.cpp fli_pdf.h indi_fli.xml.cmake
indi_flipro.xml.cmake kepler.cpp kepler.h cmake_modules/
$ grep -n "enable_testing\|add_test\|add_custom_target(.*test" CMakeLists.txt
（无命中：只有 add_executable 与 install）
```

结论：**上游确无测试套件**（该驱动子项目与整棵 indi-3rdparty 仓都没有 test 用例），已按赛事要求"没有测试用例要说明原因
并自行补充"补上 `test_package/check_driver.py` 的消费者校验；`upstream_test_pass_rate` 如实填 N/A。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/indi_fli_ccd` | FLI CCD 相机驱动（`INDI::CCD` 派生，`getDefaultName()="FLI CCD"`） |
| `bin/indi_fli_focus` | FLI PDF 调焦器驱动（`INDI::Focuser` 派生，"FLI PDF"） |
| `bin/indi_fli_wheel` | FLI CFW 滤光轮驱动（`INDI::FilterWheel` 派生，"FLI CFW"） |
| `share/indi/indi_fli.xml` | INDI 设备描述符（三个设备分组：CCDs / Focusers / Filter Wheels） |

## 注意事项

1. **Kepler/FLIPRO 分支未启用**：上游 CMakeLists 用 `if (FLIPRO_FOUND)` 把 `indi_kepler_ccd` 与
   `indi_flipro.xml` 作为可选项，需要非自由的 FLIPRO SDK（`find_package(FLIPRO)`，制品仓无该包）。未启用不影响
   CCD/调焦器/滤光轮三个驱动，符合"可选后端不引入"的既有口径。
2. **上游无测试**：见上（R51 清点）。
3. **运行期需要 libindi 的 `.so` 搜索路径**：libindi 以静态优先发布，Conan 不会把它的 lib 目录放进运行环境；
   `package_info()` 里已 `runenv_info.prepend_path("LD_LIBRARY_PATH", <libindi libdir>)`（同 indi-aok/indi-talon6）。
4. **宿主的 OHOS 未签名 ELF 限制**：本适配沙箱无法 `exec` 打包后的 OHOS 可执行文件（Errno 1 Operation not permitted），
   因此消费者校验里的"真跑驱动"一项按**有证据的宿主拒绝**记 SKIP；静态闭包审计（ELF/XML/DT_NEEDED）全部通过。
5. **两处上游遗留注释**：`fli_ccd.cpp` 与 `fli_cfw.cpp` 各有一行被注释掉的旧 API 写法（`TemperatureNP.s = …`、
   `FilterSlotN[0].min`），属上游历史残留，不影响编译与运行，本包按"最小改动"原则保持原样。
---

**编译结束**: 2026-10-15 19:46
**最终状态**: built
