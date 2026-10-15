# sleepd 2.15 — OpenHarmony PC 适配笔记

## 概览

| 项 | 值 |
|---|---|
| 包名 | sleepd |
| 版本 | 2.15 |
| 上游 | Debian 源码包（作者 Joey Hess，原 sleepd 项目） |
| 源码 | `https://deb.debian.org/debian/pool/main/s/sleepd/sleepd_2.15.tar.xz` |
| sha256 | `93511084c4413794e71851417069cb51039ba72fd8dd4cdafce06ddd5f24f52a` |
| 构建系统 | 手写 Makefile（无 configure） |
| 产物 | `bin/sleepd`、`bin/sleepctl` |

## 软件简介

sleepd 是笔记本电源事件守护进程：监视 ACPI/sysfs 电池与电源状态、可选地监视
`/proc/interrupts` 与 `/dev/input/event*` 事件，在设定的电量/负载阈值下执行挂起
或休眠命令。`sleepctl` 是配套的开关工具（on/off/status），供用户态临时抑制休眠。

## 构建要点

### 1. 命令行 CFLAGS 会覆盖 Makefile 的 `+=`

上游 Makefile：

```make
CFLAGS ?= -O2 -g -Wall
CFLAGS += -DACPI_APM -pthread     # 注意这里是 +=
```

配方在命令行传 `CFLAGS='...'` 时，make 的命令行变量会**完全替换**该变量的取值，
Makefile 内的 `+=` 追加随之失效（不是叠加）。因此 `-DACPI_APM` 与 `-pthread`
必须在命令行一并重述，否则 `acpi.c` 的 ACPI 分支不编译、`pthread` 原型缺失。

### 2. 不用上游 `make install`

```make
install:
	install -d $(PREFIX)/usr/sbin/ ...
	$(INSTALL_PROGRAM) -m 4755 -o root -g root sleepctl $(PREFIX)/usr/bin/
```

`-m 4755 -o root -g root` 是 setuid root 安装——设备上无 root 能力、且属主/权限
语义受限（hmdfs）。配方自行 `copy()` 两个二进制与 man 手册，保持 0755。

### 3. 平台事实（实测）

| 检查 | 结果 |
|---|---|
| `-lpthread` 链接 | ✅ 正常（musl 无独立 libpthread，折入 libc） |
| `<linux/input.h>` | ✅ OHOS sysroot 自带（`eventmonitor.c` 直接可用） |
| `/var/run` | ❌ 不存在（控制文件/pid 文件运行期不可写，见下） |

## 上游测试（R51 如实申报）

**上游无测试套件**：Makefile 仅有 `all` / `clean` / `install` 三个目标，源码树内
无 `tests/`、无断言脚本、无 CI 配置。因此上游测试用例数为 **0**，无「未运行」的
上游测试可申报（非"有而未跑"，是客观上不存在）。

功能覆盖由 `test_package` 提供（消费者视角，见下）。

## test_package 设计

`/var/run` 在设备上不存在，但 `sleepd`/`sleepctl` 的控制文件读取失败时
`read_control()` **回落默认值 0**，这让以下断言成为确定性行为：

| # | 调用 | 断言 |
|---|---|---|
| 1 | `sleepd -h` | 退出码 0，stderr 含 `Usage: sleepd`（二进制真实可执行） |
| 2 | `sleepctl status` | 输出含 `sleepd is not running`（pid 文件缺失）与 `sleeping enabled`（控制值回落 0） |
| 3 | `sleepctl`（无参数） | 非零退出，stderr 含 `Usage: sleepctl [on\|off\|status]`（usage 路径真实可达） |

即：验证两个二进制可执行、参数解析路径真实运行、控制文件状态机在"无控制文件"
下的默认语义正确——不依赖 root、不依赖真实电池/电源硬件。

## 已知平台限制

- `/var/run` 不存在：`sleepd` 需自行 `mkdir`（或在有写权限的目录下运行），
  `sleepctl on/off` 需要控制文件可写；本包只交付二进制，运行期目录由部署方准备。
- 真实休眠/挂起依赖 `/sys/power/state` 与 OHOS 电源管理，不在包内验证范围。
