# Distro KaOS

KaOS carries 14.4.2 with

| Patch | Commit |
| :---- | :----: |
| A sed line in [`PKGBUILD`](https://github.com/KaOSx/main/blob/master/sox/PKGBUILD) to export `lsx_error` and `lsx_flush` | 508209d |
| [A patch to `configure`](https://github.com/KaOSx/main/blob/master/sox/sox-ffmpeg0.11.patch) for ffmpeg0.11 | - |

The patch, for `sox-14.4.0`,
seems not to be relevant any more as `libavformat` is not used any more.
