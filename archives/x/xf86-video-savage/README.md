# xf86-video-savage

X.Org video driver for S3 Savage graphics chips.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 2.4.1 | published | 2026-08-09 |

## Description

The xf86-video-savage driver provides support for S3 Savage series graphics
accelerators in the X.Org X server. On HarmonyOS, the driver is built with
XAA and DRI disabled (--disable-xaa --disable-dri) as the OHOS xorg-server
does not support these features.

## Dependencies

- xorgproto (Conan)
- pixman (Conan)
- xorg-server (system, via cmd-pkgs)
- libpciaccess (system, via cmd-pkgs)
