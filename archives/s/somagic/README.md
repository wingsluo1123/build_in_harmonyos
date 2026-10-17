# somagic 1.1 — 鸿蒙 PC conan 制品

`somagic`（上游项目 `easycap-somagic-linux`）是 Somagic EasyCAP DC60 /
EasyCAP002 USB 视频采集棒（USB ID `1c88:0007`）的用户态驱动套件。
1.1 发布 4 个命令行程序：

| 程序 | 作用 |
|------|------|
| `somagic-init` | 上传芯片固件并让设备以新 product ID 重新枚举（libusb-1.0 + libgcrypt） |
| `somagic-capture` | 初始化采集寄存器并输出原始 UYVY 视频流（libusb-1.0） |
| `somagic-audio-capture` | beta 纯音频采集路径（libusb-1.0） |
| `somagic-both` | beta 初始化 + 采集合并路径（libusb-1.0） |

## 出包（鸿蒙 PC CI）

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
```

源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验。

## 依赖

- `libusb/1.0.27`
- `libgcrypt/1.11.0`（传递依赖 `libgpg-error/1.55`）

## OHOS 适配要点

- 上游为纯 Makefile（无 configure/CMake），配方以 `make` 命令行变量注入
  Conan 工具链（`CC`/`CFLAGS`/`LFLAGS`），无需补丁。
- 源码用 `#include <libusb-1.0/libusb.h>`，因此把 libusb 包的 `include/`
  父目录一并加入 `-I`。
- `execinfo.h` 仅在上游 `DEBUG` 宏下引用（默认未定义），不需要 libexecinfo。
- 不调用上游 `install`（写死 `/usr/local` 且只装两个程序）；`package()` 内
  拷贝全部四个可执行文件 + 手册页 + copyright。
- OHOS 要求 ELF 签名，`package()` 对四个可执行文件做 `binary-sign-tool` 自签。

## 已知限制

- 本套件面向真实 USB 采集硬件；无设备环境只能验证 CLI 表面与两条确定性的
  设备无关错误路径（libgcrypt 固件校验、libusb-1.0 设备枚举）。
- `somagic-audio-capture` 是仅设备可用的 beta 程序：`main()` 无 CLI，
  直接 `assert(dev)`，无硬件时 abort。

## 参考资料

- 上游项目归档: https://code.google.com/archive/p/easycap-somagic-linux/
- 源码归档: https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/easycap-somagic-linux/somagic-easycap_1.1.tar.gz
