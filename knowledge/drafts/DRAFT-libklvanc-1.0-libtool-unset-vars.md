# libtool 生成脚本引用未赋值变量（$echo 空 / $tool_oldlib 空）

- **库**: libklvanc 1.0
- **阶段**: compilation/configuration/packaging
- **严重度**: 2
- **类别**: platform, autotools, libtool, hmdfs

## 问题

OHOS/HMDFS 环境下，config.status 从 ltmain.sh 生成的 libtool 脚本存在两个未赋值变量问题：

1. 脚本仅给大写 `ECHO` 赋值（`"print -r --"`），小写 `$echo` 从未赋值。选项解析中
   `` optarg=`$echo "X$arg" | $Xsed ...` `` 退化为把参数文本当作命令执行，报
   `X--tag=CC: inaccessible or not found` 与 `libtool: cannot infer operation mode from 'clang'`。
2. `old_archive_cmds` / `old_postinstall_cmds` 引用 `$tool_oldlib` 而脚本未定义该变量，
   归档阶段 `` $RANLIB $tool_oldlib `` 变成无参 ranlib，打印 `Usage: ranlib [options] archive` 后失败。

与 E011/E110/E125（mktemp umask 077 权限）常同时出现，但本条目是脚本变量缺失，并非权限问题。

## 根因

旧式 ltmain.sh 生成的 libtool 脚本中，小写 `$echo` 赋值缺失（仅大写 ECHO），且
旧版 old_archive_cmds 采用 `$tool_oldlib`（需新版 ltmain.sh 的
func_convert_file_to_tool 赋值）而当前生成路径未提供该赋值。

## 方案

在生成的 libtool 脚本中：

1. `ECHO` 定义后补一行 `echo="print -r --"`（与大写 ECHO 同值，/bin/sh 支持 print 内建）。
2. 将 `old_archive_cmds` 与 `old_postinstall_cmds` 中的 `$RANLIB $tool_oldlib`
   改为 `$RANLIB $oldlib`（$oldlib 在链接/安装模式均已赋值，对齐 cconv 等可构建项目写法）。

```bash
sed -i 's|^ECHO="print -r --"|ECHO="print -r --"\necho="print -r --"|' libtool
sed -i 's|\$RANLIB \$tool_oldlib|\$RANLIB \$oldlib|g' libtool
```

## 验证

- `make -j1` → exit 0（全部 CCLD 通过）
- `make install DESTDIR=$TEST_PREFIX` → exit 0（32 个产物落盘）

## 适用边界

所有 autotools + libtool 项目在 OHOS/HMDFS 下生成 libtool 后执行 make /
make install 的场景；与 E011/E110/E125（mktemp umask 077）常同时出现。

## 反例与限制

- 新版 ltmain.sh（含 func_convert_file_to_tool 赋值 tool_oldlib 的版本）不会触发。
- conan create 干净构建走 automake/1.18 + libtool/2.5.4 tool_requires 的
  autoreconf 引导时不触发（该路径由 E528 recipe-local-ohos-autotools-env-closure 覆盖）。
- 本修复是针对生成脚本的临时修改，重新 configure 会覆盖，需纳入 patches 或
  在构建脚本中重复应用。

## 证据

| 命令 | 退出码 |
|------|--------|
| make -j1 | 0 |
| make install DESTDIR=... | 0 |

修复前日志：adapt-make.log（X--tag / ranlib Usage 失败）；修复后全部编译/安装通过。