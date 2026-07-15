# lua-resty-dns 0.23 — 适配笔记

## 软件概述

lua-resty-dns 是 OpenResty 生态中的纯 Lua DNS 解析库，基于 ngx_lua 的 cosocket API，
提供非阻塞 DNS 查询功能。

## 源码信息

- 上游仓库: https://github.com/openresty/lua-resty-dns
- 版本: v0.23 (tag)
- 源码格式: tar.gz
- SHA256: ecc80b91bfb4f795b8a80acfa69e1778288ef60649ddd87f30a9c4a57ac5da79

## 适配说明

### 软件类型

纯 Lua 库，无 C/C++ 编译步骤。构建过程仅涉及 `make install` 复制 .lua 文件。

### 构建系统

使用简单 Makefile，核心目标:
- `all`: 空操作（无需编译）
- `install`: 复制 `lib/resty/dns/*.lua` 到 `$(DESTDIR)/$(LUA_LIB_DIR)/resty/dns/`

### Conan 配方设计

- `settings`: 仅 "os" 和 "arch"（无编译器设置，因无 C/C++ 编译）
- `build()`: 空操作（纯 Lua 库无需编译）
- `package()`: 从源码 `lib/` 复制 `*.lua` 到包的 `lib/` 目录
- `package_info()`: `cpp_info.libs = []`（无 C++ 库），`libdirs = ["lib"]`

### 测试方案

上游测试依赖 test-nginx + Perl + Nginx + LuaJIT 运行环境，OHOS 上无法运行。
替代方案: 使用 Python 脚本验证 resolver.lua 文件的打包正确性和 API 符号完整性。

验证内容:
1. resolver.lua 文件存在于预期路径
2. 文件包含 DNS 解析器核心 API: TYPE_A, TYPE_AAAA, TYPE_CNAME 等
3. 文件包含关键方法: compress_ipv6_addr, expand_ipv6_addr, arpa_str, reverse_query
4. 文件使用 ngx.socket.udp 进行非阻塞 UDP DNS 查询

### 依赖

运行时依赖（非 Conan 依赖）:
- ngx_lua (OpenResty nginx + lua 模块)
- LuaJIT bit 库
- 不需要 C/C++ 编译依赖
