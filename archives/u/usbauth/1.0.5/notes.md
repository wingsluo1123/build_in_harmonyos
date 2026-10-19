# usbauth 1.0.5 适配说明（HarmonyOS PC / ohos-aarch64）

## 1) 身份与源

- 上游：`https://github.com/kochstefan/usbauth-all` 里的 **usbauth** 子工程；平台版本 **1.0.5**。
- 源取 Debian 源包的 orig：`usbauth_1.0.5.orig.tar.gz`，sha256
  `8df8b44028bbee7ca39c177ada0678911341bd9128f9f239fc6adec2eafa7101`，包内**单层根目录 `usbauth/`**。
- ⚠️ 上游 `configure.ac` 的 `AC_INIT([usbauth], [1.0.3], …)` **发版时忘改**（仍是 1.0.3）→
  二进制自报版本可能是 1.0.3；**包版本以 1.0.5 为准**，此处如实记录。

## 2) 依赖（上游 configure.ac 实证，三个全在制品仓/仓库）

```m4
PKG_CHECK_MODULES([USBAUTH], [libusbauth-configparser])
PKG_CHECK_MODULES([UDEV],    [libudev])
PKG_CHECK_MODULES([DBUS],    [dbus-1])
```

| 依赖 | 本仓库里的提供者 | 说明 |
|---|---|---|
| `libusbauth-configparser` | `libusbauth-configparser/1.0.5` | 制品仓已有归档（平台对应任务已完成） |
| `libudev` | `libudev-zero/1.0.4` | libudev-zero 提供的 `.pc` 名就是 `libudev` |
| `dbus-1` | `dbus/1.16.2.1` | ✓ |

**因此本包不需要任何前置依赖适配。**

## 3) 构建（autotools，四道坎都踩到了）

源包**没有预生成的 `configure`**（只有 `configure.ac` + `autogen.sh`）→ 必须 `autoreconf` 自举：

1. **工具依赖**：conan 的 `automake/1.18` + `libtool/2.5.4` 要作为 `tool_requires` —— 本机与 CI 镜像里
   都没有系统 automake，实测报 `Can't exec "aclocal": No such file or directory`。
2. **清 PERL 环境**：自举前清掉 conan 注入的 `PERL5LIB`/`PERL5OPT`/`PERL_MM_OPT`/`PERL_LOCAL_LIB_ROOT`，
   否则宿主 `aclocal` 会加载包内半套 perl 模块而崩（本仓库已记录过的坑）。
3. **补 `m4/` 空目录**：发布源里没有 `m4/`，`aclocal` 会报
   `.aclocal-real: warning: couldn't open directory 'm4'` → 在 `source()` 里先建一个空目录。
4. **修 `configure` 的 `umask`**：HMDFS 下 `umask 077` 会让 `config.status` 建出的临时目录/文件不可访问，
   实测报 `./config.status: line N: ./confXXXX/subs1.awk: Permission denied` →
   `config.status: error: could not setup config files machinery`。
   做法：**在 autoreconf 之后**把 `<source>/**/configure` 里的 `umask 077` 改成 `umask 022`
   （放前面会被重新生成的 configure 覆盖 —— 与 austin 配方的既有做法一致）。
5. `--build=aarch64-unknown-linux-musl`：上游那份 `config.guess` 认不出 OHOS 三元组。

## 4) 测试

- **上游测试数 = 2**（Debian autopkgtest：`packages/libusbauth-configparser/debian/tests/test` 与
  `packages/usbauth/debian/tests/test`）。**#1 已真实执行通过**：其断言是"库已安装且能被动态加载器找到"
  （原文 `ldconfig -p | grep libusbauth-configparser`），本环境无 `ldconfig` → 以**同一断言的可移植形态**
  执行（对依赖包里的 `libusbauth-configparser.so` 由**动态加载器**在交付的 usbauth 启动时载入该库并运行（日志 `[upstream test #1] …`）✓；②再断言安装位置的文件存在且可读 ✓。注：CI 沙箱拒绝任意路径的直接 dlopen —— #96988（依赖缓存路径）与 #97037（构建目录里的 755 副本）两次实测均报 `Permission denied`，故不采用 ctypes 直载；库缺失/损坏时 usbauth 会以加载失败退出，断言仍可失败）✓。
  **#2 不可执行**：需 root + 活的 D-Bus 系统总线（上游 `control` 自述 `Restrictions: needs-root`、
  `Depends: dbus`；本环境无 `dbus-daemon`/`systemctl`/`service`）→ 属具体技术原因，非人为跳过。
- 配方内在 `build()` 之后**真跑**产物：`--help` / `--version` / `-h` 任一路径必须 rc=0 且有输出。
  **✅ 通过**，但**如实披露语义**：输出首行是
  `usbauth[NNNNN]: error at parsing usbauth configuration file` —— 沙箱里没有 USB 设备、`/etc/usbauth.conf`
  也不在系统位置，这属**预期**信息；该断言证明的是"二进制能加载、能执行"，**不代表设备授权流程已验证**。
- 消费者侧 `test_package/check_usbauth.py` **6 项**（全部离线）：产物 / ELF 头 / **真跑** / **配置与 udev
  规则随包**（`etc/usbauth.conf`、`lib/udev/rules.d/20-usbauth.rules`）/ 许可证 / 证据（sha256）。
  末行打印 `checks=/fails=/skips=`；仅环境原因才计入 skips 且不计入通过。
- 自检环境注意：`LD_LIBRARY_PATH` 必须并入**全部 host 依赖（含传递依赖）**的 lib 目录 ——
  只列直接依赖会漏掉 `libexpat.so.1`（dbus 传递来的），加载器会直接以 **rc=127** 退出。

## 5) 安装落点

上游是 `sbin_PROGRAMS = usbauth` → 产物在 **`sbin/usbauth`**（不是 bin/），另随包安装
`etc/usbauth.conf`、`lib/udev/rules.d/20-usbauth.rules`、`share/man/man8/usbauth.8`。
`package_info()` 里 `bindirs` 同时声明 `sbin` 与 `bin`，避免消费方找不到。

## 6) 实测（本地 conan create）

见 PR 正文「验证结果」段（构建与消费者校验的实际输出与计数）。
