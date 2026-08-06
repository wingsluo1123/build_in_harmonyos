# jack 1.9.22 适配笔记

## 编译环境
- 构建系统: waf (custom Python-based)
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. `python3 ohc-run.py init-build jack 1.9.22 --url=https://github.com/jackaudio/jack2/archive/refs/tags/v1.9.22.tar.gz`
2. 应用历史 4 个补丁 + 新增 JackPosixThread.cpp 补丁（共 5 个补丁）
3. 源码修改：添加 `#ifndef __OHOS__` 守卫到 pthread_cancel/pthread_setcanceltype 相关调用（5 处修改）
4. 修改 waflib/Context.py：替换 `imp.new_module` 为 `types.ModuleType`（Python 3.12+兼容）
5. 运行 `python3 waf configure --platform=linux --samplerate=no --prefix=$DEFAULT_PREFIX`
   - 需要 `--platform=linux` 因为 waf 不识别 OHOS 平台
   - 需要 `--samplerate=no` 因为 OHOS 无 libsamplerate
   - D-Bus 是 store_true 选项，不传即禁用（不能用 --dbus=no）
   - 需要设置 CXX/CC 环境变量指向完整路径
6. 运行 `python3 waf build`
7. 运行 `python3 waf install --destdir=$TEST_PREFIX`（staging）
8. 运行 `python3 waf install`（本地安装）
9. Conan 配方生成: `ohc-run.py conan-init jack 1.9.22`
10. Conan 验证: `ohc-run.py conan-verify jack 1.9.22`
11. `ohc-run.py finish jack 1.9.22 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pthread_cancel undeclared | OpenHarmony musl libc 缺少 pthread 取消函数 | #ifndef __OHOS__ 条件编译守卫，替代为 pthread_kill(SIGTERM) |
| 2 | imp.new_module 不存在 | Python 3.12+ 已移除 imp 模块 | 替换为 types.ModuleType |
| 3 | PTHREAD_CANCEL_ASYNCHRONOUS 未定义 | OHOS 无此常量 | JackPosixThread.h 添加 __OHOS__ 守卫，默认值改为 0 |
| 4 | JackPosixThread.cpp pthread_cancel | 历史补丁遗漏此文件 | 新增 0003 补丁，Guard + pthread_kill 替代 |
| 5 | waf 不识别 OHOS 平台 | waf detect_platform 不含 OHOS | --platform=linux 伪装 |
| 6 | waf 找不到 clang++ | PATH 中有但 waf subprocess 不继承 | 设置 CXX/CC 环境变量完整路径 |
| 7 | --dbus=no 报错 | D-Bus 是 store_true flag | 不传 --dbus 即可禁用 |

## 源码修改（5 个补丁）

- 0001-common-JackControlAPI.cpp.patch: pthread_setcanceltype 守卫
- 0002-linux-alsa-hammerfall.c.patch: ALSA驱动 pthread_cancel 守卫
- 0003-posix-JackPosixThread.cpp.patch: pthread_cancel/pthread_setcanceltype 守卫 + pthread_kill(SIGTERM) 替代（新增）
- 0004-posix-JackPosixThread.h.patch: PTHREAD_CANCEL_ASYNCHRONOUS 守卫
- 0005-waflib-Context.py.patch: imp.new_module → types.ModuleType

## 依赖版本
- libpthread (system, musl libc)
- libasound (system ALSA, ALSA driver disabled in configure)
- libsamplerate: 禁用 (--samplerate=no)
- D-Bus: 禁用 (不传 --dbus flag)

## 验证结果
- jackd --version: jackdmp version 1.9.22
- libjack.so, libjackserver.so 已生成
- Conan 配方已生成并验证

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (waf 构建系统) |
| conandata.yml | 源码 + 5 个补丁声明 |
| test_package/ | Conan L1 测试 (jack_client_name_size) |
| commands.json | 命令行工具声明 (jackd) |
| patches/ (5 files) | 平台适配补丁 |
---

**编译结束**: 2026-08-06 22:03
**最终状态**: built
