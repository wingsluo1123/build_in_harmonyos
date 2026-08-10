# libiio 0.26 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-10
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://github.com/analogdevicesinc/libiio/archive/refs/tags/v0.26.tar.gz
2. 应用补丁: 0001-harmonyos-platform-support.patch
3. 安装 conan 依赖: libusb/1.0.27, libxml2/2.15.3
4. CMake 配置:
   ```
   cmake -DCMAKE_SYSTEM_NAME=HarmonyOS \
     -DWITH_USB_BACKEND=ON -DWITH_XML_BACKEND=ON \
     -DWITH_NETWORK_BACKEND=ON -DWITH_LOCAL_BACKEND=ON \
     -DWITH_IIOD=ON -DWITH_TESTS=ON \
     -DHAVE_DNS_SD=OFF -DWITH_AIO=OFF -DWITH_IIOD_USBD=OFF \
     -DWITH_SERIAL_BACKEND=OFF -DWITH_MAN=OFF -DWITH_DOC=OFF \
     -DINSTALL_UDEV_RULE=OFF
   ```
5. make -j4 && make install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake MATCHES "Linux" 不匹配 HarmonyOS | CMAKE_SYSTEM_NAME 为 "HarmonyOS" 而非 "Linux" | 补丁修改所有 MATCHES "Linux" 为 MATCHES "Linux\|HarmonyOS" |
| 2 | pthread 库未找到 | HarmonyOS 中 pthread 在 libc 中（类似 Android） | 补丁添加 HarmonyOS 到跳过 find_library 的条件，设置 PTHREAD_LIBRARIES 为空 |
| 3 | DNS-SD (avahi) 不可用 | HarmonyOS 没有 avahi D-Bus 服务 | HAVE_DNS_SD=OFF（不裁剪核心功能，仅禁用 ZeroConf 发现） |
| 4 | libaio 不可用 | HarmonyOS 没有 libaio | WITH_AIO=OFF（IIOD 子功能，非核心库功能） |
| 5 | functionfs.h 不可用 | HarmonyOS 没有 USB FunctionFS 内核接口 | WITH_IIOD_USBD=OFF（IIOD 子功能） |

## 源码修改

补丁文件: patches/0001-harmonyos-platform-support.patch
- 修改 CMakeLists.txt 中 5 处 MATCHES "Linux" 为 "Linux|HarmonyOS"
- 修改 pthread 查找逻辑，添加 HarmonyOS 到跳过列表（同 Android）
- 修改 IIOD pthread 检查，允许 HarmonyOS 跳过

## 依赖版本

- libusb/1.0.27 (conan)
- libxml2/2.15.3 (conan)

## 验证结果

```bash
# CMake 配置成功
# Features enabled: xml network ipv6 local local-mmap hwmon usb utils iiod iiod-serial man-utils
# Features disabled: zstd dns-sd avahi bonjour serial examples udev-rule c++-bindings iiod-aio iiod-usb ...
# make -j4: 100% built (libiio.so, iiod, iio_info, iio_genxml, iio_attr, iio_reg, iio_readdev, iio_writedev)
```

## 注意事项

- 前次适配禁用了所有后端（USB/XML/Network/Local/IIOD），本次适配启用了所有默认 ON 的后端
- DNS-SD/avahi、libaio、functionfs 是平台级基础设施缺失，非功能裁剪
- 运行时需要 LD_LIBRARY_PATH 包含 libiio.so 和 conan 依赖路径
---

**编译结束**: 2026-08-11 00:37
**最终状态**: built
