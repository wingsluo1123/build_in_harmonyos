# tinyhttpd

## 简介

tinyhttpd 是 J. David Blackstone 在 1999 年编写的一个不到 500 行的超轻量型 HTTP Server，用于学习网络编程和服务器原理。全部代码仅包含一个 `httpd.c`（约 500 行）和一个 `simpleclient.c`，附带一个简单的 Makefile。

主要功能：
- 支持 HTTP GET / POST 请求
- 支持 CGI 脚本执行（通过 fork + pipe + dup2）
- 多线程处理客户端连接（pthreads）
- 静态文件服务（从 htdocs/ 目录）

## OHOS 适配

- **纯 Makefile 项目**：tinyhttpd 不使用 autotools，无 configure 脚本，直接使用 make 构建
- **Makefile 硬编码 gcc**：原 Makefile 中编译命令硬编码 `gcc`，在 conanfile.py 中通过 `replace_in_file` 将 `gcc` 替换为 `$(CC)` 并添加 `$(CFLAGS)`，支持交叉编译
- **pthreads 依赖**：使用 pthreads 多线程，OHOS 平台原生支持
- **端口固定 4000**：httpd 硬编码监听端口 4000，无法通过命令行参数修改

## 依赖

- pthreads（系统库，OHOS 原生支持）

## 功能验证

```bash
$ httpd &
httpd running on port 4000

$ readelf -d httpd | grep NEEDED
 Shared library: [libc.so]
# 仅依赖 libc（pthreads 在 musl 中内联）

$ readelf -h httpd | grep Type
 Type: DYN (Position-Independent Executable file)
# PIE + BIND_NOW (RELRO) 安全特性
```

## 参考

- 源码: https://github.com/EZLippi/Tinyhttpd
- 原作者: J. David Blackstone (1999)
