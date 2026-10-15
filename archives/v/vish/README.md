# vish

VISA 命令行 shell（LibreVISA 项目）：通过 VISA 资源管理器打开仪器资源，发送
SCPI 风格命令并读取响应，支持 SRQ 事件轮询。上游为 Simon Richter 的
LibreVISA 工具链，GPL-3.0-or-later。

本项目适配鸿蒙 PC（aarch64）平台，作为独立 CLI 工具构建（package_type=application）。

## Versions

| Version | Status |
| --- | --- |
| 0.0.20130812 | built |

## 构建要点

真机池无 autoconf 且源码归档缺 config.guess/config.sub，故不跑 autotools：
直接以 CXX 编译 vish.cpp 并静态链接依赖 librevisa 包的 libvisa.a，编译时注入
`-D'PACKAGE="vish"' -D'VERSION="0.0.20130812"'` 宏替代 config.h。

Homepage: https://tracker.debian.org/pkg/vish
