# OHOS 上 `grep` 可能是 toybox 版：对二进制文件默认跳过，`-a` 无效

> Draft: `DRAFT-XDRAWCHEM-1111-TOYBOX-GREP-BINARY-SKIP`
> Stem: `xdrawchem-1.11.1-toybox-grep-binary-skip` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-XDRAWCHEM-1111-TOYBOX-GREP-BINARY-SKIP
- **严重度**: 2
- **类别**: testing|ohos-platform|toolchain|path
- **触发工具**: conan|bash|grep|toybox
- **阶段**: testing

## 现象

test_package 里一条"断言二进制 DT_NEEDED 含 Qt5Widgets / libopenbabel"的用例：

```
  PASS  TC-03-ohos-aarch64-elf-runs-on-device
    got: 
    got: 
  FAIL  TC-04-links-qt5widgets-and-openbabel
```

- 在 `conan create` / `conan test` 下**恒 FAIL**，且失败诊断（`$(grep -ao ... )`）**也是空的**；
- 把同一条命令在开发者交互 shell 里手敲，**立刻 PASS**；
- 在 test_package 里插一行 `command -v grep` 后真相大白：

```
DBG PATH=/storage/.../p/bin:/storage/.../qt5-.../bin:/system/bin:/usr/bin:/bin:...:/data/service/hnp/bin:...
DBG grep=/system/bin/grep
grep --version  →  toybox 0.8.12 (is not GNU grep 9.0)
```

## 根因

OHOS 上同时有两套用户态工具：

| 位置 | 实现 | 说明 |
|---|---|---|
| `/system/bin/grep` | **toybox 0.8.12** | 系统自带，体量小、无 GNU 扩展 |
| `/data/service/hnp/bin/grep` | GNU grep 3.12 | HNP 工具链自带 |

- 交互 shell 的 PATH 通常把 HNP 放前面（conan profile 的 `[buildenv] PATH` 也是
  `+(path)/data/service/hnp/bin`），所以手动跑时用的是 **GNU grep**；
- 而 `conan test` / `conan create` 的 test_package 运行环境里 `/system/bin` 排在
  `/data/service/hnp/bin` **之前**，`grep` 命中 **toybox**。

toybox grep 对**二进制文件默认跳过**（不会像 GNU 那样打印 "Binary file … matches"），
`-a` 也不生效。实测：

```bash
$ /system/bin/grep -q  libQt5Widgets <elf>; echo rc=$?   # rc=1（文件里确实有！）
$ /system/bin/grep -aq libQt5Widgets <elf>; echo rc=$?   # rc=1
$ /system/bin/grep -ao 'libQt5[A-Za-z]*\.so\.[0-9]' <elf>   # 无输出
$ /data/service/hnp/bin/grep -ao 'libQt5[A-Za-z]*\.so\.[0-9]' <elf> | sort -u
libQt5Core.so.5
libQt5Gui.so.5
libQt5Widgets.so.5
...
```

**危险点**：失败是"静默"的——断言恒假、诊断也为空字符串，看起来像偶发抖动；
而交互 shell 复现永远成功，很容易被误判为"环境不稳"而放过。

## 修复

断言**二进制内容**时不要用 `grep`，改用 `tr` 去 NUL + bash 内建 `case`：

```bash
BIN_TEXT="$(tr -d '\000' < "$XDRAW")"     # toybox tr 可用，行为与 GNU 一致
HAS_QT5=no; case "$BIN_TEXT" in *libQt5Widgets.so.5*) HAS_QT5=yes ;; esac
HAS_OB=no;  case "$BIN_TEXT" in *libopenbabel.so.8*)  HAS_OB=yes  ;; esac
```

- 零外部依赖、与 PATH 无关；2,587,264 字节（≈2.5 MB）的二进制实测 < 0.2 s。
- 顺带在脚本里保留 `command -v grep` 之类的环境自证，让同类差异"可诊断"而不是"空输出"。

> 若必须用 grep：用绝对路径 `/data/service/hnp/bin/grep`，但这把工具链路径写进了测试脚本，
> 跨环境不成立，只作兜底。**不要**为了走 GNU 版而把 conan 缓存路径塞进 PATH/LD_LIBRARY_PATH。

## 同类风险面

任何在测试/CI 脚本里用 `grep` 扫**二进制**的断言都可能中招：DT_NEEDED、DT_RUNPATH/rpath、
内嵌版本串、内嵌路径、符号表检查。**文本文件**（YAML/py/sh）不受影响，`grep` 可照常用。
