# unudhcpd

## 简介

`unudhcpd` 是一个极简 DHCP 服务器：对任一发出 DHCP DISCOVER/REQUEST 的客户端，
固定下发同一个 IP，不做租约管理。适用于「同一时刻只会看到一个客户端、但客户端
MAC 会变」的场景（如 USB/网络 gadget、单机调试网络）。

- 上游项目：https://gitlab.postmarketos.org/postMarketOS/unudhcpd
- 上游版本：0.2.1（tag）
- 许可证：GPL-3.0-or-later
- 语言 / 构建：C / Meson
- Conan 包名：`unudhcpd/0.2.1-r2`

## OHOS 适配

| 项目 | 值 |
|------|-----|
| 目标平台 | OpenHarmony / HarmonyOS PC，aarch64（armv8） |
| 构建方式 | 原生构建（build = host = OHOS/aarch64），**非交叉编译** |
| 编译器 | clang 15.0.4（`/data/service/hnp/bin/clang`） |
| 构建系统 | Meson（`meson.build`） |
| 外部依赖 | 无（仅 libc：`inet_aton` / `getprotobyname` / `socket` / `ioctl`） |
| 补丁 | **零补丁**（上游源码未作任何修改） |

### 适配要点

1. **上游源码零修改**：上游代码全部使用 POSIX 接口（`socket` / `setsockopt` /
   `ioctl` / `getopt`），在 OHOS aarch64 上直接编译通过，未产生任何补丁。
2. **上游自带测试**：`tests/meson.build` 用 `test()` 注册了 3 个用例
   （`Test mac_to_str`、`Test dhcp_is_invalid_request`、`Test dhcp_get_request_type`，
   合计 24 条断言）。配方 `build()` 中以 `meson.test()` 集成为层1 上游官方测试。
3. **产物是可执行文件**：`bin/unudhcpd`，故 `package_type = "application"`；
   按 R38 在软件级目录提供 `commands.json`。本包不产出 `.so`，R26（系统同名库
   静态链接）约束不适用。
4. **上游版本号不一致（上游遗留）**：`meson.build` 的 `project(version: '0.1')`
   与发布 tag `0.2.1` 不一致，因此 `unudhcpd -v` 实测输出为 `unudhcpd 0.1`。
   为保持上游行为未作修改（若下游需要正确版本号，应推动上游修正）。
5. **运行期权限**：绑定网卡使用 `SO_BINDTODEVICE`，需 `CAP_NET_RAW`
   （通常需 root）。因此 test_package 只验证启动路径与参数解析，不进行真实收包。

## 使用

```bash
conan install --requires=unudhcpd/0.2.1-r2 -r=ohpcd -g VirtualRunEnv
source conanrun.sh
unudhcpd -i <网卡> [-s <服务端 IP>] [-p <端口>] [-c <下发 IP>]
unudhcpd -v          # 打印版本
```

## 构建与测试（本仓库）

```bash
cd archives/u/unudhcpd/0.2.1-r2
conan create . -pr:h=$HOME/.conan2/profiles/ohos -pr:b=$HOME/.conan2/profiles/ohos --build=missing
```

## 版本历史

| 版本 | 说明 |
|------|------|
| 0.2.1-r2 | 首次适配：上游 0.2.1 零补丁构建通过，层1 上游测试 3/3、层2 test_package 3/3 通过 |
