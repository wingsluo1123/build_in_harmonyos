# Jsonrpc-GLib

## 简介

Jsonrpc-GLib 是一个基于 GLib 的 JSON-RPC 协议实现库，提供客户端和服务器端对象、输入/输出流以及消息序列化功能。

## 官方资源

- **源码仓库**: https://gitlab.gnome.org/GNOME/jsonrpc-glib
- **源码下载**: https://download.gnome.org/sources/jsonrpc-glib/

## 编译状态

### 3.44.0 (2026-08-06)

**状态**: ✅ Conan 适配成功

**产物**:
- 静态库: libjsonrpc-glib-1.0.a
- 头文件: 9个头文件
- pkg-config: jsonrpc-glib-1.0.pc

**依赖**:
- glib2/2.88.0
- json-glib/1.6.6

## 使用方法

### Conan 引用

```python
self.requires("jsonrpc-glib/3.44.0")
```

### 编译链接

```bash
pkg-config --cflags jsonrpc-glib-1.0
pkg-config --libs jsonrpc-glib-1.0
```
