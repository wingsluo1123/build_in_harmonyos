# cdparanoia 10.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4
- 状态: published (conan recipe verified)

## 源码
- URL: https://downloads.xiph.org/releases/cdparanoia/cdparanoia-III-10.2.src.tgz
- SHA256: 005db45ef4ee017f5c32ec124f913a0546e77014266c6a1c50df902a55fe64df

## 适配修改

### 1. config.guess/config.sub — HarmonyOS 平台检测
- configure.guess: 添加 `*:HarmonyOS:*:*` case 分支，输出 `aarch64-unknown-linux-ohos`
- configure.sub: 添加 `linux-ohos` 到 maybe_os 列表、OS 列表、独立 case

### 2. configure — umask 修复
- config.status 创建临时目录时使用 `umask 077`，在 OHOS 上导致 Permission denied
- 修改为 `umask 022`，目录权限 0755 可正常写入

### 3. interface/scan_devices.c — cuserid() 替换
- `cuserid()` 在 OHOS musl libc 上不可用
- 使用 `#ifdef __OHOS__` 守卫，用 `getpwuid(getuid())` 替代
- 实质逻辑：从 /etc/passwd 获取用户名，非空壳 stub

### 4. utils.h — u_int32_t/u_int16_t 类型定义
- BSD 风格 `u_int32_t`/`u_int16_t` 在 musl libc 上未定义
- 添加 `<stdint.h>` 和 typedef 映射到 `uint32_t`/`uint16_t`

### 5. Makefile.in — DESTDIR 支持
- 原 install 目标不支持 DESTDIR，conan 打包无法正确 staging
- 添加 `$(DESTDIR)` 前缀到所有安装路径
- 将 `ln -fs` 改为 `rm -f && ln -s` 避免 HMDFS 软链接覆盖问题
- 添加条件安装 .so 文件（静态构建时不安装）

## 交付物
- libcdda_interface.a / libcdda_interface.so — CD-ROM 接口库
- libcdda_paranoia.a / libcdda_paranoia.so — 纠错库
- cdparanoia — 命令行工具
- cdda_interface.h, cdda_paranoia.h, utils.h — 头文件

## Conan 配方
- 构建类型: library (含 CLI 工具)
- 依赖: 无外部依赖
- 系统库: rt, m
- commands.json: 声明 cdparanoia 命令行工具

## 结束
COMPLETED
