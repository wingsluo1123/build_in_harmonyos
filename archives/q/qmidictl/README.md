# qmidictl

[QmidiCtl](https://qmidictl.sourceforge.io) 是一个基于 Qt6 的 MIDI 远程控制器：
把界面上的推子/旋钮动作通过 UDP/IP 组播发到网络，让另一台主机上的
MIDI 合成器（如 Qsynth）发声。上游由 Rui Nuno Capela（rncbc）维护。

- 上游版本：**1.0.2**
- 源码：`https://download.sf.net/qmidictl/qmidictl-1.0.2.tar.gz`
  （sha256 `5c9e04e560c564b03b6ebd451e310246418b8416f25e6038575bae16c34f4339`）
- 许可证：GPL-2.0-or-later
- 构建系统：CMake（>= 3.15，AUTOMOC/AUTOUIC/AUTORCC）
- 适配形态：`application`（Qt6 GUI 可执行文件 + 图标/桌面项/man page）

## 在 HarmonyOS PC 上安装与使用

```bash
conan install --requires=qmidictl/1.0.2 -pr:h=<ohos-aarch64 profile>
```

安装后的布局：

| 路径 | 内容 |
| --- | --- |
| `bin/qmidictl` | 主程序（打包期已自签，可直接 exec） |
| `share/applications/org.rncbc.qmidictl.desktop` | 桌面项 |
| `share/icons/hicolor/{32x32,scalable}/apps/org.rncbc.qmidictl.png\|svg` | 图标 |
| `share/metainfo/org.rncbc.qmidictl.metainfo.xml` | AppStream 元数据 |
| `share/man/man1/qmidictl.1`（含 `fr` 翻译） | man page |
| `licenses/LICENSE` | 许可证 |

命令行开关（上游 `src/qmidictlOptions.cpp`）：

```
-i, --interface <addr>   绑定/使用哪块网卡地址
-u, --udp-addr <addr>    目标组播地址
-p, --udp-port <port>    目标 UDP 端口
-m, --mmc-device <path>  额外的 MIDI 设备节点
-h, --help               用法
-v, --version            版本
```

> OHOS 无 X11/Wayland 时请以离屏平台运行，例如
> `QT_QPA_PLATFORM=offscreen qmidictl --version`（CI 探针即用此方式）。

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| qtbase | 6.11.1.3 | Qt6 Core / Gui / Widgets / Network |
| qtsvg | 6.11.1.1 | Qt6 Svg（应用图标与 qrc 资源） |

`qtsvg/6.11.1.1` 自身钉住 `qtbase/6.11.1.3`；本配方跟随该版本，避免图解析冲突
（详见 `1.0.2/notes.md`）。

## 适配要点

1. **Qt6 定位（E438）**：qtbase 包内自带可重定位的 `Qt6Config.cmake`
   （`cmake_find_mode=none`），配方通过 `CMAKE_PREFIX_PATH` / `Qt6_DIR` /
   `Qt6Svg_DIR` / `CMAKE_MODULE_PATH`（指向 `lib/cmake/Qt6/platforms`，
   其中 `Platform/HarmonyOS.cmake` include Linux）把 Qt6 交给 CMake。
2. **打包期自签（E077）**：OHOS 内核拒绝 exec 未签名 ELF（EPERM，rc=126），
   因此 `package()` 用 `binary-sign-tool sign -selfSign 1` 对 `bin/qmidictl`
   签名，使消费者与 CI 探针都能真正运行该二进制。
3. **上游零改动**：`patches: []`，不引入任何平台宏或源码补丁。

## 测试

上游 **不提供任何自动化测试**（tarball 顶层仅 `CMakeLists.txt` / `ChangeLog` /
`LICENSE` / `README` / `src`，无 `tests/` 目录，也无 `enable_testing()` /
`add_test()` 注册）。因此 L1 验证由 `1.0.2/test_package/` 承担：
`test_qmidictl.sh` 以 `QT_QPA_PLATFORM=offscreen` 真实执行安装后的二进制并断言
`--version` / `--help` 输出，同时核对 ELF 头、DT_NEEDED 中的 Qt6 运行库与安装的
桌面资源文件，合计 **16 条断言**（TP-001..TP-011 共 11 个测试项；TP-003 展开为
DT_NEEDED 解析 1 条 + 5 个 Qt6 运行库链接 5 条；实测 `PASSED (16/16)`）。

清点证据见 `1.0.2/test_package/MANIFEST.yml`，适配笔记见 `1.0.2/notes.md`。
