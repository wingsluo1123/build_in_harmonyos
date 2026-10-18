# uim

> 多语言输入法库（Multilingual Input Method Library），支持多种输入法引擎和协议

## 简介

uim 是一个用于 Unix/Linux 系统的多语言输入法框架库，支持 SCHEME 脚本扩展、多种输入法协议（XIM、GTK+、Qt 等）。uim 1.9.6 是该项目的最新稳定版本。

## OHOS 适配要点

- 禁用所有 GUI 后端（GTK2/3、Qt3/4/5/6、M17N、Anthy、Canna、WNN 等），仅保留核心库和 sigscheme Scheme 解释器
- `getpeereid()` 在 OHOS 上不可用，通过 stub 跳过
- `replace/os_dep.h` 的 `#define getpeereid uim_internal_getpeereid` 宏会导致链接期未定义符号，通过 `-Duim_internal_getpeereid=getpeereid` 编译器标志修复
- HMDFS 不允许 execve() 脚本，所有 autotools helper scripts（configure、install-sh、config.guess、config.sub）的 shebang 需指向真实 ELF bash 路径 `/data/service/hnp/bash.org/bash_5.3/bin/bash`
- 配置 `--build=aarch64-linux-gnu --host=aarch64-linux-gnu` 绕过 OHOS 检测

## 依赖

无编译期外部依赖。

## 功能验证

```bash
# 检查库文件存在
ls /path/to/install/lib/libuim.a
ls /path/to/install/lib/libuim-scm.a
ls /path/to/install/lib/libuim-custom.a
ls /path/to/install/lib/libgcroots.a

# 检查头文件
ls /path/to/install/include/uim/uim.h
```

## 参考

- [uim GitHub](https://github.com/uim/uim)
- [uim 官网](https://uim.im/)
