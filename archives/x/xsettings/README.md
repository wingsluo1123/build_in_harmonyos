# xsettings 0.10 - HarmonyOS PC 适配

## 概述

xsettings 0.10 即 matchbox **libxsettings-client 0.10**——Xsettings 协议客户端 C 库，供 X11 程序读取窗口管理器设置（Net/ThemeName、Xft/DPI 等）。

- 上游：https://downloads.yoctoproject.org/releases/matchbox/optional-dependencies/Xsettings-client-0.10.tar.gz
- 适配路径：`archives/x/xsettings/0.10/`
- 构建系统：autotools → 配方内 CMake 重写（保留库名 `libXsettings-client` 与公共头文件）
- 依赖：libx11/1.8.13.1（transitive）+ xorgproto/2025.1（头文件）
- 产物：`libXsettings-client.so`（SONAME `libXsettings-client.so.0`）+ `xsettings-client.h` / `xsettings-common.h`
- 上游测试：无自动化测试套件（Makefile.am 无 check/TESTS 目标）；test_package 以 4 条消费者用例补足，含鸿蒙特有 dlopen/dlsym 非断言用例

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.10 | built | conan create + conan-verify + W3 本地 CI 全绿（详见 `0.10/reports/`） |

## 命令

本包为纯库（package_type=library），无可执行命令；commands.json 按仓库 L0k 门禁要求声明（type=tool，binary=false）。
