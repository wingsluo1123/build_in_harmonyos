# SWUpdate (swupdate)

[SWUpdate](https://github.com/sbabic/swupdate) — 嵌入式 Linux 设备软件更新代理
（本仓适配 OpenHarmony / HarmonyOS PC aarch64）。

## 本仓适配内容

- **构建系统 Kbuild**：上游用 kernel 风格 `make` + Kconfig，没有 configure/cmake。
  依赖不做自动探测（`Makefile.deps` 只给 `HAVE_*` 默认 `y`，真正判据是 Kconfig 的
  `option env=`），配方显式声明每个 `HAVE_*` 并注入 conan 依赖的头/库路径。
- **功能面**：签名镜像校验（`SIGNED_IMAGES`/`SIGALG_RAWRSA`）、镜像加密、
  HTTP 下载、内置 web 服务器（mongoose + openssl）、hawkBit 客户端
  （`SURICATTA`）、Lua 扩展与脚本处理器、libarchive 归档处理器、裸设备处理器。
- **MTD/UBI 面**：`libmtd/2.3.1-3` + `libubi/2.3.1-3` 提供 `mtd-user.h`/
  `mtd-abi.h` 与静态库，`CONFIG_MTD`/`CONFIG_CFI`/`CONFIG_UBIVOL` 已打开。
- **关闭的可选面**（OHOS 制品仓无对应包）：libubootenv（U-Boot env /
  swupdate vars）、zeromq（remote handler）、librsync+zck（delta）、
  libwebsockets+uriparser（swuforwarder）、zstd/xz/lz4、wolfssl/mbedtls、
  gpgme、btrfs。
- **OHOS 特定**：libubootenv 硬依赖经补丁收敛为可关闭面；`pthread_cancel`
  在 OHOS 缺失，SIGTERM 收尾改为 `exit()`；ELF 需用 `binary-sign-tool` 重签
  （lld 链接期自签对本工程不可用）；`LD`/`HOSTCC` 必须显式指定（上游默认
  `cc`，OHOS 无该别名）。

## 包内容

| 路径 | 说明 |
|---|---|
| `bin/swupdate` | 更新代理本体 |
| `bin/swupdate-client` | 通过 IPC 触发一次更新的客户端 |
| `bin/swupdate-progress` | 读取并显示更新进度的客户端 |
| `bin/swupdate-ipc` | IPC 消息工具 |
| `lib/libswupdate.so.0.1` | 供应用集成的 IPC 库 |
| `lib/lua_swupdate.so.0.1` | Lua 绑定 |
| `include/{network_ipc,swupdate_status,progress_ipc}.h` | IPC 头文件 |

## 用法示例

```sh
# 版本指纹
swupdate --version

# 校验一个 .swu 镜像（不安装）
swupdate -c -i firmware.swu -k public.pem

# 执行更新
swupdate -i firmware.swu -k public.pem

# 以守护进程方式启动（内置 web 服务器 / hawkBit 客户端）
swupdate -f /etc/swupdate.cfg -v
```

## 已知限制

- U-Boot 环境变量接口（swupdate vars / hawkBit `action_id` 持久化）在
  OHOS 上不可用（无 libubootenv），调用返回 `-ENOTSUP`、hawkBit 侧降级为
  WARN 后继续。
- MTD/CFI/UBI 面已启用（依赖制品仓 libmtd/libubi），但设备无真实 NAND
  夹具，`test_flash_handler` 以 mock 驱动验证。
- CMS 签名（`CONFIG_SIGALG_CMS`）未启用，`SIGALG_RAWRSA` 覆盖签名校验面。
- 产物为 unstripped（上游 `SKIP_STRIP=y`），体积较 strip 版大；这是为保住
  OHOS 的 ELF 代码签名语义。

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 2026.05.1 | built | 首个 OHOS PC (aarch64) 适配版本 |
