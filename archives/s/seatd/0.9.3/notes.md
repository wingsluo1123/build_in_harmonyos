# seatd 0.9.3 适配笔记

## 软件信息
- **名称**: seatd
- **版本**: 0.9.3
- **许可证**: MIT
- **上游仓库**: https://git.sr.ht/~kennylevinsen/seatd
- **GitHub 镜像**: https://github.com/kennylevinsen/seatd
- **源码归档**: https://github.com/kennylevinsen/seatd/archive/refs/tags/0.9.3.tar.gz
- **构建系统**: meson (>=0.60.0)
- **类型**: 独立服务/守护进程（积分赛）
- **产物**: seatd 守护进程 (bin/seatd) + libseat 库 (lib/libseat.*)
- **依赖**: 无强制依赖（可选 systemd / elogind，OHOS 上禁用）

## 功能说明
seatd 是一个最小化的 seat 管理守护进程，同时提供 libseat —— 一个通用的 seat 管理
库。libseat 抽象了 seat 的物理设备（键盘、鼠标、显卡等）访问，应用程序通过 libseat
API 申请设备访问权限，由 seatd 守护进程仲裁授权。

## OHOS 适配要点

### 1. 平台选项
- OHOS 平台在 `config_options` 中删除 `shared` 选项，强制静态构建 libseat。
- OHOS 无 systemd / elogind，`libseat-logind` 设为 `disabled`。
- 保留 `server=enabled` 以构建 seatd 守护进程可执行文件。
- `libseat-seatd=enabled`（libseat 通过 seatd 守护进程通信的后端）。

### 2. meson 选项映射
| meson 选项          | 类型  | 取值       | 说明                     |
|---------------------|-------|------------|--------------------------|
| default_library     | -     | static     | OHOS 静态                |
| server              | combo | enabled    | 构建 seatd 守护进程      |
| libseat-seatd       | combo | enabled    | libseat seatd 后端       |
| libseat-builtin     | combo | disabled   | 不内嵌 seatd server      |
| libseat-logind      | combo | disabled   | 无 systemd/elogind       |
| man-pages           | feat  | disabled   | 无 man 页                |
| examples            | combo | disabled   | 不构建示例               |

### 3. 产物
- `bin/seatd`：seatd 守护进程可执行文件
- `lib/libseat.a`（静态）/ `lib/libseat.so*`（动态，非 OHOS）
- `include/libseat.h`：公共头文件
- `lib/pkgconfig/libseat.pc`：pkg-config 文件

### 4. 测试
`test_package/test_package.c` 验证 `libseat.h` 头文件可被包含，并调用
`libseat_open_seat()`。在无 seat 环境（如交叉编译测试）下预期返回 NULL，
头文件可包含即说明库安装成功。

## 已知限制
- seatd 守护进程运行需要访问输入设备（/dev/input、evdev）与 DRM 设备，OHOS
  上需相应的设备节点与权限策略配合。
- 默认 seatd socket 路径为 `/run/seatd.sock`（Linux），可通过 meson 选项
  `defaultpath` 调整。
- 源码归档 SHA-256: `302564d54d8e28191fadfd734f2675ecb0c9e0615a58011b89ef15dfa4dbaa96`。

## 参考
- 上游 README: https://git.sr.ht/~kennylevinsen/seatd
- 类似 meson 适配参考: archives/u/unudhcpd/0.2.1-r2/conanfile.py
