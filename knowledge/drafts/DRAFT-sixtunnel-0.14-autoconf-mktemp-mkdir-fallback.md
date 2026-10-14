# DRAFT-sixtunnel-0.14-autoconf-mktemp-mkdir-fallback
> OHOS setgid HMDFS 下 Autoconf AS_TMPDIR 的 mktemp -d 生成不可写临时目录：强制 mktemp 失败触发 mkdir fallback 并放宽 umask 077→022

## 问题特征（真实日志片段/标记）

sixtunnel/0.14 真机 preflight 在 compile 阶段稳定失败，HMBS 诊断为 `unsafe_local_mktemp`：


HMBS_PLATFORM_CAPABILITIES={"shell":"/bin/sh","tmpdir":"/storage/Users/currentUser/preflight/clients/cf2d9ed5c070/runtime/sixtunnel-0.14/tmp","jobs":1,"install_shim":true,"hardlink":0,"symlink":1,"chmod":0,"local_mktemp":1}
./confOnfhho/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
sixtunnel/0.14: ERROR:


关键结构化标记：`"chmod":0`（worker 无法把 shim 置为可执行）、`"local_mktemp":1`（使用本地 mktemp）。失败目录名在不同轮次为 `confOnfhho`/`confDlnmeN`/`confCgchio`，均为 mktemp 随机后缀形态；attempt 54606 观察到新失败目录 `conf38156-19156` 属 `conf$$-$RANDOM` 的 mkdir-fallback 形态，说明 `mktemp→false` 已生效但 fallback 自身仍不可写。

## 根因

autoconf 的 `AS_TMPDIR` 逻辑用 `(umask 077 && mktemp -d "./confXXXXXX")` 在当前目录创建 `config.status` 临时目录，随后把 `subs1.awk` 等辅助文件写进去。在 OHOS setgid HMDFS 卷上，toybox `mktemp -d` 的产物被映射成 `drwx--S---`：组位被 setgid 占用且组不可写，连创建者自身也无法写入，于是写 `subs1.awk` 时 EACCES，`config.status` 报 `could not setup config files machinery`。

三条错误路径被逐轮证伪：

1. PATH-prepend `mktemp` wrapper（attempt 16934/54290）失败——该 worker `HMBS_CAP_CHMOD=0`，shim 文件以 0644 落盘，PATH 查到也因非可执行被跳过。
2. 只改 configure 的 `umask 077`→`022`（attempt 16989）失败——`mktemp -d` 会自行 `chmod(0700)`，忽略外层 umask。
3. 只把 `mktemp -d` 改为失败（attempt 17003/54564）——fallback 分支是 `(umask 077 && mkdir)`，在 setgid HMDFS 上仍产出不可写的 `drwx--S---`。

最终 attempt 54606 同时做两件事才通过：让 `mktemp -d` 确定性失败走 mkdir fallback，并放宽 fallback 的 `umask 077`→`022`。

## 修复方案（rec）

1. 在 `archives/s/sixtunnel/0.14/conanfile.py` 新增 `_patch_configure_for_ohos()`，对 source/build 树内所有 `configure` 幂等改写。
2. 将 `mktemp -d "./confXXXXXX"` 替换为 `false`，强制 autoconf 走内置 `|| mkdir` fallback，使临时目录名变为确定性的 `conf$$-$RANDOM` 形态。
3. 将 `umask 077` 替换为 `umask 022`（a52dec/qprint/inn2 同款已验证方案），使 mkdir fallback 建出的目录保持组可写，避开 `drwx--S---`。
4. 由于 AS_TMPDIR 块会被嵌入生成的 `config.status`，一次改写同时覆盖 configure 阶段与 `config.status` 阶段，无需依赖 chmod、PATH shadow 或 mktemp 运行期行为。
5. 去掉 `HMBS_AUTOCONF_MKTEMP_FALLBACK` 环境门控，无条件幂等应用补丁，避免门控值不精确命中导致补丁根本不执行。
6. 本地校验：真实 tarball 的 `configure` 中 `mktemp -d` 1→0、`umask 077` 2→0、`umask 022` 0→2；执行 `./configure` 与 `./config.status` 均 rc=0 并生成 Makefile。
7. 真机复跑后补齐非本主题门禁项：`test_package/`（真实执行打包的 `6tunnel -V` 并输出 `HMBS_TEST_PACKAGE_RESULT`，attempt 17075）与 `archives/s/sixtunnel/commands.json`（attempt 47601）。

## 禁止策略

禁止只放宽 `umask 077`→`022` 而保留真实 `mktemp -d`，也禁止依赖 PATH-prepend `mktemp` wrapper。前者因 `mktemp -d` 自行 `chmod 0700` 忽略 umask 而无效；后者在 `HMBS_CAP_CHMOD=0` 的 worker 上因 shim 不可执行而无效。二者都会让 `config.status: error: could not setup config files machinery` 原样复现。

## 与相近条目的边界（查重）

与 buildtorrent 类条目（`DRAFT-buildtorrent-0.0.0-umask-077-chmod-hmdfs`）的边界：那条只覆盖 umask/chmod 侧，把 `umask 077` 放宽即可解决；本条额外覆盖 `mktemp -d` 自身 `chmod 0700` 与 setgid HMDFS 组位不可写（`drwx--S---`）的组合内核——单改 umask 不够，必须先让 `mktemp -d` 失败以触发 mkdir fallback，再放宽 fallback 的 umask。查重命中的 `HMBS_PLATFORM_CAPABILITIES`/`hmbs_cap_chmod` 通用样板行不构成本条内核的重复。

## 适用判断

当真机 compile 日志出现 `config.status: error: could not setup config files machinery` 且伴随 `confXXXXXX/subs1.awk: Permission denied`，且环境标记含 `"local_mktemp":1`、构建目录位于 setgid HMDFS 卷时，优先采用本条目：先确认 `configure` 中 AS_TMPDIR 使用 `mktemp -d`，再套用 `mktemp→false` + `umask 077→022` 的双改法。若无法改写 `configure`，可退回把 AS_TMPDIR 重定向到可写 TMPDIR，但需预期部分 HMDFS worker 上权限仍可能复发。
