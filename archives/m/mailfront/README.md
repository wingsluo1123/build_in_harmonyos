# mailfront

mailfront 是模块化邮件协议前端，提供 SMTP、QMTP、QMQP、POP3 和 IMAP 认证入口，并通过运行时模块组合协议、后端和策略插件。

## 功能概述

- 提供 SMTP、QMTP 与 QMQP 前端和 echo、qmail、queuedir 后端。
- 支持 CVM 认证、Lua、规则、RBL、反病毒、垃圾邮件过滤和 UCSPI STARTTLS 插件。
- 提供 POP3、IMAP 认证入口以及可扩展的动态模块接口。

## HarmonyOS 适配

- 使用 HarmonyOS clang 和 Conan Makefile 配置构建 10 个程序与 19 个动态模块。
- 使用制品仓中已发布的 `bglibs/2.04`、`cvm/0.97` 与 `lua/5.1.5`。
- 从主程序路径解析同包模块目录，避免固化构建机或 Conan 缓存路径。
- 对最终程序和模块原位签名，并检查 `.codesign`、`RPATH/RUNPATH` 与构建路径泄漏。
- 在 UCSPI STARTTLS 原地升级成功后、读取下一条命令前，原子撤销握手前的邮件事务、EHLO 身份、认证副本与 relay 授权状态。
- 真机消费者测试运行安装后的主程序和动态模块，完成真实 TLS 握手、CVM 认证、授权、队列后端及异常流水线验证。

## 依赖关系

- 运行与编译依赖：bglibs、CVM、Lua。
- 测试依赖：cdb、OpenSSL。
- 构建系统：上游自定义 Makefile；编译器为 HarmonyOS clang。

## 参考资料

- 上游主页：https://untroubled.org/mailfront/
- 上游源码：https://untroubled.org/mailfront/archive/mailfront-2.12.tar.gz
