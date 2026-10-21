# wifi-qr 0.4 — 鸿蒙PC (aarch64-linux-ohos) 适配笔记

## 上游
- 仓库: https://github.com/kokoye2007/wifi-qr （GPL-3.0+）
- 版本: 0.4（tag v0.4）
- 形态: 单一 bash 脚本 `wifi-qr`（1133 行）+ man page + desktop/icon/metainfo

## 语言预检（R47）
- lang-preflight: task=cpp, detected=c（顶层 Makefile），exit 0 兼容族通过。
- 实际主体为 bash 脚本——属 v12.21 §12 无构建/打包族（脚本工具），走 headeronly
  模板变体 C，conanfile 不定义 build()（禁止伪造编译日志，R34）。

## 打包方式
- package_type=application；bin/wifi-qr (chmod 755) + man1 + share/applications + icons
- requires: qrencode/4.1.1（创建二维码）、zbar/0.23.93（zbarimg 扫描解码）
- package_id 清空（无编译产物）
- commands.json（软件级，R38，type=tool）

## 功能依赖与降级
- 运行期依赖: bash、qrencode、zbarimg、nmcli（连接功能）；可选 zenity/kdialog、fzf、tput
- nmcli（NetworkManager）鸿蒙PC 无 → WiFi 扫描/连接功能不可用，脚本不崩溃
  （`command -v` 检测/缺失仅 stderr 提示）；二维码创建(-t/-c)与文件扫码(-f)功能完整可用
- tput 缺失仅产生 stderr 噪音，功能与退出码不受影响（保持上游原样，不打补丁）

## 上游测试三步法（R51）
1) 清点: 无 tests/，无 ctest/pytest；Makefile test-install 仅为安装演练 → 0 项
2) 实测: 无可运行上游测试 → test_package 消费者测试真实调用 `wifi-qr -v` / `-h`
3) 申报: 上游 0/0 (N/A)；test_package 2/2 通过（conan create 实测）

## 版本号（R37）
- 首次适配，无源码修改（0 补丁），版本保持上游 0.4。
---

**编译结束**: 2026-10-17 06:55
**最终状态**: published
