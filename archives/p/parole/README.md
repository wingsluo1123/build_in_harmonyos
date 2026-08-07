# parole

Parole is a modern media player based on GStreamer for the XFCE desktop environment.

## Versions

| Version | Status | Build System |
|---------|--------|-------------|
| 4.20.0 | built | meson |

## Dependencies

- glib >= 2.38.0
- gtk+-3.0 >= 3.22.0
- dbus-1 >= 0.60
- dbus-glib-1 >= 0.70
- gstreamer-1.0 >= 1.0.0 (base, video, audio, pbutils, tag)
- libxfce4ui-2 >= 4.16.0
- libxfce4util-1.0 >= 4.16.0
- libxfconf-0 >= 4.16.0

## Optional Dependencies

- taglib_c (taglib support, disabled)
- libnotify (notify plugin, disabled)
- X11 (enabled)
- Wayland (disabled)
