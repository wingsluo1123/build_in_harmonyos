# Distro NetBSD

NetBSD carries 14.4.2 with three patches.

## Patches

All three have been applied to `sox_ng`.

| Patch | Issue |
| :---- | :---: |
| [remove-the-error-line-and-live-without-file-type-det](http://cgit.openembedded.org/meta-openembedded/tree/meta-multimedia/recipes-multimedia/sox/sox/0001-remove-the-error-line-and-live-without-file-type-det.patch?h=master) | #67 |
| [Update-exported-symbol-list](http://cgit.openembedded.org/meta-openembedded/tree/meta-multimedia/recipes-multimedia/sox/sox/0001-Update-exported-symbol-list.patch?h=master) | #35 |
| [tests-Include-math.h-for-fabs-definition](http://cgit.openembedded.org/meta-openembedded/tree/meta-multimedia/recipes-multimedia/sox/sox/0001-tests-Include-math.h-for-fabs-definition.patch?h=master) | #50 |

## Build dependencies

### For a release tarball

to compile for full functionality

    pkg_add libao libao-oss ...

amd ensure that `alsa-lib` is not installed or `configure --without-alsa`

## Building

On NetBSD, `./configure --without-oss --without-sunaudio`
to avoid compilation errors "ld: _oss_ioctl undefined"
and "'audio_info_t' has no member named 'output_muted'"

I also had to

    ./configure CFLAGS="-I/usr/pkg/include -O2" LDFLAGS=-L/usr/pkg/lib

before it could find most of the libraries

## Runtime dependencies

    libao-oss ffmpeg2-8
