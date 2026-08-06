# gst-plugins-bad

GStreamer Bad Plug-ins - multimedia framework plugins.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 1.28.3 | built | 2026-08-06 |

## Description

GStreamer is a library for constructing graphs of media-handling components.
The "bad" plug-ins are a set of plug-ins that aren't tested well enough,
or have code issues. This package builds from the GStreamer monorepo,
which also includes gstreamer core and gst-plugins-base.

## Build Notes

GStreamer 1.28.x uses a monorepo structure. This recipe builds from the
monorepo root, producing gstreamer, gst-plugins-base, and gst-plugins-bad
artifacts together.
