# gst-plugins-good

GStreamer Good Plugins — a set of well-maintained plug-ins for GStreamer.

## Description

The gst-plugins-good module contains a set of plug-ins that are considered
to have good quality code, good feature set, and good licensing (LGPL).

These plugins include codecs for common formats (FLAC, JPEG, PNG, WAV, AVI,
Matroska, etc.), audio/video effects, and various utilities.

## Versions

- 1.28.3 — adapted for HarmonyOS PC (aarch64), meson build system

## Build System

Meson build system. Key configure options:
- Platform-incompatible plugins disabled (v4l2, oss, pulse, jack, etc.)
- Tests, examples, and documentation disabled
- ORC optimization disabled (not available on OHOS)

## Dependencies

- gstreamer/1.28.3
- gst-plugins-base/1.28.3
- glib/2.84.0.1
- cairo/1.18.4
- flac/1.4.3
- libjpeg-turbo/3.2.0
- libpng/1.6.58
