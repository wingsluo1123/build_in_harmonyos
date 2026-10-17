# rmcast

Reliable Multicast Library (RML) — LAND/UFRJ 的 IP 组播可靠传输 C 库（QPL-1.0）。

- 适配版本: 2.0.0（上游最终版本）
- 上游: https://www.land.ufrj.br/tools/rmcast/rmcast.html （站点多次 503，无公开 git 镜像；
  归档仅可经官方站点或 web.archive.org 快照获取）
- 产物: librmcast（.a/.so）+ rmcast.h + 演示工具 rmchat / mcastproxy
- 构建: autotools（上游自带 2009 年代 configure，需 autoreconf 再生或 --host 三元组）
- 依赖: 无第三方依赖（libc + POSIX sockets）
- 运行时: 需要可用 IP Multicast 网络；test_package 仅覆盖无网络可判定的 API（版本串、选项回环）

版本目录: `2.0.0/`（详见其 manifest.yaml 与 notes.md）
