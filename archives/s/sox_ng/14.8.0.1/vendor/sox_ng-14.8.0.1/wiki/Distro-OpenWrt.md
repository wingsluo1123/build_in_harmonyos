# Distro OpenWrt

OpenWrt carries 14.4.2 with three patches.

All are included in `sox_ng-14.5.0`.

| Patch | Issue/Commit |
| :---- | :---: |
| [cross-compile](https://github.com/openwrt/packages/blob/master/sound/sox/patches/001-cross_compile.patch) | c4e760c |
| [fix_uclibc_build_issue](https://github.com/openwrt/packages/blob/master/sound/sox/patches/010-fix_uclibc_build_issue.patch) | #76 |
| [reproducible-builds](https://github.com/openwrt/packages/blob/master/sound/sox/patches/020-reproducible-builds.patch) | #171 |
