# libmtp

Library for accessing MTP (Media Transfer Protocol) devices.

## Description

libmtp is a library implementation of the MTP (Media Transfer Protocol) for accessing portable media devices, such as Android phones, MP3 players, and digital cameras. It provides a simple API for reading and writing files on these devices.

## Features

- Full MTP implementation
- Support for a wide range of MTP devices
- Command-line tools for device management (17 个 mtp-* CLI 工具随库安装)
- Cross-platform support

## Compiled Versions

| Version | Status | Date |
|---------|--------|------|
| 1.1.21 | prepared | 2026-09-30 |

- 1.1.21 曾以旧格式条目于 2026-05-26 在真机整链构建成功（历史记录见
  `1.1.21/notes.md` 与 `1.1.21/hints/`）；现行 Conan 框架适配
  （conanfile.py / conandata.yml / test_package）处于 prepared 状态，
  待 OHOS 真机验证。

## Links

- Official Website: https://libmtp.sourceforge.net/
- Source Code: https://sourceforge.net/projects/libmtp/
