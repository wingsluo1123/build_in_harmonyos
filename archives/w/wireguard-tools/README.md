# wireguard-tools

WireGuard 是一种极快、现代且安全的 VPN 隧道技术，使用最先进的加密技术。

## 软件信息

- **官方网站**: https://www.wireguard.com/
- **源码仓库**: https://git.zx2c4.com/wireguard-tools/
- **编译状态**: built (已在鸿蒙平台成功编译)

## 编译版本

| 版本 | 状态 | 补丁数 | 编译日期 |
|------|------|--------|----------|
| 1.0.20260223 | built | 0 | 2026-07-15 |
| 1.0.20250521 | built | 1 | 2026-05-19 |

## 鸿蒙平台适配

wireguard-tools 在鸿蒙平台需要以下适配：

1. **sockaddr_storage 重复定义修复**: 鸿蒙SDK中 `sys/socket.h` 和 `linux/socket.h` 都定义了该结构体，通过生成 `ohos_compat.h` 定义 `_UAPI_LINUX_SOCKET_H` 宏跳过 `linux/socket.h` 的重复定义
2. **uapi/harmonyos 目录不存在**: `uname -s` 返回 `harmonyos` 而非 `linux`，Makefile 检测 `uapi/$(PLATFORM)/` 找不到目录。创建 `uapi/harmonyos -> uapi/linux` 符号链接或传 `PLATFORM=linux`
3. **WGALLOWEDIP_A_FLAGS 未定义**: 鸿蒙 sysroot 无 `linux/wireguard.h`，需通过 `uapi/linux` include path 提供项目自带的 `wireguard.h`

## 使用说明

wireguard-tools 提供两个核心工具：

- **wg**: WireGuard 配置工具（用于手动配置 WireGuard 接口）
- **wg-quick**: 快速启动工具（基于 bash 脚本，自动从配置文件启动 WireGuard）

注意：wg-quick 需要 bash 环境，鸿蒙系统需先安装 bash。

## 依赖

- **无外部库依赖**：wireguard-tools 仅依赖标准 C 库
- **可选依赖**：
  - bash（用于 wg-quick）
  - WireGuard 内核模块（需要内核支持）

## 注意事项

- wireguard-tools 仅提供用户空间工具，实际 VPN 功能需要内核模块支持
- 鸿蒙平台可能缺少 WireGuard 内核模块，工具可编译但实际功能依赖内核支持
- wg 工具已编译并验证可用（通过 `wg --help` 和 `wg genkey` 测试）
