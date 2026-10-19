# util-linux 默认开启型工具无 `--enable-<name>` 选项：`--disable-all-programs` 聚焦构建静默产出空包

Status: DRAFT
Source: util-linux 2.42.2 (mcookie 首次适配)
PR: 【知识库扩展】feat(mcookie): 2.42.2 适配 HarmonyOS PC

## 相关既有条目

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| E402 | gzip CLI 短选项与 toybox 的 `unrecognized option` 运行时行为 | 本草稿是 **configure 脚本的选项注册层**，与 CLI 运行时解析无关 |
| E503 | jshn CLI `--version/--help` 落入 default 分支非 0 退出（L2 门禁） | 同上，运行时 CLI 层；本草稿在 configure 层 |
| E011 | configure `umask 077` 在 HMDFS 建 700 权限临时目录不可写，patch configure 修复 | 同为"patch 生成后的 configure 脚本"这一机制，但问题域不同（文件权限 vs 选项注册）；`similar_to` 引用 |
| DRAFT-util-linux-ts-runsh-ohos-bash-xargs-driver | util-linux 测试驱动器（run.sh/bash/xargs）在 OHOS 的适配 | 本草稿是 **configure 裁剪层**，与测试驱动器不同层；两者组合才是完整聚焦配方 |

检索关键词：`disable-all-programs`、`UL_BUILD_INIT`、`default-on`、`unrecognized options`、`enable-mcookie`。
结论：无既有条目覆盖"autotools 默认开启工具在聚焦裁剪下静默空包"这一机制。

## Scope

- util-linux 2.42.x 中 `UL_BUILD_INIT(<name>, [yes])` 且**未**写 `AC_ARG_ENABLE(<name>)` 的 12 个默认开启工具：
  `isosize`、`mkswap`、`look`、`mcookie`、`namei`、`getopt`、`renice`、`setpgid`、`setsid`、`colcrt`、`colrm`、`rev`。
- 采用 `--disable-all-programs + --enable-<name>` 聚焦单工具配方（uuidgen/lsblk 的既有模式）时必现。
- 对照：`uuidgen`/`lsblk`/`login` 都有显式 `AC_ARG_ENABLE` 注册，因此既有聚焦配方可用——mcookie 是**第一个**撞上此机制的默认开启工具。

## Symptom

真实日志（mcookie 2.42.2 首次本地 W3，2026-10-16）：

```text
configure:51469: WARNING: unrecognized options: --enable-mcookie
...
mcookie/2.42.2: RUN: make -j4
Makefile:10827: Documentation/.deps/test_boilerplate-boilerplate.Po: No such file or directory
make  all-recursive
Making all in po
make[2]: Nothing to be done for `all'.
make[2]: Nothing to be done for `all-am'.
...
mcookie/2.42.2: package(): Packaged 1 file: COPYING
mcookie/2.42.2: Created package revision ...
```

关键事实：

1. `configure` 通过（exit 0），但只递归构建了 `po/`，`misc-utils/` 根本没进 SUBDIRS；
2. `package()` 只有 `COPYING`，`bin/` 目录存在但为空；
3. `conan create` 整体 **exit 0**，构建"成功"——错误被静默吞掉；
4. 交叉编译（macOS→OHOS，`tools.build.cross_building:can_run=False`）下 `test_package` 被 `can_run` 跳过，连消费者测试也发现不了。

## Root Cause

机制链：

1. util-linux `configure.ac` 对默认开启工具只写 `UL_BUILD_INIT([mcookie], [yes])`，**没有** `AC_ARG_ENABLE([mcookie]...)`（对照 `configure.ac:1555` uuidgen 与 `2469` login 都有）；
2. `UL_BUILD_INIT` 宏（`m4/ul.m4`）在 `$2=yes` 分支**不读取 `$enable_<name>`**，只跟随 `$ul_default_estate`：
   ```sh
   if test "x$ul_default_estate" != x; then
     enable_mcookie=$ul_default_estate
     build_mcookie=yes
     if test "x$ul_default_estate" = xno; then build_mcookie=no; fi
   else
     build_mcookie=yes; enable_mcookie=yes
   fi
   ```
3. `--enable-mcookie` 虽被 configure 通用解析臂（`-enable-*|--enable-*`）`eval enable_mcookie=yes`，但该赋值被上一步**覆盖/忽略**；
4. 选项不在 `ac_user_opts` 白名单 → `WARNING: unrecognized options: --enable-mcookie`（`configure:2036` 机制）；
5. `--disable-all-programs` → `ul_default_estate=no` → `build_mcookie=no` → `BUILD_MCOOKIE` 条件不成立 → `misc-utils` 不进 SUBDIRS → 空包。

本质：**"聚焦配方"的前提（目标工具有独立开关）对默认开启工具不成立**，而 configure 只警告不报错，conan 层又只认 exit code，三重静默叠加。

## Recommended Fix / Workaround

推荐（补丁法，`patches/0002-ohos-register-enable-mcookie.patch` 先例，`patch -p1 --forward` 应用）：

1. 在 configure 的 `ac_user_opts` 白名单（`enable_all_programs` 行后）追加 `enable_mcookie`——消除 `unrecognized options` 警告；
2. 将 mcookie 构建状态块改写为：

   ```sh
   if test "x$enable_mcookie" = x; then
     if test "x$ul_default_estate" != x; then
       enable_mcookie=$ul_default_estate
     else
       enable_mcookie=yes
     fi
   fi
   if test "x$enable_mcookie" = xno; then
     build_mcookie=no
   else
     build_mcookie=yes
   fi
   ```

   效果：`--disable-all-programs --enable-mcookie` 现在真正只开 mcookie；无标志时默认开启；`--disable-mcookie` 也能用。

同族 11 个工具（namei/getopt/look/rev/colrm/colcrt/setsid/setpgid/renice/isosize/mkswap）照此各加一行注册即可，一次补丁解决一类问题。

验证（修复后实测）：`grep -c 'BUILD_MCOOKIE_TRUE=' Makefile` ≥ 1，`make mcookie` 产出 `mcookie`，`conan create` 后 `find ~/.conan2/p -path '*/p/bin/mcookie'` 非空，包内仅 `bin/mcookie + licenses/COPYING`。

## Fallback

不传 `--disable-all-programs`：改用 `--disable-<name>` 显式关闭其余带选项工具，接受 12 个默认开启工具全部编译，`package()` 只保留目标二进制。可行但构建集更宽，且 selinux/ncurses/readline 等自动探测依赖可能被意外启用。

## Forbidden Approaches

- `--disable-all-programs + --enable-mcookie`（未打 0002 补丁时）：静默空包，`conan create` 仍 exit 0，交叉编译下完全不可见，合入后才在设备/CI 暴露；
- 以"裁剪失败"为由把 manifest 状态写成 `failed/env_unsupported` 绕过：问题可修，不是环境不支持；
- 只改 `configure.ac` 不重新生成 configure：tarball 用预生成 configure，改 `configure.ac` 不生效。

## Verification

1. 判定层：`grep -c 'AC_ARG_ENABLE(\[<name>\]' configure.ac` 为 0 → 默认开启型；
2. 复现层：修复前 `./configure --disable-all-programs --enable-mcookie` 必现 `unrecognized options` 警告且 `grep -c 'BUILD_MCOOKIE_TRUE=' Makefile` 为 0；
3. 修复层：应用 0002 补丁后上述两项反转，`make mcookie` 产出二进制；
4. 包级：`conan create -pr:h=ohos-local -pr:b=default --build=missing` 后 `find ~/.conan2/p -path '*/p/bin/mcookie'` 非空；`file` 显示 `ELF 64-bit LSB pie executable, ARM aarch64, interpreter /lib/ld-musl-aarch64.so.1`；
5. 测试：上游 `tests/ts/mcookie/mcookie`（1 断言）+ `test_package/test_mcookie.sh`（7 断言，OHOS 目标执行）。

## Prevention

- 新 util-linux 工具聚焦移植前，先查 `configure.ac` 是否有 `AC_ARG_ENABLE`；没有即为默认开启型，直接套 0002 补丁模式；
- 交叉编译场景把"检查 package 的 bin/ 非空"纳入本地 W3 验证清单，不依赖 `conan create` 的 exit code 与 `test_package`；
- 把 `WARNING: unrecognized options` 视为配方正确性信号而非噪音。

## References

- util-linux 2.42.2 `configure.ac`（`UL_BUILD_INIT([mcookie], [yes])` @1956；uuidgen @1555 带 `AC_ARG_ENABLE`；login @2469 带 `AC_ARG_ENABLE`）
- util-linux 2.42.2 `m4/ul.m4`（`UL_BUILD_INIT` 宏定义 @457）
- 仓内先例：`archives/u/uuidgen/2.42.2/`（同 tarball 聚焦配方）、`archives/u/util-linux/2.42/`（裁剪只编库）
- 修复补丁：`archives/m/mcookie/2.42.2/patches/0002-ohos-register-enable-mcookie.patch`
