# libkdumpfile 0.5.5 — autotools 生成 libtool 缺 echo 定义与 tool_oldlib 未赋值

## 问题

OHOS 上对 autotools 项目执行 `configure` 后，`config.status` 生成的 `libtool`
脚本存在两个缺陷，`make` 在编译/链接阶段直接失败：

1. 参数解析失败：`libtool --tag=CC --mode=compile clang ...` 报
   `X--tag=CC: inaccessible or not found`、`libtool: ignoring unknown tag`、
   `cannot infer operation mode from ...`。
2. 静态库链接失败：`ar cr ...` 成功后 `ranlib` 被无参数调用，打印
   `Usage: ranlib [options] archive` 并 exit 1。

## 根因

生成的 `libtool` 在 config 段只定义了**大写** `ECHO`（如 `ECHO="print -r --"`），
而脚本主体全部使用**小写** `$echo`。`$echo` 展开为空字符串时，参数解析行
`$echo "X$opt"` 实际变成把字面量 `X--tag=CC` 当作命令执行（shell 报
"inaccessible or not found"），随后 mode/tag 全部解析失败。

另一个缺陷：`libtool.m4` 在 RANLIB 非空时向 `old_archive_cmds` 与
`old_postinstall_cmds` 追加 `$RANLIB $tool_oldlib`；但本环境生成的 ltmain 路径
从未给 `tool_oldlib` 赋值（该变量在生成物中无赋值点），于是
`ranlib $tool_oldlib` 变成 `ranlib `（无参调用）。

两者都位于 configure 之后的**生成物** `libtool` 脚本中，不随 tarball 源码分发，
无法用静态 `patches/` 覆盖。

## 方案

在 conanfile.py 的 `build()` 中、`autotools.configure()` 之后、`make` 之前，
对生成 libtool 做两处内联替换（对 source/build 两个候选路径都执行，正则兼容
config 段的转义形态 `\$VAR`）：

1. 在 `^ECHO=.*$` 行后补一行 `echo=$ECHO`（小写 echo 引用已定义的大写 ECHO）；
2. 将 `$RANLIB $tool_oldlib` / `\$RANLIB \$tool_oldlib`（含 `-t` 变体）替换为
   引用 `$oldlib`——该路径下 `$oldlib` 在创建归档时已有值。

找不到文件或模式时记录 warning 不阻断。补丁只改生成物，不入 patches/ 管线。

```python
# conanfile.py build() 内联（参考 libkdumpfile 0.5.5 配方 _patch_libtool）
#   re.sub(r"(^ECHO=.*$)", r"\1\necho=$ECHO", text, count=1, flags=re.M)
#   text.replace("$RANLIB $tool_oldlib", "$RANLIB $oldlib")
#   text.replace("\\$RANLIB \\$tool_oldlib", "\\$RANLIB \\$oldlib")
```

## 验证

- 修补前：`make -j2` 在 `src/addrxlat` 的 `ctx.lo` 编译（libtool X--tag）与
  `libaddrxlat.la` 链接（ranlib 无参）两处失败。
- 修补后：`make -j2` 全绿，生成 `libkdumpfile.so.12.0.0`、`libaddrxlat.so.3.1.4`
  与静态库；conan-verify G2 干净构建 PASS。
- 核验命令：`grep -c "echo=\$ECHO" libtool` ≥1、`grep -c tool_oldlib libtool` =0。

## 适用边界

- 适用于所有在本环境 configure 后生成 libtool 的 autotools 项目（与 E011 的
  config.status 临时目录问题同属"生成物平台缺陷"家族）。
- 仅影响生成物脚本，不影响 tarball 源码；CI 与本地 conan create 均复现。
- 若上游 libtool 版本更新后自带 `echo=$ECHO`/`tool_oldlib` 赋值，补丁自动跳过
  （模式未命中仅 warning）。

## 查重差异

- E011（umask 077 config.status 临时目录）、E052（config.status 临时目录）：
  同属"configure 生成物在 HMDFS/OHOS 的缺陷"，但错误面不同（临时目录权限 vs
  libtool 脚本变量），方案不同（umask/目录 vs echo/ranlib 变量），不构成等价命中。
- E543-draft（libtool link `ar cru` 引号）：不同的 libtool 链接命令形态。
- DRAFT-libftdi（libtool 2.2.6 ECHO/转义三坑）：老版本 ltmain 的 echo 处理，
  与本条目（2.4.7 生成物缺小写 echo 赋值）错误面不同。
