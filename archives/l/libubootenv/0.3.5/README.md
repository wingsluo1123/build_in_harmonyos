# libubootenv 0.3.5 (HarmonyOS PC)

U-Boot environment access library — 鸿蒙PC (OHOS aarch64) 适配

## 构建信息

- 版本: 0.3.5
- 构建系统: CMake
- 目标平台: OHOS aarch64 (clang 15, libc++ 17)
- 构建日期: 2026-10-18
- 许可证: LGPL-2.1-or-later

## 依赖

- zlib/1.3.1
- libyaml/0.2.5

## 适配要点

1. **CMake 4.x 兼容**: 源码 `cmake_minimum_required(VERSION 2.6)` 与 CMake 4.x 不兼容，build() 中 inline 提升至 3.5
2. **SONAME 显式设置**: CMake 在 OHOS 平台忽略 VERSION/SOVERSION，通过 `LINKER:-soname,libubootenv.so` 强制设置
3. **Conan 依赖注入**: OHOS 交叉编译下 `find_package(zlib/libyaml)` 失效，build() 阶段获取 cpp_info 路径后注入 CMake
4. **OHOS SDK bug**: `<mtd/ubi-user.h>` 存在 `__packed` 重定义错误，通过 `__OHOS__` 宏跳过并提供 UBI 桩结构

## 产物

| 文件 | 说明 |
|------|------|
| libubootenv.so | U-Boot 环境访问库 |
| fw_printenv | 打印环境变量 CLI |
| fw_setenv | 设置环境变量 CLI |

## 测试

- 上游无自动化测试
- test_package 含消费者 API 测试 + 鸿蒙特有 dlopen 运行时测试
- W3 本地 CI: 100% 通过

## 源码

https://github.com/sbabic/libubootenv
