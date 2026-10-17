# indi-sx

## 软件描述
indi-sx 是 INDI 生态中面向 **Starlight Xpress（SX）** 硬件的驱动集合，由 indi-3rdparty 仓的 `indi-sx/`
子目录构建，一次产出三个 INDI 驱动与一个上游诊断工具：

| 可执行文件 | 设备类型 | INDI 基类 | 默认设备名 |
|-----------|---------|-----------|-----------|
| `bin/indi_sx_ccd` | CCD 相机（SXVF/SXVR/LodeStar/CoStar/SuperStar） | `INDI::CCD` | SX CCD |
| `bin/indi_sx_wheel` | USB 滤光轮 | `INDI::FilterWheel` | SX Wheel |
| `bin/indi_sx_ao` | 主动光学（AO） | `INDI::DefaultDevice` + `GuiderInterface` | SX AO |
| `bin/sx_ccd_test` | 上游交互式 USB 诊断工具（随包交付） | — | — |

## 功能概述
- **CCD**：USB 连接与设备枚举、制冷与温度回读、bining/subframe、曝光/中止、FITS 写盘（cfitsio）、Bayer 矩阵声明
- **滤光轮**：单/双向转动模式、孔位上下限同步、位置查询（走 hidapi）
- **主动光学**：N/S/E/W 四向步进、回中、解除卡滞、限位灯，并按 INDI 导星接口（GuiderInterface）响应 `GUIDE_NS/WE`

## OHOS 适配

### 构建方式
- **CMake 源码构建**：源码取自 Debian main pool 的 `indi-sx_1.16+20221222162728.orig.tar.gz`
  （= indi-3rdparty 仓 `indi-sx/` 子目录快照），sha256 与顶层目录名见 `1.16-20221222162728/conandata.yml`
- 保留整棵驱动树（`CMakeLists.txt` 会把 `cmake_modules/` 追加进 `CMAKE_MODULE_PATH`）

### 关键攻坚点
1. **INDI 2.x 属性 API 迁移**（补丁 0004）：`TemperatureN[0].value`、`FilterSlotN[0].min/max` 等基类 C 结构体成员
   改为 `TemperatureNP[0]`/`FilterSlotNP[0]` 的 `setValue/getValue/setMin/setMax`，`.s` 改 `setState/getState`，
   `IDSetNumber(&P,…)` 改 `P.apply()`，`BayerT[2]` 改 `BayerTP[2].setText()`
2. **GuiderInterface 三段式改造**（同一补丁）：2.x 要求 `构造函数 GuiderInterface(this)` +
   `initProperties(group)` + `processNumber(dev,name,values,names,n)`，替掉 1.x 的
   `initGuiderProperties(dev,tab)` / `processGuiderProperties(...)`
3. **hidapi 显式化**：`sxwheel.h` 用裸名 `<hidapi.h>`、`sxwheel.cpp` 直接调用 `hid_open/hid_write/hid_read`，
   而上游 CMakeLists 只链接 USB1 → 需 `requires("hidapi/0.15.0")`、注入其头目录并把 hidapi/libusb 的
   libdir/libs 放进链接行
4. **libusb 头路径**：`sxccdusb.h` 用版本前缀 `<libusb-1.0/libusb.h>`，而 FindUSB1 只给出 leaf 目录 →
   注入 libusb 的 include 根（同 libfli 的处理）
5. **不往宿主写文件**（补丁 0003）：`RULES_INSTALL_DIR` 上游是绝对路径 `/lib/udev/rules.d/`，
   改为本包私有 `lib/udev/rules.d`；`INDI_DATA_DIR` 改成本包 `share/indi`
6. **CMake 4 兼容 + C++17 + FindINDI 版本正则**（补丁 0001/0002/0003）

### 与 Linux 的差异
- 无源码级平台分支；差异集中在 **INDI 2.x API 迁移**（含 GuiderInterface）、**hidapi 依赖显式化**与打包路径
- 本适配沙箱对 OHOS 未签名 ELF 的 `exec` 受限，"真跑驱动"按有证据的宿主拒绝记 SKIP，静态校验全部通过

## 依赖关系
- **构建/运行期**：`libindi/2.2.2.1`、`cfitsio/4.6.4`、`libusb/1.0.27`、`hidapi/0.15.0`（均已合入制品仓）

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.16-20221222162728 | built | 2026-10-15 | Debian main pool orig tarball；4 个可移植性补丁；消费者校验 9 项（6 通过 + 3 平台 SKIP） |

## 参考资料
- 上游仓库: https://github.com/indilib/indi-3rdparty
- Starlight Xpress: https://www.sxccd.com/
