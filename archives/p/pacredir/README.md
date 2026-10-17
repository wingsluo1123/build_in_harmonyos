# pacredir

pacredir 是一个 pacman 镜像重定向守护进程：它监听 `127.0.0.1:7077`，把 pacman
发出的 `*.db` / `*.files` / `*.pkg` 下载请求以 HTTP 307 重定向到局域网内经 mDNS
（`_pacserve._tcp.local`）发现的对等 pacserve 镜像上，并在 `/` 暴露一个每 30 秒
自刷新的 HTML 状态页（内嵌 favicon.png 与 style.css，无需外部静态文件）。

## 功能概述

- **peer 发现**：经 systemd-resolved 的 `org.freedesktop.resolve1.Manager.ResolveRecord`
  D-Bus 方法查询 mDNS PTR/SRV/TXT 记录，并用 TXT 里的 `arch=` / `id=` 过滤掉
  架构或发行版不匹配的对等体；
- **静态 peer**：`/etc/pacredir.conf` 的 `pacserve hosts` 项可绕过 mDNS 直接指定
  对等体（`general:ignore interfaces` 可排除网卡，`general:verbose` 调日志级别）；
- **择优重定向**：用 libcurl 的 multi 接口并发探测候选 peer 的目标文件，按
  `CURLINFO_TOTAL_TIME` 选最快者；对返回坏结果的 peer 做指数退避（`BADTIME`
  起始 30 秒，每次翻倍）；
- **状态页与探针**：`/` 状态页统计 redirects / not found 并给出健康色标，
  `/check` 返回纯 `OK` 供监控探活；
- **信号控制**：`SIGHUP` 重置退避计数并立即重新发现，`SIGUSR1`/`SIGUSR2` 转储
  内部状态（忽略网卡、已知 peer、计数器），`SIGINT`/`SIGTERM` 干净退出；
- **systemd 集成**：`sd_notify` 上报就绪与计数状态，`sd_journal_send` 写日志，
  以 root 启动时自动降权到 uid/gid 65534。

上游整体只有 1 个 C 源文件（`pacredir.c`）+ 4 个头文件，构建系统是裸 GNU Makefile。

## OHOS 适配

### 可执行产物在 OHOS 上是完整的

HTTP 服务、状态页、静态资产投递、配置解析、libcurl 并发探测与择优、信号控制、
降权、日志回退全部可用。编译产物为 AArch64 PIE，`DT_NEEDED` 为
`libcurl.so` + `libsystemd.so.0` + `libc.so`（libmicrohttpd / iniparser / zlib
在制品仓里本就是静态库，均已静态吸收；libcurl 保留动态的原因见下文适配要点 5）。

### 平台能力缺口：mDNS 自动发现

OHOS 不运行 systemd，因此没有 systemd-resolved、没有系统 D-Bus 总线、也没有
journald。对应行为：

| 上游能力 | OHOS 上的表现 |
|---|---|
| mDNS peer 自动发现 | `sd_bus_open_system()` 失败，上游走 `goto fast_finish` 优雅降级：守护进程**不崩溃**，peer 表为空，只记录一条 `Failed to open system bus` |
| `sd_notify` 就绪/状态上报 | 无 `NOTIFY_SOCKET` → 返回 0 → `systemd=0`，不影响主流程 |
| `sd_journal_send` 日志 | 无 journald → 调用失败被忽略；`write_log` 回退到 stdout/stderr（这正是 OHOS 上唯一的日志出口） |

**因此 OHOS 上 pacredir 的实际可用形态是「静态 peer 重定向器 + 状态页」**：
在 `/etc/pacredir.conf` 里用 `pacserve hosts` 显式列出对等体，重定向主链路即完整
可用；mDNS 自动发现则需要平台提供 systemd-resolved 等价的 mDNS/DNS-SD 解析服务。
这不是本次适配引入的限制，而是上游把发现能力硬绑在 systemd-resolved D-Bus 接口上的
直接后果。

### 构建期适配要点

1. **musl 头文件与类型**：上游 `pacredir.h` 依赖 glibc 的传递包含与内部 typedef，
   需补 `#include <sys/ioctl.h>`（`ioctl` / `SIOCGIFFLAGS`）并把 `__time_t` 换成
   POSIX 的 `time_t`。见 `0.7.10/patches/`。
2. **Arch 专有的构建期探测**：上游 Makefile 在解析期 `source /etc/makepkg.conf`
   取 `CARCH`、`source /etc/os-release` 取 `ID`；OHOS 上两个文件都不存在，
   `$(shell)` **静默返回空串**并把空值经 `version.h` 编进二进制，进而污染运行期的
   DNS-SRV TXT 匹配与 curl User-Agent。配方改为从 Conan settings 推导并显式传
   `ARCH=aarch64` / `ID=ohos`。
3. **Rust-only 资产工具链**：`favicon.h` 上游由 `resvg --width=32 --height=32
   logo.svg | oxipng -` 生成，两者都是 Rust CLI，制品仓未发布且 CI 无 Rust 工具链。
   配方用纯标准库 Python 复刻整条链（解码随包 `logo.png` → 最近邻缩到 32x32 →
   重编码 → 生成同构 C 头），并对产物做 chunk CRC 与维度自校验。
4. **不可移植的资产脚本**：`contrib/static_file.sh` 的 shebang 是 `#!/bin/sh` 却用了
   bash 4 的 `${NAME^^}`，还依赖 GNU `stat --format=%s` 与 coreutils `sha1sum`。
   不改上游脚本，由配方按同一份 `static_file.h` 布局直接产出。
5. **依赖图冲突与 override 方向**：`systemd` 钉 `zlib/1.3.1`（非 PIC），`libcurl` 钉
   `zlib/1.3.1.1`（PIC），同图必冲突；override 到任一方都会让另一方失去预编译二进制、
   被迫从源码重建。配方选 **override 到 `zlib/1.3.1.1`**，让 libcurl 沿用已发布的动态
   二进制，把源码重建推给 `systemd`（纯 meson + ninja）。这个方向是被远程 CI #93768
   逼出来的：反向方案（override 到 1.3.1 + libcurl 切静态）会让 libcurl 从源码构建，
   其 CMake 走 `make -j20`，在 OHOS 上必撞 SELinux 禁 FIFO（E074/E525：GNU make 的
   jobserver 靠 FIFO 传并行令牌），报 `jobserver mkfifo: Operation not permitted` →
   `/bin/sh: can't fork` → `Error 127`；而那个 `-j20` 出自 libcurl 自己的配方，下游
   无从干预（`tools.build:jobs` 属 profile/conf，改它等于在单库 PR 里动框架文件）。
   ninja 用 pipe 不用 FIFO，故 systemd 不受影响；且 systemd/261.1 本身就是经 PR CI
   从源码构建成功后才发布的，worker 侧 meson/ninja 可用性已有实证。
6. **已发布 libsystemd.so 的悬空符号**：`libsystemd.so.0.44.0` 带一个未定义的
   `mallinfo2`，链接**可执行文件**时会被 lld 的 `--no-allow-shlib-undefined`
   升级成硬错误。配方加 `-Wl,--allow-shlib-undefined`，只放行共享库自身的未定义
   符号，pacredir 自己的未定义符号仍照常报错。

详细过程、实测数据与逐条根因见 [0.7.10/notes.md](0.7.10/notes.md)。

## 依赖关系

**编译依赖**（全部已在 ohpcd 制品仓发布，`conan download --only-recipe` 实测）：

| 包 | 版本 | 提供的能力 |
|---|---|---|
| `systemd` | 261.1 | libsystemd：sd-bus / sd-daemon / sd-journal |
| `libmicrohttpd` | 1.0.1 | HTTP 服务与响应构造 |
| `libcurl` | 8.5.0（沿用已发布的 `shared=True` 动态二进制） | peer 探测与计时（multi 接口） |
| `iniparser` | 4.2.6 | `/etc/pacredir.conf` 解析 |
| `zlib` | 1.3.1.1（override，libcurl/systemd 的传递依赖） | — |

**运行依赖**：`libcurl.so`、`libsystemd.so.0`、`libc.so`（即 `DT_NEEDED` 全集；
`libcurl.so` 的 SONAME 就是无版本号的 `libcurl.so`，实测可解析）。

**上游需要但本适配未打包的构建期工具**：`resvg`、`oxipng`（Rust，已由配方复刻）、
Perl `markdown`（生成 .html 文档，改为只装 .md 原文）、`darkhttpd`（上游把
`pacserve` 做成指向它的符号链接，属 Arch 侧 systemd unit 配套件）。

## 参考资料

- 上游仓库：<https://github.com/eworm-de/pacredir>
- 上游文档：<https://pacredir.eworm.de/>
- pacserve（对等的镜像服务端，Arch 侧由 darkhttpd 承担）：<https://github.com/eworm-de/darkhttpd>
- 本仓归档：[0.7.10/](0.7.10/)
