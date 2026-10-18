# sinfo

sinfo — 分布式系统信息监控（作者 Jürgen Rinas）：局域网内每台主机运行
`sinfod` 守护进程，采集系统负载、内存占用与 top-N 进程信息，经 UDP 广播
分发并应答直接查询；`sinfo` 客户端以 ncurses 交互界面或纯文本模式
（`-H` 主机名 / `-L` 负载 / `-I` IP / `-W` HTML）汇总展示，效果类似
分布式 top(1)。RPC 层为上游自制 idlx 代码生成器产物的消息序列化。

上游主页 http://www.ant.uni-bremen.de/whomes/rinas/sinfo/ 已失效
（~2016 起 302 跳转到大学院系页）；Debian pool 保留的 pristine orig
tarball（sha256 与签名 .dsc 一致）是当前唯一稳定的官方原始归档。

## 功能

### sinfod（sbin/，守护进程）
- 周期性向广播地址（默认 255.255.255.255:60003）发送本机测量消息
- 在 UDP/TCP 60002（SINFO_REQUEST_PORT）应答 `sinfo` 客户端的直接查询
- 默认 daemonize；`-F` 前台运行，`-q` 静默，`-b` 设广播地址，
  `-m` 打标记，`-i` 忽略进程，`-t` top 数量，`-N` nice 值

### sshallsinfo（bin/，工具）
- 上游附带：`sinfo --hostsandipmode` 列出在线主机后逐台 `ssh` 执行给定
  命令的扇出脚本（215 字节 POSIX shell）

### sinfo（bin/，客户端）
- `-h host[:port]` 直连指定 sinfod（默认 127.0.0.1），`--udp`（默认）
  / `--tcp` 选择协议
- 默认进入 ncurses 交互界面；`-H`/`-L`/`-I`/`-W` 为非交互输出模式
- `-u` 高亮用户进程，`-d` 刷新间隔，`-t` top 数量，`-c` 负载显示比例

## HarmonyOS PC (arm64) 适配说明

- 交叉编译（clang 15 / libc++ / musl）：上游 autotools tarball 预生成
  configure，三补丁完成 OHOS 平台化（config.guess 注入 HarmonyOS 分支、
  config.sub 接受 linux-ohos、configure 的 umask 077 → 022 修 HMDFS E011）
- configure 传 `--with-boost-signals=no --with-boost-system=no` 跳过两个
  对 Boost 1.84 已无意义的找库检查（代码只用 header-only 的
  asio/signals2/system/bind）；AC_FUNC_MALLOC 交叉编译陷阱用
  `ac_cv_func_malloc_0_nonnull=yes` 缓存变量规避 rpl_malloc 链接错误
- 链接依赖：boost/1.84.0（header-only 用法）+ ncurses/6.6（静态
  libncursesw）；ncurses 的 `use_default_colors()` 因包内无 libncurses
  探测失败而走 `#ifdef` 守卫降级（仅终端底色方案，功能不受损）
- 产物布局：`bin/sinfo` + `bin/sinfod` + `bin/sshallsinfo`（Conan
  AutotoolsToolchain 默认把上游 sbin/ 重定向到 bin/，三可执行同目录）、
  `share/man/man{1,8}`；`lib/sinfo/` 下为上游 pkglib 内部静态归档，
  非公开链接接口；运行时 ABI 为 OHOS PC glibc（解释器
  /lib/ld-linux-aarch64.so.1，NEEDED 仅 libc.so）
- 守护进程在受限环境运行建议 `sinfod -F -q -b 127.0.0.1`（广播收窄到
  环回）；ncurses 交互界面需要真实终端，自动化验证覆盖
  `-H`/`-L` 文本模式与端到端查询

## 依赖关系

- 编译/链接：boost/1.84.0、ncurses/6.6（制品仓均有 OHOS/armv8 二进制）
- 运行：无额外运行时依赖（静态链接 ncurses，musl libc）

## 参考资料

- 上游主页（已失效）: http://www.ant.uni-bremen.de/whomes/rinas/sinfo/
- 源码归档: https://deb.debian.org/debian/pool/main/s/sinfo/
- man pages: sinfo(1)、sinfod(8)（随包安装于 share/man/）
