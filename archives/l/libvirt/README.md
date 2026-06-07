# libvirt

libvirt 是一个开源的虚拟化管理 API、守护进程和管理工具集。

## 描述

libvirt 提供了一个通用的虚拟化 API，支持多种虚拟化技术：
- KVM/QEMU
- LXC
- Xen
- VMware
- VirtualBox
- Bhyve
- Hyper-V

主要组件：
- libvirt API 库
- libvirtd 守护进程
- virsh 命令行工具
- virt-manager 图形工具

## 鸿蒙平台编译状态

**当前版本**: 11.3.0
**编译状态**: ❌ failed
**原因**: HMDFS 文件系统系统性限制

### HMDFS 限制详情

鸿蒙平台的 HMDFS 文件系统存在以下限制：
- ❌ **所有脚本文件无法直接执行**（Python、Perl、Shell 等）
- ❌ 即使设置了执行权限（chmod +x），脚本仍然无法执行
- ❌ 这是平台层面的安全机制，无法通过源码修改绕过

### 编译尝试记录

1. **第一次尝试**（2026-05-29）：
   - meson 配置阶段失败
   - Python 脚本执行权限问题

2. **第二次尝试**（2026-05-31）：
   - 修改 meson.build 使用 python3 解释器
   - 解决编译器和依赖路径问题
   - meson 配置成功
   - 编译阶段再次遇到 HMDFS 限制（keymap-gen 等脚本无法执行）

### 无法编译的原因

libvirt 的构建系统大量使用脚本：
- `scripts/rpcgen/main.py` - RPC 协议生成
- `subprojects/keycodemapdb/tools/keymap-gen` - 键盘映射表生成
- 其他构建过程中的自定义命令脚本

所有这些脚本都无法在 HMDFS 上执行，导致编译无法进行。

## 建议

### 短期方案
等待鸿蒙系统更新 HMDFS，支持脚本文件执行。

### 长期方案
考虑以下替代方案：
1. 使用鸿蒙官方提供的虚拟化方案（如有）
2. 使用 Docker/容器技术进行隔离（需要平台支持）
3. 等待社区提供鸿蒙适配补丁

### 不推荐的方案
- 预生成所有产物（违反 R6 铁律）
- 完全重写构建系统（工作量巨大）

## 依赖

libvirt 主要依赖：
- glib-2.0 ≥ 2.66.0
- gnutls ≥ 3.6.0
- libxml-2.0 ≥ 2.9.1
- libcurl ≥ 7.19.1（可选）

## 版本历史

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 11.3.0 | ❌ failed | 2026-05-31 | HMDFS 限制 |
| 10.0.0 | ❌ failed | 2026-05-31 | 同样问题 |
| 5.10.0 | ❌ failed | 2026-05-31 | 同样问题 |

## 技术总结

### 已解决的问题
- ✅ 编译器路径问题（使用真实路径而非符号链接）
- ✅ pkg-config 路径问题（设置 PKG_CONFIG_PATH）
- ✅ meson 配置成功

### 未解决的问题
- ❌ HMDFS 系统性脚本执行限制
- ❌ 无法完成编译构建

### 知识沉淀
- E082: HMDFS 文件系统系统性限制 - 所有脚本文件无法直接执行
- 编译器符号链接需要使用真实路径
- pkg-config 需要手动设置环境变量

## 许可证

LGPLv2+

## 参考资料

- [libvirt 官方网站](https://libvirt.org/)
- [libvirt 源码仓库](https://gitlab.com/libvirt/libvirt)
- [编译文档](https://libvirt.org/compiling.html)