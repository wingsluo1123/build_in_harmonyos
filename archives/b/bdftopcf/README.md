# bdftopcf

**X.Org BDF → PCF 字体编译器**（X.Org Foundation，MIT/X11）

`bdftopcf` 把 BDF（Bitmap Distribution Format，可读的位图字体描述）编译成
PCF（Portable Compiled Format，X server / font server 实际读取的编译字体）。
PCF 按字节序分小端/大端两种结构，任何架构都能读；本机直接读时走"免重排"快路径，
跨架构读则慢一些但仍可用 —— 这正是它存在的意义（上游 `README` 原文）。

## 用法

```bash
bdftopcf [-p#] [-u#] [-m] [-l] [-M] [-L] [-t] [-i] [-o pcf 文件] [bdf 文件]
    # 其中 -p 的 # 取 1、2、4、8；-u 的 # 取 1、2、4
```

| 形态 | 行为 |
|------|------|
| `bdftopcf -o out.pcf in.bdf` | 编译到指定文件（**`-o` 是选项**，不是第二个位置参数） |
| `bdftopcf in.bdf > out.pcf` | 不给 `-o` 时把 PCF 写到 stdout |
| `bdftopcf < in.bdf` | 不给位置参数时从 stdin 读 BDF |
| 任意未知参数 | `invalid option` + usage，**退出码 1** |

⚠ **本工具没有 `--version` / `--help`**：`-v`/`--foo` 一律走 `invalid option` + usage、
退出码 1。验证时请用**真实的 BDF→PCF 转换**（断言 PCF magic `01 66 63 70`），
不要断言版本号输出。

本包提供命令行工具 `bdftopcf`，不含库与头文件（见 `commands.json`）。

## 构建系统

上游 tarball 是标准 autotools 树（`configure` + `Makefile.am`，X.Org 官方发布路径），
本仓走 **autotools**：设备与 CI 均具备，也是上游发布时验证过的一条。

## OHOS 适配要点

详见版本级 `notes.md` 与 `1.1/manifest.yaml` 的 `ohos_adaptation`。摘要：

1. **依赖只有 `xorgproto/2025.1`（header-only）** —— `configure.ac` 无 `AC_CHECK_LIB` /
   `PKG_CHECK_MODULES`，`Makefile.am` 链接行只有 `CWARNFLAGS`；被包含的 8 个 X11 头
   （`X.h`/`Xproto.h`/`Xos.h`/`Xfuncproto.h`/`Xfuncs.h`/`Xdefs.h`/`fonts/fontstruct.h`/
   `fonts/FSproto.h`）逐一实测都在 conan 的 `xorgproto` 包里 ⇒ **不拉 `libx11`**。
2. **`config.guess` / `config.sub` 不识 `uname -s = HarmonyOS`** ⇒ 补 HarmonyOS case 与
   `linux-ohos*` 白名单（E007/E072）。⚠ 本包是 **2017 老版 `config.guess`**（分支 `echo+exit`，
   无 `GUESS=` 变量）与 **2017 老版 `config.sub`**（要补 KERNEL-OS 与 basic-system-types **两处**），
   **与同族 `appres` 的新版写法不可互抄**。
3. **`configure` 的 `umask 077 && mktemp -d`** 建 700 目录，HMDFS 拒写 ⇒ 022 + `mkdir`（E110/E112）。
4. **不注入平台宏**（R8/PF5）：全文无 `__OHOS__` 字面量，`config.guess` 靠 uname 名识别 OS。
5. **不采用 `--build`/`--host` 绕过** `config.guess`（会被判交叉编译、跳过 `AC_RUN_IFELSE`
   生成错误 `config.h`）。

## 测试

- **上游测试资产 0**（`§12.72` 四口径就地清点：无 `test*/`、无 `*/res`、无 `*RUNTEST*`、
  无 `demo|examples`；`Makefile.am` 未注册 `TESTS`/`check_PROGRAMS`），`make check` 实测空转
  （`Nothing to be done for 'check'`，rc=0）。
- `test_package/test.sh` 提供 **7 条**消费者断言，实测 **`7/7 checks PASS`**：
  `-o` 主用法、PCF magic `01 66 63 70`、产物非空、`stdin→stdout` 流式路径、`-p8` 选项、
  损坏输入错误路径、文件缺失错误路径。全部**不落盘**（`-o /dev/null` + stdout 管道），
  且**不依赖 X server**（`bdftopcf` 是纯本地文件编译器，`DISPLAY` 未设不影响任何断言）。
