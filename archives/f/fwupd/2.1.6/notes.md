# fwupd 2.1.6 适配笔记

## 编译环境
- 构建系统: meson (最小化 standalone 配置)
- 编译日期: 2026-07-20
- 编译器: clang/clang++ (15.0.4, aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
export CC=/data/service/hnp/bin/clang
export CXX=/data/service/hnp/bin/clang++
export AR=/data/service/hnp/bin/ar
export RANLIB=/data/service/hnp/bin/ranlib
export TMPDIR=/storage/Users/currentUser
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:/storage/Users/currentUser/usr/local/libusb-package/lib/pkgconfig

meson setup build -Dbuild=standalone ...(最小化选项)
ninja -C build -j2
DESTDIR=<staging> meson install -C build --no-rebuild
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libusb_get_parent 静态声明冲突 | libusb 1.0.27 已有该函数声明，但 meson has_symbol 检测失败 | fu-usb-device.c: 添加 LIBUSB_API_VERSION 守卫 |
| 2 | fu_common_*_impl 链接未定义 | OHOS 系统名 "harmonyos" 不在 meson linux列表 | 3 个 meson.build 添加 harmonyos 平台支持 |
| 3 | sockaddr_storage 重定义 | OHOS sys/socket.h 和 linux/socket.h 都定义了该结构 | fu-udev-backend.c: 预定义 __MUSL__ 触发条件守卫 |

## 源码修改

- `libfwupdplugin/fu-usb-device.c` — 添加 LIBUSB_API_VERSION 守卫
- `libfwupdplugin/meson.build` — 添加 harmonyos 平台
- `src/meson.build` — 添加 harmonyos 平台
- `meson.build` — 添加 harmonyos 平台 (HAVE_UDEV)
- `src/fu-udev-backend.c` — 预定义 __MUSL__ 修复头文件冲突

## 依赖版本

- glib-2.0 2.88.0
- libcurl 8.12.0
- libxmlb 0.3.19
- libusb-1.0 1.0.27
- sqlite3 3.49.1
- zlib 1.3.1
- liblzma 5.8.2

## 验证结果

```bash
$ file staging/bin/fwupdtool
fwupdtool: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 注意事项

- OHOS 上 meson 的 host_machine.system() 返回 'harmonyos'（全小写）
- HMDFS 不支持符号链接，需用 rm -f && ln -s
- /tmp 只读，需要设置 TMPDIR
---

**编译结束**: 2026-07-20 14:31
**最终状态**: built
