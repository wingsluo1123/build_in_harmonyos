# dfu-util 0.11 适配笔记

## 软件信息
- 名字: dfu-util
- 版本: 0.11
- 类型: 【积分赛】USB DFU 固件升级工具
- 官方源: http://dfu-util.sourceforge.net/
- GitHub: https://github.com/Stefan-Schmidt/dfu-util
- 构建系统: autotools (configure + make)
- 产物: dfu-util, dfu-suffix, dfu-prefix 可执行文件
- 依赖: libusb

## 构建环境
- 目标: HarmonyOS PC (aarch64)
- 构建系统: autotools
- 编译器: clang / clang++
- 状态: archived (配方已创建，待目标环境实际构建验证)

## 构建步骤
1. 源码获取: SourceForge 官方 `dfu-util-0.11.tar.gz`
2. 使用发布包自带的预生成 `configure`
3. Configure: `./configure --prefix=/usr/local` (通过 pkg-config 检测 libusb-1.0)
4. Make: `make -j$(nproc)`
5. Install: `make install`

## 依赖说明
- libusb/1.0.27: USB 设备访问库，dfu-util 通过 pkg-config 检测 libusb-1.0
  - 需设置 PKG_CONFIG_PATH / LDFLAGS / CPPFLAGS 指向 libusb (cmd-pkgs 预编译包)
  - 参考 dfu-programmer 的 pre-configure 处理方式

## 关键说明
- dfu-util 0.11 官方发布于 SourceForge，SHA-256 为 `b4b53ba21a82ef7e3d4c47df2952adf5fa494f499b6b0b57c58c5d04ae8ff19e`。
- 产物为终端工具 (dfu-util/dfu-suffix/dfu-prefix)，无可链接库，故 cpp_info.libs = []。
- `test_package/test.sh` 执行 dfu-util、dfu-prefix 和 dfu-suffix，并核对版本输出。

## 质量门禁
G1-G4 待目标环境构建验证。
