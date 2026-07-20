# Falco Security Libraries

## 简介

falcosecurity-libs 提供 Falco 和 Sysdig 使用的核心用户态库，包括事件采集抽象库 libscap 与系统检查库 libsinsp。

## OHOS 适配

- 使用 CMake 构建共享库。
- 保留 nodriver、savefile 和 source plugin 用户态引擎。
- 禁用 Linux 内核模块、现代 BPF、示例和上游测试目标。
- 启用面向 musl libc 的兼容实现。

## 参考

- GitHub: https://github.com/falcosecurity/libs
