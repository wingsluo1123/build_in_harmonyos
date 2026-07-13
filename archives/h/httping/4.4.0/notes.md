# httping 4.4.0 适配笔记

## 概述
httping 是一个类似 ping 的 HTTP 请求延迟测试工具。
官方仓库: https://github.com/folkertvanheusden/HTTPing

## 构建系统
CMake (最小版本 3.12)

## 首次适配配置
- USE_SSL=OFF (openssl 依赖可选，本次未启用)
- USE_TUI=OFF (ncurses 依赖可选，本次未启用)
- USE_GETTEXT=OFF (gettext 国际化可选，本次未启用)
- USE_FFTW3=OFF (FFT 可视化可选，需 USE_TUI)

## 补丁
1. `0001-guard-gettext-calls-with-HAVE_INTL.patch`
   - 问题: CMakeLists.txt 中 USE_GETTEXT=OFF 时，main.c 仍无条件调用 bindtextdomain()/textdomain()
   - 修复: 用 #if INTL_FOUND 包裹 libintl.h 包含和 bindtextdomain/textdomain 调用
   - gen.h 已有正确的 #if INTL_FOUND 守卫，仅需修改 main.c

## 编译验证
- configure: cmake -DUSE_SSL=OFF -DUSE_TUI=OFF -DUSE_GETTEXT=OFF -DUSE_FFTW3=OFF
- build: make -j
- install: make install DESTDIR=$TEST_PREFIX
- --version: "HTTPing v4.4.0, (C) 2003-2023 folkert@vanheusden.com"

## 后续优化方向
- 启用 USE_SSL=ON (需 openssl 依赖)
- 启用 USE_TUI=ON + USE_FFTW3=ON (需 ncurses + fftw3 依赖)
- 启用 USE_GETTEXT=ON (需 gettext 依赖)
---

**编译结束**: 2026-07-13 21:51
**最终状态**: built
