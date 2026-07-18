# baresip 4.9.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-18
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

```bash
cmake -B build \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_PREFIX_PATH=/storage/Users/currentUser/usr/local \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DSTATIC=OFF
cmake --build build -j1
cmake --install build
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 找不到 re 库 | re 未安装到系统默认路径 | 先构建并安装 re 4.9.0，设置 CMAKE_PREFIX_PATH |
| 2 | sockaddr_storage 重定义（netroam 模块） | linux/netlink.h 与 sys/socket.h 冲突 | 补丁 0001-netroam-ohos-compat.patch：在 OHOS 上跳过 netlink 编译 |
| 3 | libre.so 缺少 _mod_open/_mod_sym/_mod_close 符号 | CMake 不识别 OHOS 为 UNIX 系统 | 已在 re 4.9.0 中修复（补丁 0002-cmake-ohos-support.patch） |

## 源码修改

- 0001-netroam-ohos-compat.patch: netroam 模块在 OHOS 上跳过 netlink.c 编译

## 依赖版本

- re (libre) 4.9.0
- OpenSSL 3.5.6（系统预编译包，通过 re 间接依赖）

## 验证结果

```bash
# 验证库文件
ls -la /storage/Users/currentUser/usr/local/lib/libbaresip.*
# 输出: libbaresip.so (共享库)

# 验证可执行文件
ls -la /storage/Users/currentUser/usr/local/bin/baresip
# 输出: baresip (可执行文件)

# 验证模块
ls /storage/Users/currentUser/usr/local/lib/baresip/modules/
# 输出: 35 个模块 (account, g711, srtp, stun, turn, ice 等)
```

## 注意事项

- baresip 的实际构建系统是 CMake（不是 autotools），manifest.yaml 已修正
- 使用 `-DSTATIC=OFF` 构建共享库和动态模块
- re/4.9.0 尚未发布到 Conan 远程（ohpcd），需先发布 re 或使用本地安装的 re
---

**编译结束**: 2026-07-18 20:09
**最终状态**: built
