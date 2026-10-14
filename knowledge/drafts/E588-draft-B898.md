# E588 — Orc configure.sh 构建期执行 config.sed/mkversio：x86 runner 上 AC_SUB 静默失败

## 错误特征

`configure.sh` 退出码 0、末尾照常打印 `generating Makefile`，但 `make` 立刻失败：

```
make: CC@: No such file or directory
make: *** [<builtin>: blockio.o] Error 127
```

真正的错误只在 `config.log` 里：

```
generating config.sed
aarch64-binfmt-P: Could not open '/lib/ld-musl-aarch64.so.1': No such file or directory
aarch64-binfmt-P: Could not open '/lib/ld-musl-aarch64.so.1': No such file or directory
...
```

生成的 `Makefile` 残留占位符（levee 实测 12 个）：`CC=@CC@`、`CFLAGS=@CFLAGS@`、`@LIBS@`……

## 触发条件

- 项目使用 David Parsons 的 `configure.sh` + `configure.inc`（shell 版 autoconf 模拟器；discount、levee 等）
- 在 x86_64 runner 上以 OHOS profile 构建（W3 / conan-verify 的 `-pr:h=-pr:b=ohos-aarch64`，
  编译器是交叉 clang，产物为动态链接的 AArch64 ELF）
- runner 注册了 qemu-aarch64 binfmt，但没有 `/lib/ld-musl-aarch64.so.1`（也不应该有）

## 根因分析

`configure.inc` 没有「构建机编译器」概念，只有一个 `$CC`：

1. `__ac_config_sed` 用 `$AC_CC -o config.sed ngc$$.c`（**只带 CC**，不带 CFLAGS/LDFLAGS）编译一个
   做 sed 转义的小程序，之后**每一次** `AC_SUB` 都执行 `./config.sed` 往 `config.sub` 里写替换规则；
2. 项目自己的 Makefile 还会编译并执行辅助程序（levee 的 `mkversio` 生成 `version.c`）。

在设备上原生构建（CI）时这些程序直接运行；在 x86 上它们是动态链接的 AArch64 程序，binfmt 交给
qemu-aarch64 后找不到 musl 动态加载器而失败。`AC_SUB` 不检查返回值，`config.sub` 为空，
`AC_OUTPUT` 仍然“成功”生成 Makefile——失败被推迟到 make 执行 `@CC@` 时才暴露，离根因很远。

## 解决方案

### 推荐方案：把编译器驱动为 `<cc> -static-pie`

```python
cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")
env = {
    "CC": f"{cc} -static-pie",          # 必须在 CC 里：config.sed 只用 $CC 编译
    "CFLAGS": "-O2 -fPIE -I<dep>/include",
    "LDFLAGS": "-L<dep>/lib",
    "LIBS": "-l<dep>",
}
self.run(" ".join(f"{k}={shlex.quote(v)}" for k, v in env.items()) + " bash ./configure.sh ...", cwd=src)
self.run("make -j1", cwd=src)
```

- `config.sed`、`mkversio` 与最终交付物都成为**无 PT_INTERP 的 static PIE**：x86 上经 qemu-aarch64
  binfmt 可执行，AArch64 设备上原生可执行，W3 与 CI 同一份配方；
- 交付物保留 PIE + `BIND_NOW` + full RELRO + 不可执行栈（`llvm-readelf -lhd` 实测）；
- 依赖需有静态形态（本仓 ncurses 等系统同名库按 R26 本就是静态）；
- 副作用：每个 `-c` 编译会多一条 `argument unused during compilation: '-static-pie'` 警告，无害。

先例：ren 1.0（纯 libc 工具以 `-static-pie` 交付，test_package 在 x86 经 qemu 执行打包产物）。

### 回退方案

依赖只有动态形态、无法 static-pie 时：本地只做到交叉编译+链接，把「构建期需执行目标产物」如实记录为
x86 runner 的环境边界，由设备 CI 原生执行（同 libkcddb 草稿的 detect-and-delegate-to-ci 思路）。

### 禁止做法

- ❌ 手工 `sed` 替换 Makefile/config.sub 里的 `@CC@` 等占位符：改生成文件（R6），且 `config.h` 的探测
  结果同样依赖 configure 正常运行。
- ❌ 设置 `QEMU_LD_PREFIX` 或往构建机 `/lib` 放 `ld-musl-aarch64.so.1`：binfmt P 模式下前者不生效，
  后者污染构建机且与 CI 不一致。

## 验证

```bash
grep -c '@[A-Z_]*@' Makefile                # 修复后应为 0
grep 'Could not open' config.log             # 修复后应无输出
file mkversio                                # make 后为 "static-pie linked"（config.sed 在 AC_OUTPUT 末尾被删除）
```

## 适用边界

- 适用：构建期执行自身编译出的目标程序、且只接受单一 `$CC` 的构建系统（Orc configure.inc 为典型）。
- 不适用：autoconf 的 `AC_TRY_RUN` 类探测（有交叉分支/缓存变量可用，见 E543）；需要宿主工具
  （如 Qt moc）的场景（宿主与目标必须分离，见 libkcddb 草稿）。

## 参考

- 实例：`archives/l/levee/4.0/conanfile.py`（`build()` 中的 configure_env）
- 查重：知识库无 `config.sed`/`configure.inc`/`static-pie` 相关条目；E543 覆盖 autoconf AC_TRY_RUN，不覆盖本机制
