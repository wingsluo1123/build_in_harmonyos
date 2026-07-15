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
1. 源码获取: GitHub archive (Stefan-Schmidt/dfu-util)
2. 重新生成 autotools: `autoreconf -fi` (GitHub 归档未含预生成 configure)
3. Configure: `./configure --prefix=/usr/local` (通过 pkg-config 检测 libusb-1.0)
4. Make: `make -j$(nproc)`
5. Install: `make install`

## 依赖说明
- libusb/1.0.27: USB 设备访问库，dfu-util 通过 pkg-config 检测 libusb-1.0
  - 需设置 PKG_CONFIG_PATH / LDFLAGS / CPPFLAGS 指向 libusb (cmd-pkgs 预编译包)
  - 参考 dfu-programmer 的 pre-configure 处理方式

## 关键说明
- dfu-util 0.11 在 GitHub 仓库未打 tag (最新 tag 为 v0.7)，0.11 release 官方发布于 SourceForge。
  - conandata.yml 中 URL 暂用 GitHub archive 格式 (refs/tags/v0.11)，sha256 留空待实际构建时校验填充。
  - 若 GitHub 归档不可用，可改用 SourceForge 官方 release: https://sourceforge.net/projects/dfu-util/files/dfu-util-0.11.tar.gz
- 产物为终端工具 (dfu-util/dfu-suffix/dfu-prefix)，无可链接库，故 cpp_info.libs = []。
- 测试配方 test_package 编译占位 C 程序并运行 `dfu-util --version` 验证可执行文件可用。

## 质量门禁
G1-G4 待目标环境构建验证。
