# Traceroute — OpenHarmony 编译档案

## 软件简介
Traceroute 是经典的网络诊断工具，用于跟踪数据包从本机到目的地址所经过的路由路径。支持 UDP、ICMP、TCP、DCCP 等多种探测模式。

## 功能概述
- UDP/ICMP/TCP/DCCP 多协议探测
- ASN 查询
- IPv4/IPv6 双栈支持
- 可配置超时、探测次数、端口

## OHOS 适配要点
- 修改 Make.rules 中 LIBDEPS 过滤 `-l%` 选项，避免 `-lm` 被当作文件依赖
- 将默认 CC 从 gcc 改为 clang（OHOS 平台仅有 clang）
- 使用 `env=yes` 标志继承环境变量

## 依赖关系
- 无外部依赖，仅需标准 C 库 (libc.so) 和数学库 (-lm)

## 参考资料
- [SourceForge 项目页](https://sourceforge.net/projects/traceroute/)
