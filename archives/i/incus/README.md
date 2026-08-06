# incus

Incus 是 LXD 项目的社区分支，提供强大的系统容器和虚拟机管理功能。

## 描述
Incus 是从 Canonical LXD 项目 fork 出来的社区版本，专注于开放治理和社区驱动。支持系统容器（LXC）和虚拟机管理，提供 REST API 和命令行工具。

## 已编译版本
- 7.1.0 (2026-08-06)

## 依赖
- Go 1.26.5 (Harmonybrew)
- libacl 2.4.0 (Harmonybrew)
- libcap 2.78 (Harmonybrew)
- gettext 1.0 (Harmonybrew)
- binutils 2.47 (Harmonybrew, GNU ld)

## 特性
- 系统容器（LXC）管理
- 虚拟机管理（QEMU）
- REST API 支持
- 远程镜像仓库
- 存储池管理
- 网络配置
- 项目隔离

## 使用方法
```bash
# 列出容器
incus list

# 启动容器
incus launch ubuntu:22.04 my-container

# 进入容器
incus exec my-container -- bash

# 管理虚拟机
incus launch ubuntu:22.04 my-vm --vm
```

## 注意事项
- CGO_ENABLED=0 编译客户端工具（incus, incus-migrate, incus-simplestreams, incus-user, incus-agent）
- CGO_ENABLED=1 编译需要 C 依赖的工具（fuidshift, incus-benchmark, lxd-to-incus）
- incusd 服务端需要 cowsql + liblxc + libudev，OHOS 上不可用，待转专家分析
- lxc-to-incus 需要 liblxc 开发文件，Harmonybrew lxc 包仅含 CLI 二进制
- OHOS 关键修复：
  - `-D__MUSL__` 解决 sockaddr_storage 重定义冲突
  - 沙箱路径 `/data/storage/el2/base/files/tmp` 解决 Go linker mmap 问题
  - GNU ld (binutils) 解决 lld libxml2 依赖问题
  - `-Wno-macro-redefined` 解决 ACL_UNDEFINED_ID 宏重定义
