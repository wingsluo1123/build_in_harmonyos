# Distro MSYS2

MSYS2 mingw carries 14.4.2 with one patch

## Links

* [MSYS2 mingw package](https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-sox)

## Patches

The patch ensures we don't try to rewind pipes when using the UCRT libc.

Applied as issue #169
