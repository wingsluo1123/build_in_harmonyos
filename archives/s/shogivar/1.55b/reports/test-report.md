# 测试报告 — shogivar 1.55b

> **项目**: shogivar（C-port 1.55b，GTK+ 3 前端）
> **测试日期**: 2026-10-14
> **测试环境**: HarmonyOS / HongMeng Kernel 1.12.0 aarch64（clang 15.0.4，target aarch64-unknown-linux-ohos）
> **测试类型**: 上游官方测试套件（空）+ 鸿蒙消费者用例

---

## 一、测试摘要

### 1.1 上游官方测试（`make check`）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 0 | — |
| 通过 (PASS) | 0 | — |
| 失败 (FAIL) | 0 | — |
| 跳过 (SKIP) | 0 | — |

上游**没有任何自动化测试用例**（N = 0、N′ = 0），因此通过率不适用。
清点证据见第四节 4.1；`make check` 已实际执行，退出码 0，输出仅
`CDPATH="${ZSH_VERSION+.}:" && cd <srcdir> && true`（automake 在无 `TESTS` 时生成的空规则）。

### 1.2 鸿蒙消费者用例（test_package，R51 要求的适配后新增用例）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 21 | 100% |
| 通过 (PASS) | 21 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**消费者用例通过率**: ✅ **100%（21/21）**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**：包在 OHOS aarch64 上真实构建成功，ELF/动态链接契约与运行期资源契约全部成立；
上游无自动化测试，功能验证由消费者用例承担。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 图形界面需窗口系统 | 无头环境无法断言棋盘/棋规交互 | 🟡 |
| 上游无测试套件 | 无上游回归基线可比对 | 🟡 |

### 2.3 可用功能清单

```
✅ 命令行入口: -v/--version、-h/--help（gtk_init 之前处理，无显示环境可用）
✅ 资源解析: 启动时按可执行文件位置解析 share/games/shogivar（可重定位安装）
✅ 资源完整性: 18 个变体 .dat / 18 个 .rul / 1028 棋子图 / 25 标题图 / 24 帮助图
✅ 动态链接: libgtk-3 / libcairo / libglib-2.0 / libpango-1.0 等 30 个 NEEDED 全部存在
⚠️ 图形棋盘: 需要窗口系统（X11/Wayland/Broadway），CI 无显示
```

### 2.4 已知限制

1. GTK3 图形棋盘必须有窗口系统；无显示环境下 `shogivar` 以
   `Gtk-WARNING: cannot open display:` 与退出码 1 干净退出（非崩溃）。
2. 上游未提供任何自动化测试，无法与上游基线做回归比对。
3. 上游棋规逻辑、棋盘资源与图形交互未在本报告中断言（需真实显示环境），
   本报告不伪造这部分通过。

---

## 三、测试详情

### 3.1 通过的测试（21/21）

#### A. ELF / 动态链接契约（test_package/conanfile.py，纯 Python 解析 ELF）

| # | 测试项 | 功能 | 结果 |
|---|--------|------|------|
| 1 | `ELF64 little-endian aarch64 executable` | 产物是 64 位小端 AArch64 ELF | ✅ PASS |
| 2 | `PT_INTERP is the OHOS musl loader` | 解释器 = `/lib/ld-musl-aarch64.so.1` | ✅ PASS |
| 3 | `DT_NEEDED contains libgtk-3.so.0` | 真实链接 GTK3 | ✅ PASS |
| 4 | `DT_NEEDED contains libcairo.so.2` | 真实链接 cairo | ✅ PASS |
| 5 | `DT_NEEDED contains libglib-2.0.so.0` | 真实链接 glib | ✅ PASS |
| 6 | `DT_NEEDED contains libpango-1.0.so.0` | 真实链接 pango | ✅ PASS |

实测 `e_machine=0xb7 interp=/lib/ld-musl-aarch64.so.1 needed=30 libs`。

#### B. 运行期消费者用例（test_package/test.sh，conanrun 环境中执行包内二进制）

| # | 测试项 | 功能 | 结果 |
|---|--------|------|------|
| 1 | `bin/shogivar installed and executable` | 可执行文件安装到位 | ✅ PASS |
| 2 | `shogivar --version` | 退出码 0，输出 `shogivar version C-port-1.55b` | ✅ PASS |
| 3 | `shogivar -v` | 同上（短选项） | ✅ PASS |
| 4 | `shogivar --help` | 退出码 0，列出 `-v/--version` 与 `-h/--help` | ✅ PASS |
| 5 | `share/games/shogivar asset tree installed` | 资源树存在 | ✅ PASS |
| 6 | 18 个 `*.dat` 齐全且非空 | 变体棋盘定义 | ✅ PASS |
| 7 | 18 个 `*.rul` 齐全且非空 | 变体规则（含 General.rul） | ✅ PASS |
| 8 | `pieces/` ≥ 1028 个文件 | 棋子/棋盘图形 | ✅ PASS（实测 1028） |
| 9 | `titles/` ≥ 25 个文件 | 变体标题图 | ✅ PASS（实测 25） |
| 10 | `help/` ≥ 24 个文件 | 棋子说明图 | ✅ PASS（实测 24） |
| 11 | PNG 魔数 `89504e47` | 代表资源是真实 PNG | ✅ PASS |
| 12 | 资源树无 0 字节文件 | 安装未截断 | ✅ PASS |
| 13 | `share/man/man6/shogivar.6` 非空 | 手册页 | ✅ PASS |
| 14 | `--help` 报告的数据目录存在且可用 | **可重定位安装的端到端验证** | ✅ PASS |
| 15 | 无显示启动干净退出 | 退出码 1（非信号崩溃）且报 display 错误 | ✅ PASS |

### 3.2 失败的测试

无。

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| 图形棋盘交互 / 棋规对弈 | CI worker 无窗口系统（GTK 报 `cannot open display`），无法在无头环境断言；本报告不伪造该项通过 |

---

## 四、关键问题分析

### 4.1 上游测试清点（R51「上游确无测试」证据）

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 测试目录 | `ls -d */`（源码根） | 只有 `Data/`、`gtk/`，无 `tests/`、`test/`、`t/` |
| 测试文件 | `find . -iname "*test*" -o -iname "check*" -o -iname "*.trs"` | 0 命中 |
| Makefile.am 测试目标 | `grep -E "^(TESTS\|check_PROGRAMS\|check_SCRIPTS\|check_LTLIBRARIES)" Makefile.am` | 无输出 |
| 上游文档 | README 全文 | 只讲 `autogen.sh`/`configure`/`make`/`make install`，未提测试方式 |
| `make -n check` | 实际执行 | 仅 `cd <srcdir> && true` |

### 4.2 构建期关键问题（完整清单见 notes.md「遇到的问题与解决方案」）

| 问题 | 根因 | 解决方案（补丁） |
|------|------|------------------|
| `unable to guess system type` | 2014 版 config.guess 无 HarmonyOS 分支 | 0004 |
| `system 'ohos' not recognized` | config.sub 未收 linux-ohos | 0005 |
| `gtk+-2.0 ... were not met` | 上游前端是 GTK2，制品仓只有 GTK3 | 0006/0007 + 0010/0011 |
| `Please install "makeinfo"` | 继承自 XBoard 的检查，shogivar 无 Texinfo 手册 | 0006/0007 |
| `./confXXXXXX/subs1.awk: Permission denied` | HMDFS 忽略 umask/chmod 语义 | 0006 |
| `missing: aclocal-1.14: command not found` | worker 无 automake，maintainer-mode 被触发 | 0001 |
| `jobserver mkfifo: Operation not permitted` | OHOS 禁止 GNU make jobserver 建 FIFO | 全部 make 显式 `-j1` |
| `duplicate symbol: currBoard` | clang 15 默认 `-fno-common` | 0003 |
| 资源目录写死编译期 `/share/games/shogivar` | conan 默认 `--prefix=/` | 0002/0003/0008/0009/0010 |
| `char[80]` 路径缓冲写穿 | 16-bit 时代的 STRING 上限 | 0002 |

---

## 五、测试环境

```
软件版本: shogivar 1.55b (C-port-1.55b)
编译配置: conan create archives/s/shogivar/1.55b
          -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
          --build=shogivar/*
          configure --prefix=/ --disable-update-mimedb --disable-silent-rules
          make -j1 / make check -j1 / make install DESTDIR=<pkg> -j1
依赖:     gtk/3.24.43, cairo/1.18.4（传递: glib 2.84.0.1, pango 1.50.14.1.1,
          gdk-pixbuf 2.44.6.1, atk 2.38.0.1.1, cairo-gobject 1.18.4.2,
          fribidi 1.0.16, libepoxy 1.5.10 …）
conan create 日志: .ci_logs/conan_create_shogivar_1.55b.log
W3 本地 CI 日志:   reports/w3-local-ci.log
Package ID:        9d069a74340868f4bf3ae39e937763cf897f9e2f
```

---

*报告生成时间: 2026-10-14*
