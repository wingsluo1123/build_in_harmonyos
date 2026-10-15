# ubridge 1.1.1 适配笔记

## 编译环境
- 构建系统: makefile（上游裸 Makefile，无 configure）
- 编译日期: 2026-10-13
- 编译器: clang（OHOS SDK 15，`tools.build:compiler_executables.c`）
- 目标平台: OpenHarmony / HarmonyOS PC (aarch64，os=OHOS 6.0，arch=armv8)
- 状态: published

## 编译步骤

```bash
# 依赖：libpcap/1.10.6（iniparser 用上游自带 src/iniparser/，不引外部包）
conan create archives/u/ubridge/1.1.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方 `build()` 实际执行（源码即构建目录）：

```bash
make CC=<conf: tools.build:compiler_executables.c> \
     "CPPFLAGS=-I<libpcap includedirs>" "LDFLAGS=-L<libpcap libdirs>" -j1
```

上游 Makefile 没有 `.c.o` 规则，走 make 内建规则 `$(CC) $(CPPFLAGS) $(CFLAGS) -c`，
因此用 `CPPFLAGS` 传依赖头文件目录，不会覆盖 Makefile 自己的 `CFLAGS += -Wall`；
链接行为 `$(CC) $(CFLAGS) $(LDFLAGS) -o ubridge $(OBJ) $(LIBS)`，`-lpcap` 上游已写在
`LIBS` 里，只需补 `-L`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译出来的二进制缺 brctl/link/docker/iol_bridge 模块，`nio_linux_raw.c`、`netlink/nl.c` 等 6 个源文件根本不被编译 | 上游 Makefile 用 `ifeq ($(shell uname), Linux)` 判定 Linux，而 OHOS 的 `uname` 返回 `HarmonyOS`（`uname -o` 仍是 `GNU/Linux`），Linux 分支被跳过（补丁 0001） | Makefile 判定改为 `ifneq ($(filter Linux HarmonyOS,$(shell uname)),)` |
| 2 | `struct sockaddr_storage` 重复定义：`error: redefinition of 'sockaddr_storage'` | OHOS 的 UAPI `<linux/socket.h>`（由 `<linux/if.h>` / `<linux/netlink.h>` / `<linux/if_tun.h>` 间接引入）与 musl 的 `<sys/socket.h>` 都定义该结构（知识库 E091） | 6 个包含点在包含内核头期间临时 `#define sockaddr_storage __linux_sockaddr_storage` 把内核头的 struct tag 改名、包含后 `#undef`（无条件改写，不含平台条件编译，补丁 0002–0008） |
| 3 | `error: unknown type name 'ushort'` | `ushort` 是 glibc/SysV 专有类型，musl 只提供 `u_short`（所以 `u_char`/`u_int` 能编过，`ushort` 不能） | `src/netlink/nl.h`、`src/netlink/nl.c` 各 1 处改为标准 `unsigned short`（补丁 0005/0006） |
| 4 | 链接失败：`undefined symbol: pthread_cancel` / `pthread_testcancel` | OHOS 的 musl 不实现线程取消 API：`<pthread.h>` 不声明、`libc.so` 也未导出（只在静态 `libc.a` 里有），知识库 E085/E513 | 新增 `src/ohos_pthread_compat.c`：进程级安装一次 SIGUSR1 处理器（处理器内 `pthread_exit`），`pthread_cancel(t)` 改为 `pthread_kill(t, SIGUSR1)`，`pthread_testcancel()` 空实现（补丁 0009）。**没有用空实现顶替**——ubridge 的用法恒为 `pthread_cancel(tid); pthread_join(tid, NULL);`，空实现会让 `join` 永久阻塞（E513 明确告警）。SIGUSR1 在 ubridge 中未被占用（它只用 SIGHUP/SIGTERM/SIGINT/SIGPIPE） |

## 源码修改

补丁 11 枚，全部经 `refresh-patch --auto` 生成：

| 补丁 | 内容 |
|------|------|
| 0001-Makefile.patch | HarmonyOS 视同 Linux；并把 `src/ohos_pthread_compat.c` 纳入 `SRC` |
| 0002–0004, 0007, 0008 | E091 `sockaddr_storage` 改名绕行（hypervisor_brctl.c / hypervisor_docker.c / hypervisor_link.c / nio_linux_raw.c / nio_tap.c） |
| 0005–0006 | `ushort` → `unsigned short`（netlink/nl.c、netlink/nl.h），nl.c 同时含 E091 改名绕行 |
| 0009 | 新增 `src/ohos_pthread_compat.c`（OHOS 线程取消兼容层） |
| 0010 | `main()` 中调用 `ubridge_ohos_pthread_cancel_init()`（非 OHOS 为空操作） |
| 0011 | `src/ubridge.h` 补充 OHOS 兼容接口声明 |

补丁链验证：全新源码树按 `conandata.yml` 顺序重放，11/11 全部干净应用。

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| libpcap | 1.10.6 | ohpcd 制品仓 | 上游 Makefile 链接 `-lpcap`（唯一外部依赖） |
| iniparser | 不使用 | 上游自带 | 上游默认内嵌 `src/iniparser/`（`SYSTEM_INIPARSER != 1`），保持上游默认，不引外部包 |
| python3 | 3.12 | 环境自带 | 仅 `build()` 里跑上游 `tests/brctl/test_no_privs.py` |

## 上游测试申报表（R51 三步法）

### 1. 清点（适配前）

上游 v1.1.1 **没有** `make check` / ctest / meson test / pytest 目标，测试是
`tests/` 下的 Python 黑盒套件，每套一个 `main()`，由 `r.check(描述, 条件)` 断言，
通过 TCP 控制端口驱动 ubridge。清点方式：`tests/*/test_*.py` 文件数 + 各文件
`.check(` 调用数。

| 套件文件 | 检查点数 | 运行前置条件 |
|----------|---------|--------------|
| tests/brctl/test_basic.py | 21 | root + cap_net_admin + `ip` 工具 |
| tests/brctl/test_boundary.py | 36 | root + cap_net_admin + `ip` 工具 |
| tests/brctl/test_concurrency.py | 6 | root + cap_net_admin + `ip` 工具 |
| tests/brctl/test_no_privs.py | 4 | **无特权**（专门测拒绝路径） |
| tests/brctl/test_robustness.py | 15 | root + cap_net_admin + `ip` 工具 |
| tests/brctl/test_state.py | 12 | root + cap_net_admin + `ip` 工具 |
| tests/brctl/test_stress.py | 3 | root + cap_net_admin + `ip` 工具 |
| tests/link/test_basic.py | 22 | root + cap_net_admin + `ip` + veth 支持 |
| **合计** | **8 套 / 119 检查点** | |

### 2. 实跑（本机 OHOS PC，aarch64）

```bash
# 免特权套件（已集成进 conanfile.py build()）
$ cd tests/brctl && python3 test_no_privs.py
  [PASS] hypervisor version works without caps  -- 100
  [PASS] create -> 206/EPERM  -- got 206
  [PASS] delete missing -> 206/EPERM
  [PASS] process alive after test
4/4 PASS          # rc=0

# 其余 7 套（逐套实跑）
$ python3 test_basic.py   # FileNotFoundError: [Errno 2] No such file or directory: 'ip'
$ python3 test_boundary.py     # 同上
$ python3 test_concurrency.py  # 同上
$ python3 test_robustness.py   # 同上
$ python3 test_state.py        # 同上
$ python3 test_stress.py       # 同上
$ cd ../link && python3 test_basic.py   # 同上
```

**逐项技术原因**：上述 7 套在**第一个断言之前**就抛
`FileNotFoundError: [Errno 2] No such file or directory: 'ip'` —— 它们用
`subprocess.run(["ip","-o","link","show",...])` 建立/校验测试 fixture（dummy/veth
接口），而本环境没有 iproute2 的 `ip` 命令；即便有，变更内核 bridge/veth 还需要
root + CAP_NET_ADMIN（本机 `uid=20020085`，无该能力）。这两条都是**环境前置条件
缺失**，与本适配引入的回归无关：`test_no_privs.py` 已证明二进制本身在无特权下的
应答与拒绝语义完全正确（`create -> 206/EPERM` 且进程存活）。

### 3. 如实回填

| 指标 | 数值 |
|------|------|
| 上游测试套件 | 8 套（119 检查点） |
| 实跑并全部通过 | 1 套（test_no_privs.py：**4/4 PASS**） |
| 因环境前置条件缺失无法执行 | 7 套（逐套原因见上：缺 `ip` 工具 + 无 root/cap_net_admin） |
| 上游测试用例修改 | **无**（未改动任何上游测试文件） |
| test_package 消费者测试 | 20 断言 **20/20 PASS**（真实启动二进制并驱动控制协议） |

## 验证结果

```bash
$ conan create archives/u/ubridge/1.1.1 -pr:h=... -pr:b=... --build=missing
...
ubridge/1.1.1: Package 'abcc22ccfacc35e65d0b28eea673a07549943239' built
...
  $ hypervisor module_list -> ['101 link', '101 brctl', '101 iol_bridge', '101 docker', '101 bridge', '101 hypervisor', '100-OK']
  [PASS] E1 module_list 含 hypervisor
  [PASS] E1 module_list 含 bridge
  [PASS] E1 module_list 含 brctl
  [PASS] E1 module_list 含 link
  [PASS] E2 module_list 正常结束 100
  [PASS] F1 cmd_list 有 101 明细行
  [PASS] F2 cmd_list 末行 100
  [PASS] F3 cmd_list 列出 create/delete/show
  [PASS] G1 未知模块 → 201
  [PASS] G2 未知命令 → 202
  [PASS] H1 无特权变更被拒绝(206/207) code=206
  [PASS] H2 被拒绝后进程仍存活并可应答
  [PASS] I1 hypervisor stop → 100
  [PASS] I2 进程在 stop 后退出

通过 20 项，失败 0 项
```

控制协议实测返回的 `module_list` 含 `link` / `brctl` / `iol_bridge` / `docker` / `bridge` /
`hypervisor` 六个模块，这是本适配补丁 0001 生效的直接证据（未打补丁时 OHOS 上只有
`hypervisor` / `bridge` 两个模块）。消费者测试的 E1 断言覆盖其中 `hypervisor` / `bridge` /
`brctl` / `link` 四项（4 条断言，计入 20 条总数）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/ubridge | ~150 KB | aarch64 OHOS ELF 可执行文件（`e_machine=0xB7`，消费者测试实测） |

## 注意事项

- 上游 Makefile 的 `install` 目标用 `setcap`（OHOS 无此工具），配方**不用**
  `make install`，由 conan `package()` 直接拷贝二进制到 `bin/`。
- 二进制需要 `cap_net_admin,cap_net_raw` 才能真实创建/删除内核 bridge；本环境
  无特权，因此 `brctl create` 返回 206/EACCES 属预期行为，不是缺陷。
- 集成测试（`tests/link/`、`tests/brctl/` 多数套件）需要 root + `ip` + 内核
  bridge/veth 支持，本环境与 CI 沙箱均不具备，已如实申报。
---

**编译结束**: 2026-10-13 16:23
**最终状态**: published
