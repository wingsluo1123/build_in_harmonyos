# gst-rtsp-server

GStreamer-based RTSP server library and rtspclientsink plugin.

## Description

gst-rtsp-server is a GStreamer library that allows building RTSP servers
to stream GStreamer pipelines via the RTSP protocol. It provides:

- `libgstrtspserver-1.0` — RTSP server core library
- `libgstrtspclientsink` — GStreamer plugin for RTSP client sink

## Build System

Meson (>= 1.4)

## Dependencies

- gstreamer 1.28.3
- gst-plugins-base 1.28.3 (provides gst-rtsp, gst-sdp, gst-rtp, gst-net, gst-app, gst-video)
- glib2 2.88.0

## Adaptation Notes

- No platform patches needed — meson builds natively on OHOS (aarch64)
- Static build used to avoid -fPIC issues with conan zlib static library
- CI worker's llvm-* tool names (AR, AS, NM, etc.) are resolved to GNU binutils in generate()

## License

LGPL-2.1-or-later
