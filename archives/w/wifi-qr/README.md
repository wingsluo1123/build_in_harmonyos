# wifi-qr

终端环境创建/扫描 WiFi 二维码并自动连接的命令行工具（bash 脚本）。

- 上游: https://github.com/kokoye2007/wifi-qr （GPL-3.0+）
- 适配版本: 0.4
- 平台: 鸿蒙PC (aarch64-linux-ohos)
- 依赖: qrencode/4.1.1、zbar/0.23.93（Conan 提供 qrencode/zbarimg）
- 运行期可选: nmcli（NetworkManager，WiFi 扫描连接）、zenity/kdialog（GUI）、fzf
- 平台适配: shebang 改写为 `#!/usr/bin/env bash`（鸿蒙PC 无 /bin/bash）
