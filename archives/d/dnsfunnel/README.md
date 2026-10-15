# dnsfunnel

## 简介

dnsfunnel 是 skarnet.org 的本地 DNS 转发漏斗：客户端把查询发到本地桩地址，
守护进程按缓存列表把查询转发给一个或多个上游 DNS 解析器，再把响应送回客户端；
需要改写时它会对查询/响应做轻量处理。

## 功能概述

- `dnsfunneld`：转发守护进程，绑定 UDP 端口（默认 `127.0.0.1:53`），
  从 root 目录下的 `caches` 文件读取上游地址列表（纯 IP，无端口项）。
- `dnsfunnel-translate`：读取 resolv.conf，写出 `caches` 文件；
  默认把 `127.0.0.1` 视为本地桩地址并剔除（可用 `-x` 指定别的忽略地址）。

## OHOS 适配

- 版本 0.0.3.2 为**纯可执行包**（`package_type = application`），
  产物 `bin/dnsfunneld`、`bin/dnsfunnel-translate` 与 `include/dnsfunnel/config.h`，
  无供下游链接的库，软件级提供 `commands.json`。
- 上游是 skarnet 家族**自带的 POSIX configure + GNU make**（不是 GNU autoconf），
  配方直接调用 `./configure && make && make install`，不使用 Conan 的 Autotools 工具链。
- 依赖 ohpcd 制品仓已发布的 `skalibs/2.15.1.0` 与 `s6-dns/2.4.1.0`，
  通过依赖包目录传入 `--with-include` / `--with-lib` / `--with-sysdeps`。
- 构建要点、验证读数与已知限制见 `0.0.3.2/notes.md` 与版本级 `manifest.yaml`。

## 依赖关系

- 编译依赖：`skalibs/2.15.1.0`、`s6-dns/2.4.1.0`（静态链接进两个可执行文件）。
- 无运行时外部依赖：上游解析器地址由部署方在 `caches` 中给出。

## 测试

- 上游无注册测试：`package/targets.mak` 的 `TEST_BINS` 为空、`src/tests/` 不存在，
  `make check` 循环 0 项（N_static = 0）。
- 消费者测试 5 条断言（`0.0.3.2/test_package/test.sh`）：CLI usage 契约、
  resolv.conf 解析、缺输入错误码、守护进程非特权端口监听就绪、端到端真实 DNS 转发。

## 参考资料

- 上游项目页：https://skarnet.org/software/dnsfunnel/
- 上游代码镜像：https://github.com/skarnet/dnsfunnel
- 上游文档：`doc/dnsfunneld.html`、`doc/dnsfunnel-translate.html`（随源码分发）
