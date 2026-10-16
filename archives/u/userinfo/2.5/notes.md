# userinfo 2.5 适配笔记

## 编译环境
- 构建系统: autotools（release 自带预生成的 `configure` + `Makefile.in` + libtool）
- 编译日期: 2026-10-15
- 编译器: OHOS SDK clang（`tools.build:compiler_executables`）
- 状态: built

## 编译步骤

1. `source()`：取 Debian 同版本 `.orig.tar.bz2`（HTTPS 镜像，sha256 固定），
   `get(..., strip_root=True)` 解压。
2. `apply_conandata_patches()`：打 1 个补丁（configure 的 umask）。
3. `build()`：`sh ./configure --build/--host/--target=aarch64-unknown-linux-gnu
   --program-prefix= --prefix=<pkg>`，`touch` 生成文件避免 maintainer 模式重生成，
   再 `make -j1`。
4. `package()`：`make install` 装 `bin/ui`、`lib/userinfo/{passwd,mail,login}.so`、
   `share/man/man1/ui.1`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.status` 建 `./confXXXXXX/subs1.awk` 报 `Permission denied` | autoconf 用 `(umask 077 && mktemp -d ./confXXXXXX)` 建临时目录（模式 0700）；HMDFS 拒绝在 group/other 无 x 位的目录里创建文件 | 补丁 0001 把 configure 中两处 `umask 077` 改为 `umask 022` |
| 2 | 安装后程序名变成 `aarch64-unknown-linux-gnu-ui` | `AC_CANONICAL_TARGET` 因显式 `--target` 给程序名加 triplet 前缀 | configure 加 `--program-prefix=` |
| 3 | 老 `config.guess`/`config.sub` 不认 HarmonyOS | `build/` 里的辅助脚本年代久远 | 显式传 `--build/--host/--target=aarch64-unknown-linux-gnu` |
| 4 | `make` 触发 `aclocal-1.14` 重生成并失败 | `configure.ac` 的 mtime 比 `aclocal.m4` 新 | `touch aclocal.m4 configure ... Makefile.in` 使生成文件比源新 |

## 依赖版本

无三方依赖（仅 libc）。模块通过 libtool 构建为 `.so`，用 RUNPATH 定位。

## 验证结果

```bash
# 上游测试：无（N=0，无 check/ctest/tests/）
# 消费者（test_package/test_userinfo.sh）
USERINFO_CHECK_SUMMARY checks=23 fails=0
```

## 注意事项

- `ui` 依赖 RUNPATH 定位 `lib/userinfo/*.so`；配方以 `--prefix=<package_folder>`
  配置，使 RUNPATH 直接指向最终包目录。
- OHOS 无 utmp/lastlog：`login.so` 会打印 `/dev/null/utmp`、`/var/log/lastlog`
  之类的警告，但模块仍正常执行并输出字段（`:!:` 表示未知）。
