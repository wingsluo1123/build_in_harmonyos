# sleepd：手写 Makefile 的命令行 CFLAGS 覆盖 与 `/var/run` 缺失

> 配套结构化条目：`DRAFT-sleepd-makefile-command-line-cflags-and-var-run.kv`

## 现象

按常规把宏通过命令行传给手写 Makefile 时，编译行为与预期不符；
另外上游 `make install` 在设备上无法执行。

## 坑 1：命令行 `CFLAGS=` 会**整体替换**变量，`Makefile` 内的 `+=` 失效

上游 Makefile：

```make
CFLAGS     ?= -O2 -g -Wall
CFLAGS     += -DACPI_APM -pthread     # ← 注意是 +=
```

GNU make 的语义：**命令行给出的变量值优先级最高，会完全替换该变量的所有取值**，
Makefile 内的 `+=` 追加**不会**与之叠加。所以：

```bash
make CFLAGS='-O2 -g -Wall'          # ← -DACPI_APM / -pthread 丢了！
```

正确做法是在命令行**把宏一并重述**：

```bash
make CC=<clang> \
     CFLAGS='-O2 -g -Wall -DACPI_APM -pthread' \
     LIBS='-lpthread'
```

漏掉 `-DACPI_APM` → `acpi.c` 的 ACPI 分支不编译；漏掉 `-pthread` → pthread 原型缺失。

## 坑 2：上游 `make install` 是 setuid root 安装

```make
install: $(BINS)
	install -d $(PREFIX)/usr/sbin/ $(PREFIX)/usr/share/man/man8/ \
	    $(PREFIX)/usr/bin/ $(PREFIX)/usr/share/man/man1/
	$(INSTALL_PROGRAM) sleepd $(PREFIX)/usr/sbin/
	install -m 0644 sleepd.8 $(PREFIX)/usr/share/man/man8/
	$(INSTALL_PROGRAM) -m 4755 -o root -g root sleepctl $(PREFIX)/usr/bin/   # ← setuid
```

`-m 4755 -o root -g root` 需要 root 且依赖属主语义（hmdfs 上受限）。
配方**自行 `copy()`** 两个二进制（0755）与 man 手册，不使用该 install 目标。

## 坑 3：设备 `/var/run` 不存在 —— 反而给了确定性断言

```c
#define PID_FILE     "/var/run/sleepd.pid"
#define CONTROL_FILE "/var/run/sleepd.ctl"
```

设备上 `/var/run` 目录**不存在**：

```
$ ls -ld /var/run
ls: /var/run: No such file or directory
```

于是运行期：

- `read_control()` 打开失败 → **回落默认值 0**（enabled）；
- `getpid()` 读 pid 文件失败 → 返回 -1，`verify_daemon_running()` 打印
  "sleepd is not running"。

这让 `sleepctl status` 的输出**完全确定**，因此 test_package 可以做真实断言而
**无需 root、无需电池/电源硬件**：

| # | 调用 | 断言 |
|---|---|---|
| 1 | `sleepd -h` | 退出 0，stderr 含 `Usage: sleepd`（二进制可执行、参数解析到 usage 分支） |
| 2 | `sleepctl status` | 含 `sleepd is not running` 与 `sleeping enabled`（控制文件缺失下的默认语义） |
| 3 | `sleepctl`（无参数） | 非零退出 + 含 `Usage: sleepctl [on\|off\|status]` |

## 平台事实（实测）

| 检查 | 结果 |
|---|---|
| `-lpthread` 链接 | ✅ 正常（musl 无独立 libpthread，折入 libc） |
| `<linux/input.h>`（eventmonitor.c 用） | ✅ OHOS sysroot 自带 |
| `/var/run` | ❌ 不存在（见上） |

## 上游测试（R51 如实申报）

上游**无测试套件**：Makefile 只有 `all` / `clean` / `install` 三个目标，
源码树内无 `tests/`、无断言脚本。因此上游用例数为 **0**（客观不存在，
非"有而未跑"），功能覆盖由 test_package 提供。
