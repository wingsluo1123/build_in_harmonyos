# fonttosfnt

**X.Org BDF/PCF → sfnt（OpenType）位图字体封装工具**（X.Org Foundation，MIT）

`fonttosfnt` 把一个（或一组）BDF/PCF 点阵字体**包进 sfnt 外壳**，产出 `.otb`
（OpenType Bitmap）文件 —— 也就是"看起来是 TrueType/OpenType、内容仍是点阵位图"的字体。
上游 `README` 原文一句话概括：*wraps a set of bdf or pcf bitmap fonts in a sfnt
(TrueType or OpenType) wrapper*。读侧走 FreeType 的 BDF/PCF 驱动，写侧自己拼
`EBDT/EBLC/cmap/glyf/head/hhea/hmtx/loca/maxp/name/post` 等表并回填校验和。

## 用法

```bash
fonttosfnt [ -v ] [ -c ] [ -b ] [ -r ] [ -g n ] [ -m n ] -o font.otb [ -- ] [ font ] ...
fonttosfnt --help | --version
```

| 形态 | 行为 |
|------|------|
| `fonttosfnt -o out.otb in.bdf` | 主用法：`-o` **是必填选项**；缺它报 `Missing required -o option` + usage、退出码 1 |
| `fonttosfnt -o out.otb < in.bdf` | 不给位置参数时从 **stdin** 读 BDF（man 页语义） |
| `-v` / `-c` / `-b` / `-r` | 详细输出 / 不裁剪字形 / 写字节对齐位图数据 / 不重编码为 Unicode |
| `-g n` / `-m n` | 可缩放字形 / 可缩放度量的写入方式（`-g 0` = 不写可缩放字形，表目录随之少 `glyf`/`loca`） |
| 任意未知参数 | `Unknown argument: …` + usage，**退出码 1** |
| `--version` | 打印 `fonttosfnt 1.2.5`（`PACKAGE_STRING`），退出码 0 |

⚠ 与流式过滤器不同：`-o` 目标会被 `fopen(filename, "wb+")` 打开并 `fseek` 回填表校验和，
因此**必须给一个可 seek 的真实文件**（不能像 `bdftopcf` 那样用 `-o /dev/null` 规避落盘）。

本包提供命令行工具 `fonttosfnt`（+ man 页），不含库与头文件（见 `commands.json`）。

## 依赖

`configure.ac` 只有一行依赖声明：

```
PKG_CHECK_MODULES(FONTTOSFNT, [xproto >= 7.0.33 freetype2 fontenc])
```

| 模块 | conan 包 | 用途 |
|---|---|---|
| `xproto` | `xorgproto/2025.1` | X11 协议头（`X11/Xos.h`） |
| `freetype2` | `freetype/2.14.3.2.1` | read.c 用 FreeType BDF 驱动读 BDF/PCF |
| `fontenc` | `libfontenc/1.1.7` | read.c 用 `FontEncMapFind`/`FontMapReverse` 重编码 |

⚠ `libfontenc` 钉 **1.1.7**：仓内 `archives/l/libfontenc/1.1.9` 已归档但**未发布到 ohpcd**
（`conan download --only-recipe` 对"未发布版本"与"不存在的名/版本"返回同一条远程错误，
需用控制探针区分）。

## 构建系统

上游 tarball 是标准 autotools 树，且**自带生成好的 `configure`**（无需 `autoreconf`）。
本仓走 autotools：设备与 CI 均具备。

## OHOS 适配要点

详见版本级 `notes.md`、`1.2.5/manifest.yaml` 的 `ohos_adaptation`。摘要：

1. **`config.guess` 不识 `uname -s = HarmonyOS`**（本包时间戳 2024-07-27）⇒ 补
   `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos`（E007/E072）。
   ⚠ 本包是**新版 `GUESS=` 变量式**写法（分支只赋值、不 `exit`），与 `bdftopcf` 的 2017
   老版（`echo <tuple>; exit ;;`）**不可互抄**。
2. **本包 `config.sub` 无需补** —— tarball 自带新版，已含 `ohos*`/`linux-ohos*` 两处
   （实测 `config.sub aarch64-unknown-linux-ohos` rc=0）⇒ 只 patch `config.guess` 一件，
   **不能照抄 bdftopcf 的三件套**。
3. **`umask 077 && mktemp -d` 在 HMDFS 上建 700 不可写目录**（E011/E114）⇒ `config.guess`
   的 `set_cc_for_build`（3 处）与 `configure` 的 config.status 临时目录（2 处）都放宽到 `022`。
4. **不注入平台宏**（R8/PF5）：全文无 `__OHOS__` 字面量，只按 `uname -s` 名识别 OS。
5. **不采用 `--build/--host` 绕过** `config.guess`：本包 `configure.ac` 的
   `AC_CHECK_FUNC(setenv)` / `AC_CHECK_FUNCS(vasprintf)` / `AC_CHECK_DECLS(va_copy)`
   在交叉模式下语义会变、`config.h` 会错。改用"native 构建 + 补 `config.guess`"。
6. **`AutotoolsDeps` 注入的 `-L/-l` 会让 autoconf 的 conftest 链接 conan 共享库** ⇒
   `Error loading shared library libfontenc.so.1 (needed by ./conftest)` → `cannot run C
   compiled programs`。修法：`generate()` 把依赖 libdir 前置进 build scope 的
   `LD_LIBRARY_PATH`（同签名先例 `xdriinfo/1.0.8`）。
7. **⚠ 环境坑（非配方）**：设备 `sed` 是 **toybox 0.8.12**；CONAN_HOME 路径若含非 ASCII
   字节，autoconf 2.72 的 config.status 生成器会挂（`could not make ./config.status` /
   `gawk: unterminated string`）。换成纯 ASCII CONAN_HOME 后一次通过，**未为此加补丁**。

## 测试

- **上游测试资产 0**（§12.72 四口径就地清点全部为 0；`Makefile.am`/`man/Makefile.am` 无
  `TESTS`、无 `check_PROGRAMS`；`configure.ac` 无测试宏）。`make check` 在配方 `build()` 内
  **真实执行**：`man/` 报 `Nothing to be done for 'check'`，rc=0（空转）。
- `test_package/test.sh` 提供 **16 条**消费者断言，实测 **`16/16 checks PASS`**：
  真实 BDF→`.otb` 转换 + sfnt 结构解析（版本号 `00010000`、`numTables=13`、13 个表 tag 齐备、
  `head` magic `5F0F3CF5`）+ `-g 0 -m 0` 差分断言 + 7 条 CLI/错误路径断言。
  产物写进 `$TMPDIR` 的 `mktemp -d` 并退出即删，不落 `test_package/`。
