# sircbot 0.4 适配笔记

## 编译环境

- 构建系统: makefile（手写 Makefile，无 configure）
- 目标平台: HarmonyOS PC（OHOS/aarch64 原生；`HongMeng Kernel 1.12.0`，arm64）
- Conan profile: `ohos-aarch64`（host 与 build 均为目标机配置）
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，由 Conan conf 提供）
- 编译日期: 2026-10-15
- 状态: built（本地验证通过，尚未 release）
- 语言预检（R47）: `expected=cpp, detected=c`，主体 4 个 C 源文件（100%），C↔C++ 属兼容族

## 编译步骤

上游 Makefile 的默认目标 `all` 会把 Lua 绑定一并编入 `$(TARGETS)`，而该开关写法为
`ifneq (NOLUA,)`——它比较的是字面量 `NOLUA` 与空串，恒为真，所以 Lua 目标无法从命令行
关闭。因此构建显式指定两个核心目标：

```bash
make CC=clang sircbot sircbot-send -j1
```

`make install` 同样不可用（它依赖被污染成含 Lua 的 `$(TARGETS)`），产物由配方直接拷入
`bin/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `/var/run` 不存在、`/var` 不可写（mkdir 报 Permission denied），daemon 无法写 pidfile | 鸿蒙 rootfs 布局与常规 Linux 发行版不同 | 运行目录改为运行时可配置 `SIRCBOT_RUNDIR`（默认仍为 `/var/run/sircbot`），并在启动时按需创建 |
| 2 | `/etc` 为只读文件系统，钩子目录 `/etc/sircbot.d` 无法存在 | 同上 | 钩子目录改为运行时可配置 `SIRCBOT_HOOKSDIR`（默认仍为 `/etc/sircbot.d`） |
| 3 | `/bin/run-parts` 不存在，钩子从不执行（`execlp` 传的是绝对路径，不走 PATH） | 系统未提供 run-parts(8) | runner 依次尝试 `SIRCBOT_RUNPARTS` → `/bin/run-parts` → PATH 中的 `run-parts`，全部失败则使用补丁内置的 POSIX 目录扫描回退 |
| 4 | **路径名 AF_UNIX socket 在任何用户可写目录 bind 都返回 EPERM**，`sircbot-send` 报 `No such file or directory`，核心发消息功能整体不可用 | 鸿蒙内核对用户目录下的路径名 unix socket 有安全限制 | 通道 socket 改为「路径名优先，被拒则回退抽象命名空间（`sun_path[0]=='\\0'`）」，守护进程与客户端对称实现 |
| 5 | 出站消息永不送达：`sircbot-send` 返回 0，但 IRC 服务器收不到 PRIVMSG | 上游 `sb.chan[i].last_data_sent` 从未初始化即被 `send_fifo_queue()` 读取；malloc 垃圾值落在未来时 `(now - last_data_sent) < flush_rate` 恒真，队列永不刷新 | 在 `main()` 初始化 `last_data_sent`（并一并初始化同类未初始化的 `last_ping`） |

问题 4 的实测证据（真机，路径名 bind 直接探测）：

```
/storage/.../runprobe/a.sock   -> [Errno 1] Operation not permitted
$HOME/a.sock                   -> [Errno 1] Operation not permitted
rel.sock                       -> [Errno 1] Operation not permitted
/dev/shm/a.sock                -> [Errno 13] Permission denied
abstract b'\x00sircbot-probe'  -> OK
tcp 127.0.0.1                  -> OK
```

## 源码修改

补丁由 `refresh-patch --auto` 生成，共 2 个文件，**新增行中不含任何平台宏**（R8/PF5）：

### `patches/0001-sircbot-send.c.patch`（+50/-5）

- socket 目录改由 `SIRCBOT_RUNDIR` 决定，默认值仍为 `/var/run/sircbot`。
- `connect_channel()` 先按历史路径名地址连接；失败后改用与守护进程同名的抽象命名空间地址。

### `patches/0002-sircbot.c.patch`（+142/-18）

- `DEFAULT_RUNDIR` / `DEFAULT_HOOKSDIR` 取代写死的路径；新增 `env_str()`（运行期覆盖）、
  `ensure_dir()`（按需创建运行目录，best-effort）。
- `init_channel_socket()`：路径名 bind 成功后 `goto bound`；被拒时改用 `abstract_addr()`
  构造的抽象命名空间地址再 bind 一次。两条路径都不成立才报错。
- `run_hooks()`：钩子目录来自 `SIRCBOT_HOOKSDIR`；runner 依次尝试 `SIRCBOT_RUNPARTS`、
  `/bin/run-parts`、PATH 中的 `run-parts`，都不可用时调用新增的 `run_hook_dir()`——按
  run-parts 语义（`-a user -a data -a rcpt` 即三个位置参数）执行目录内全部可执行普通文件。
- `main()`：初始化 `last_data_sent`/`last_ping`；pidfile 路径跟随 `SIRCBOT_RUNDIR`，并
  修正上游 `snprintf(pidfile, sizeof(pidfile_suffix), ...)` 误用 64 字节长度截断 PATH_MAX
  缓冲区的问题。

补丁只做「新增运行期覆盖 + 回退」，上游默认路径与行为在路径可用的系统上保持不变；未使用
`#ifdef __OHOS__`，因此不涉及 R8 例外说明。补丁已用原始源码验证可干净应用，且应用后与调试
工作目录逐字节一致。

## 依赖版本

无第三方依赖。仅使用目标机 libc（musl）与 clang 15 自带头文件；链接 libc 由编译器隐式完成。

## 未纳入本次适配的上游可选组件：Lua 绑定

上游 `lua/lsircbot.c` 提供 Lua 绑定（README："To build the lua module you need Lua 5.1, 5.2
or 5.3"）。本次**未构建**，理由如下：

1. 制品仓 `ohpcd` 的 lua 包只发布**开发件**（`include/lua.h`、`lib/liblua.a`），包内没有
   `bin/` 解释器；本机与制品仓都没有 Lua 解释器。绑定的真实用途是 `require('sircbot')` 后
   由解释器加载 `.so`，**没有解释器就无法在目标机验证其真实运行行为**；按规则 12/R40
   「未验证的功能不发布」的原则不纳入交付。
2. 上游 Makefile 恒真守卫使该目标无法通过命令行关闭（见上），所以本次以显式目标构建核心产物。
3. 该文件同样使用路径名 unix socket，若将来启用需同步施加与本补丁相同的抽象命名空间回退。

## 验证结果

```bash
# 干净构建 + 消费者端到端测试（conan create 内部执行上游测试与 test_package）
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

上游测试清点结论：**上游无任何测试**（Makefile 无 `check`/`test` 目标，`make -n check` 报
"No rule to make target 'check'"，源码无断言），故上游实测数为 0，全部验证来自本次新增的
消费者端到端用例。

### 规则 12：鸿蒙消费者端到端用例（已在鸿蒙 PC 目标机实跑通过）

| 项 | 内容 |
|----|------|
| 用例 ID | `E2E-1` |
| 用例数 / 断言数 | 1 个完整消费者用例 / 7 项断言，**7 PASS、0 FAIL、0 SKIP** |
| 用户场景 | 脚本/CI 钩子把一条消息投到 IRC 频道，并让 bot 在收到频道消息时执行本机脚本 |
| 被测产物 | 本配方安装后的 `bin/sircbot`、`bin/sircbot-send`（经 `VirtualRunEnv` 注入 PATH，确认解析到包内产物） |
| 源码/入口 | `test_package/consumer_test.sh`（对端脚手架 `test_package/fakeircd.py`） |
| 真实输入 | 出站 stdin 文本 `hello-from-iot`；入站 `:alice!u@h PRIVMSG #testchan :hello-from-irc` |
| 完整流程 | 起伪 IRC 服务器作对端 → 以**守护进程模式**启动 `sircbot -l <log> -s 127.0.0.1 -p <port> -n testnick '#testchan'` → 等握手/JOIN 与频道 socket 就绪 → `printf 'hello-from-iot\n' \| sircbot-send '#testchan'` → 对端注入一条入站消息 → 核对输出 |
| 预期业务输出 | 服务器收到 `PRIVMSG #testchan :hello-from-iot`；钩子日志出现 `HOOK-ARGS sender=[alice] message=[hello-from-irc] channel=[#testchan]` |
| 实际命令 | `conan create archives/s/sircbot/0.4 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64`（内部执行 `bash consumer_test.sh`） |
| 目标机 | 本机即鸿蒙 PC 目标机（`HongMeng Kernel 1.12.0 aarch64`），host = build = `ohos-aarch64` |
| 退出码 | `0` |
| 输出核对 | 7 项断言全部 PASS，与预期业务输出逐字一致 |
| 日志定位 | 本地 `reports/w3-local-ci.log` 与 `$TMPDIR/conan-create.log`（按仓库惯例 `reports/` 与日志不入 PR） |

> 计数口径：`E2E-1` 是**一个**端到端流程用例，其内部 7 个断言不拆成 7 个用例，也**不**在
> 上游表中重复计入。上游实测数为 0，未把新增消费者用例反填成上游测试。
> 摘要详见 `test_package/MANIFEST.yml`（`test_package_tests` / `assertion_count`）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/sircbot` | IRC bot 守护进程，每个已加入频道持有 1 个 AF_UNIX socket |
| `bin/sircbot-send` | 命令行客户端，把 stdin 写入指定频道 socket |

## 注意事项

- **运行期目录**：鸿蒙上没有 `/var/run` 且 `/var` 不可写，守护进程模式（非 `-f`）需要写
  pidfile，因此**必须**把 `SIRCBOT_RUNDIR` 指到一个可写目录，否则 `daemonize()` 写 pidfile
  失败并使进程直接退出。`-f` 前台模式不写 pidfile，不受此限。
- **socket 位置**：鸿蒙上频道 socket 注册在抽象命名空间（可用 `grep <channel> /proc/net/unix`
  查看，条目以 `@` 开头），文件系统中**不会**出现 `/var/run/sircbot/<#channel>` 节点。
- **钩子**：脚本目录为 `$SIRCBOT_HOOKSDIR/<频道名>/`，脚本按 run-parts 语义接收三个位置
  参数：发送者、消息、频道名。
- 上游未随源码包提供 COPYING/LICENSE 文件（授权信息写在源文件头注释中，GPL-2），因此
  包内没有许可证文件可分发。
- **PF9 已知假阳性（留痕）**：本变更集含 3 个软件级文件（`README.md`、`commands.json`、
  `manifest.yaml`），其路径层级为 4（`archives/s/sircbot/<file>`），会被 `preflight` 的
  `check_branch_and_paths()` 判为「缺版本目录层」并触发 PF9。但 R38 与 ARCHIVE-SPEC 明确
  要求命令行工具包在软件级目录放置 `commands.json`，故该命中属框架启发式与规范天然冲突的
  假阳性；CI 侧对应门禁 L0n/JC6 并不拦截（W3 本地 CI 实证 JC6「涉及软件数: 1（合规）」）。
  本包按与 CI L0n 同口径处理，**不删除 `commands.json`**（删除会转为 PF8/L0k 真失败）。
- `reports/` 按 `.gitignore` 全局忽略，是供 `submit` 读取的**本地工作态**（审计结果
  `reports/audit-result.json` 亦在此）；持久化的 PR 证据以本 `notes.md`、
  `test_package/MANIFEST.yml` 与 PR 正文为准。
---

**编译结束**: 2026-10-15 20:08
**最终状态**: built
