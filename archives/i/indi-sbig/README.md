# indi-sbig

## 软件描述
indi-sbig 是 INDI 生态中面向 **SBIG / Diffraction Limited** CCD 相机的驱动，由 indi-3rdparty 仓的
`indi-sbig/` 子目录构建，交付 `bin/indi_sbig_ccd`（`INDI::CCD`）与设备描述符
`share/indi/indi_sbig.xml`（把 `SBIG CCD`、`SBIG ST-I` 两个设备都登记到同一驱动）。

## 功能概述
- CCD 曝光/中止、bining/subframe、FITS 写盘（cfitsio）
- 制冷与温度调节（TE cooler 功率回读、温度状态机）、风扇状态
- 内建/外接滤光轮（CFW）支持：`CFW_PRODUCT` 产品信息、`FILTER_SLOT` 孔位与 `FILTER_NAME` 名称
- 自适应光学（AO）N/S/E/W 步进与回中
- USB 直连（libusb）+ 厂家库（libsbig）访问硬件

## OHOS 适配

### 构建方式
- **CMake 源码构建**：源码取自 Debian contrib pool 的 `indi-sbig_2.1+20221220234924.orig.tar.gz`
  （= indi-3rdparty 仓 `indi-sbig/` 子目录快照），sha256 见 `2.1/conandata.yml`

### 关键攻坚点
1. **INDI 2.x 属性 API 迁移**（补丁 0004）：`TemperatureN[0]`/`FilterSlotN[0]` 数组成员 → `TemperatureNP`/
   `FilterSlotNP` 的 `setMin/setMax/setValue` 与 `getMin/getMax/getValue`；`.s` → `setState/getState`；
   `IDSetNumber(&P,…)` → `P.apply()`；`IUUpdateMinMax(&P)` → `P.updateMinMax()`；`BayerT[2]` →
   `BayerTP[2].setText()`；FilterInterface 的 `FilterNameT` 数组不存在 → 用 `FilterNameTP.count()` 判断、
   `FilterNameTP.getName()` 比对、`deleteProperty(FilterNameTP)` 注销
2. **libusb 头路径**：`sbig_ccd.h` 用 `<libusb-1.0/libusb.h>`，需注入 include 根
3. **INDI_DATA_DIR 归本包**（补丁 0003，否则描述符落进 libindi 包）
4. **CMake 4 兼容 + C++17 + FindINDI 版本正则**（补丁 0001/0002/0003）

### 与 Linux 的差异
- 无源码级平台分支（macOS 分支与本平台无关）；差异集中在 INDI 2.x 迁移与打包路径
- 本沙箱不允许 `exec` OHOS 未签名 ELF，"真跑驱动"按有证据的宿主拒绝记 SKIP；静态校验全绿

## 依赖关系
- **构建/运行期**：`libindi/2.2.2.1`、`libsbig/4.9.9`、`cfitsio/4.6.4`、`zlib/1.3.1.1`、`libusb/1.0.27`

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 2.1 | built | 2026-10-15 | Debian contrib orig tarball；4 个可移植性补丁；消费者校验 4 项（3 通过 + 1 平台 SKIP） |

## 参考资料
- 上游仓库: https://github.com/indilib/indi-3rdparty
- 厂家: https://www.diffractionlimited.com/
