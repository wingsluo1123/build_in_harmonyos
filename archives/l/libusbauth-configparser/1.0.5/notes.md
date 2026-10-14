# libusbauth-configparser 1.0.5 — HarmonyOS PC 适配笔记

## 这是什么

`libusbauth-configparser` 是 [usbauth](https://github.com/kochstefan/usbauth-all)
USB 防火墙的配置文件解析库：一套 **flex 词法 + bison 语法** 的规则解析器，
外加一层小 C API，把 `/etc/usbauth.conf` 里的 `allow`/`deny`/`condition`
规则读成 `struct Auth` / `struct Data` 数组（以及反向序列化）。

交付内容：

| 产物 | 说明 |
|------|------|
| `lib/libusbauth-configparser.so.1` | 主库（SONAME `libusbauth-configparser.so.1`，`-version-info 1:0:0`） |
| `include/usbauth/usbauth-configparser.h` | 公开头（含 `#include "generic.h"`，同目录） |
| `include/usbauth/generic.h` | 枚举/结构定义（`Parameter`/`Operator`/`Auth`/`Data`） |
| `lib/pkgconfig/libusbauth-configparser.pc` | pkg-config 文件 |

## 上游事实（monorepo @ commit d40b9790）

- 上游是 **monorepo `usbauth-all`**：顶层无独立 tag，本包对应
  `libusbauth-configparser/` 子目录（`configure.ac` 的 `AC_INIT` 版本 1.0.5）。
- 构建系统：**autotools**（`AM_INIT_AUTOMAKE([-Wall foreign])`、`LT_INIT`）。
- 顶层 `Makefile.am`：`SUBDIRS = src data`；**无 `test/` 目录，无
  `TESTS`/`check_PROGRAMS`** → **上游测试用例 0 条**。
- `configure.ac` 里 `PKG_CHECK_MODULES([UDEV], [libudev])`（无
  ACTION-IF-NOT-FOUND）→ 配置期**硬依赖 libudev**。
- `src/Makefile.am`：`BUILT_SOURCES = syn.usbauth_yy.h`、`AM_YFLAGS = -d`，
  `lib_LTLIBRARIES = libusbauth-configparser.la`，
  `..._la_CFLAGS = -include config.h $(UDEV_CFLAGS)`，
  `..._la_LIBADD = $(UDEV_LIBS)`，头装到 `$(includedir)/usbauth`，
  并有 `install-exec-hook: rm -f $(DESTDIR)$(libdir)/*.{la,a}`。
- 源码把配置路径**写死**：`#define CONFIG_FILE "/etc/usbauth.conf"`。

## 依赖

- **eudev/3.2.14**（已上架 ohpcd）：同时满足 configure 的
  `PKG_CHECK_MODULES([UDEV],[libudev])`（其 `pkg_config_name=libudev`）
  与库本体的链接需求（`LIBADD = $(UDEV_LIBS)`，源码调用
  `udev_device_get_parent` / `udev_device_get_sysattr_value`）。
- 工具链自带：`autoconf` 家族与 `flex`/`bison` 在设备
  `/data/service/hnp/bin`（`AC_PROG_LEX`/`AC_PROG_YACC`，与 libpll 同源）；
  `automake`/`libtool` 仓库里没有，故经 `tool_requires` 拉入
  （automake/1.18 + libtool/2.5.4，libpll/abiword 先例）。

## OHOS 适配点

1. **monorepo 包子目录上提**（`source()`）：`get(strip_root=True)` 拿到
   `usbauth-all-<sha>/` 的内容后，把 `libusbauth-configparser/` 里的文件
   上提到源根，autotools 才是自洽的一棵树；补丁路径随之为
   `src/usbauth-configparser.c`。
2. **无 `configure` 的 git 快照**（`build()`）：`autoreconf -fi` 自举
   （`VirtualBuildEnv` 把 tool_requires 的 automake/libtool 注入
   `conanbuild` PATH，`_prepare_autotools_env()` 修正
   `AUTOCONF/AUTOHEADER/AUTOM4TE/SED` 的绝对路径）。
3. **`/etc` 只读**（补丁 0001）：源码写死 `CONFIG_FILE "/etc/usbauth.conf"`，
   而 HarmonyOS 的 `/etc` 是只读 HMFS 挂载。补丁引入一个通用（无平台宏）
   的可覆盖入口：`usbauth_config_file()` 读取 `$USBAUTH_CONFIG`，非空则用之，
   **默认值不变**（chkboot 的 `${VAR:-default}` 同型先例）。
4. **E386**：`autoreconf`/`configure`/`make` 一律
   `env -u CONFIG_SHELL SHELL=/bin/sh`（profile 的
   `CONFIG_SHELL=…/hnp/bash` 在 HMDFS 路径上 getcwd 失败）。
5. **E114**：生成的 `configure` 里 `umask 077` → `umask 022`
   （HMDFS 强制 setgid，0700 的 config.status 临时目录连属主都写不进）；
   `TMPDIR` 指向可写的 build 目录。
6. **E074**：`make -j1`（HMDFS jobserver fifo EPERM）。
7. **`install-exec-hook` 的花括号通配**：`*.{la,a}` 是 bash 专属展开，
   `/bin/sh` 下不展开会静默留下 `.la/.a`，故 `package()` 内按后缀无条件清理。

不改任何 `.c/.h` 的逻辑，只动配置路径常量（补丁 0001，3 个 hunk）。

## test_package（消费者视角）

- `test_libusbauth_configparser`：链接
  `libusbauth-configparser::libusbauth-configparser`，校验
  参数/运算符 string<->enum 映射表、`usbauth_get_param_type` 的值类型图、
  `usbauth_convert_str_to_data`、`usbauth_sub_length` 的 0 夹取，以及缺失
  配置文件时 `usbauth_config_read()` 返回 -1 且 `get_auths` 给出 NULL/0。
- `test_libusbauth_configparser_ohos`（**鸿蒙特有, rule12**）：
  - **H1 `ohos_runtime_resigned_so_loads`**：重签名的
    `libusbauth-configparser.so.1` 在 OHOS 运行时经
    `dlopen(…, RTLD_NOW|RTLD_LOCAL)` 可加载、导出符号可解析
    （SONAME 是 OHOS 加载器的关键字段）。
  - **H2 `ohos_config_parse_roundtrip_via_override_path`**：把一份 5 行规则
    写到可写位置，经 `$USBAUTH_CONFIG` 覆盖路径由 flex/bison **真实解析**
    （`allow all` / `allow idVendor==1234` / `deny …两条属性` / `# 注释` /
    `condition … case …`），逐字段校验 `Auth.type`/`attr_len`/`cond_len`
    与 `Data.param/op/val`，再用 `usbauth_config_write()` 序列化到另一路径并
    读回文本比对 —— 一条完整"写→解析→校验→再序列化→再读回"的端到端链路。
  - 上游既无测试套件，也无这两个路径的任何覆盖。

## 复现

```bash
conan create archives/l/libusbauth-configparser/1.0.5 \
    --profile:host=<ohos-aarch64> --profile:build=<ohos-aarch64>
# test_package 自动运行：
#   ./test_libusbauth_configparser       -> PASS: libusbauth-configparser consumer test OK
#   ./test_libusbauth_configparser_ohos  -> PASS: libusbauth-configparser HarmonyOS cases (H1 runtime load, H2 parse round-trip) ok
```
