# indi-dsi

INDI 天文框架的 **Meade DSI/DSI II/DSI III（Pro & Color）相机驱动**（C++ 可执行程序，非库）。

- 上游：[indilib/indi-3rdparty](https://github.com/indilib/indi-3rdparty)（`indi-dsi/`，本包源码为 2022-12-23 快照，Debian `indi-dsi_0.4+20221223123028.orig.tar.gz`）
- 协议：USB bulk（DsiDevice 层 libusb-1.0 直连；首连经 fx2 固件上传，固件 `meade-deepskyimager.hex` 随包安装）
- 产物：`bin/indi_dsi_ccd`（INDI::CCD 子类驱动，由 INDI 服务框架加载运行）；`share/firmware/`（fx2 固件）、`share/udev/rules.d/`（udev 规则，Linux 主机参考用）

## 依赖

| 包 | 版本 | 用途 |
|---|---|---|
| libindi | 2.2.2.1 | INDI 框架（INDI::CCD 基类） |
| cfitsio | 4.6.4 | FITS 图像输出（静态库，链接需 libz） |
| libusb | 1.0.27 | USB bulk 传输 |
| zlib | 1.3.1.1 | 静态 libz.a，cfitsio 链接闭包 |

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 0.4-20221223123028 | built | 初始适配（patches 0001-0003 完成 libindi 2.x 迁移，0003 仅两处 BayerTP Property 回移） |

适配细节见 [0.4-20221223123028/notes.md](0.4-20221223123028/notes.md)。
