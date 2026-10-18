# indi-fli

## 软件描述
indi-fli 是 INDI 生态中面向 **Finger Lakes Instrument（FLI）** 硬件的驱动集合，由 indi-3rdparty 仓的 `indi-fli/`
子目录构建，一次产出三个独立的 INDI 驱动可执行文件：

| 可执行文件 | 设备类型 | INDI 基类 | 默认设备名 |
|-----------|---------|-----------|-----------|
| `bin/indi_fli_ccd` | CCD 相机 | `INDI::CCD` | FLI CCD |
| `bin/indi_fli_focus` | 调焦器（PDF） | `INDI::Focuser` | FLI PDF |
| `bin/indi_fli_wheel` | 滤光轮（CFW） | `INDI::FilterWheel` | FLI CFW |

## 功能概述
- **CCD 相机**：连接（USB/串口/并口/INET 四种域）、制冷与温度读取（Cooler Power）、bining/subframe、
  曝光前 flush、后台 flush、曝光与中止、FITS 写盘（cfitsio）
- **调焦器**：绝对/相对移动、归零（Home）、当前步位读取、速度设定
- **滤光轮**：滤光片切换、位置查询、孔位上下限同步

## OHOS 适配

### 构建方式
- **CMake 源码构建**：源码取自 Debian main pool 的 `indi-fli_1.5+20221225141318.orig.tar.gz`
  （= indi-3rdparty 仓 `indi-fli/` 子目录快照），sha256 与顶层目录名见 `1.5-20221225141318/conandata.yml`
- **保留整棵驱动树**：`CMakeLists.txt` 会把 `cmake_modules/` 追加进 `CMAKE_MODULE_PATH`，
  `find_package(INDI/FLI/CFITSIO/ZLIB)` 都依赖它
- 未启用可选的 Kepler/FLIPRO 分支（需要非自由 FLIPRO SDK）

### 关键攻坚点
1. **INDI 2.x 属性 API 迁移**（补丁 0004）：驱动是 2022 年的 INDI 1.x 写法，基类属性（`TemperatureNP`、
   `FocusAbsPosNP`、`FilterSlotNP`…）在 2.x 变成 `INDI::Property*` 对象，数组成员与 `.s` 状态都要换成
   `setValue/getValue/updateMinMax/apply/setState/getState` 访问器
2. **树内 FindINDI.cmake 版本正则**（补丁 0001）：INDI 2.x 的 `#define INDI_VERSION "2.2.2"` 带引号，
   2022 版正则失配 → `failed to detect INDI version`
3. **C++14 → C++17**（补丁 0002）：`CMakeCommon.cmake` 钉死 C++14，而 INDI 2.x 头文件用 `std::any`
4. **静态 libfli.a 的 USB 依赖**（补丁 0003）：归档库的 USB 后端引用 libusb-1.0，必须显式
   `find_library(usb-1.0)` 并加入链接行（制品上体现为 `DT_NEEDED` 含 `libusb-1.0.so.0`）
5. **`INDI_DATA_DIR` 归属**（补丁 0003）：树内 finder 会把数据目录定成 libindi 包的绝对路径，
   改为本包 `share/indi`，设备描述符才不会被写进依赖包
6. **CMake 4 兼容**（补丁 0003）：上游 `cmake_minimum_required(VERSION 3.0)` 在 CMake ≥4 下硬报错

### 与 Linux 的差异
- 无源码级平台分支：驱动本身跨平台；差异集中在 **INDI 2.x API 迁移**与 **打包/运行环境**
  （libindi 的 `.so` 搜索路径需在 `package_info()` 里声明）
- 本适配沙箱对 OHOS 未签名 ELF 的 `exec` 受限，消费者校验中"真跑驱动"按有证据的宿主拒绝记 SKIP，
  静态校验（ELF/XML/DT_NEEDED）全部通过

## 依赖关系
- **构建/运行期**：`libindi/2.2.2.1`、`libfli/2.0-20221221182632`、`cfitsio/4.6.4`、`zlib/1.3.1.1`、`libusb/1.0.27`
  （均已合入制品仓）

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.5-20221225141318 | built | 2026-10-15 | Debian main pool orig tarball 快照；4 个可移植性补丁；消费者校验 9 项（6 通过 + 3 平台 SKIP） |

## 参考资料
- 上游仓库: https://github.com/indilib/indi-3rdparty
- FLI 官网: https://www.flicamera.com/
