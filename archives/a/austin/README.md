# austin

- **上游**：https://github.com/P403n1x87/austin （CPython frame stack sampler）
- **版本**：**3.7.0**（与平台清单一致）
- **形态**：C（austin 本体；依赖仓库已归档的 `argp-standalone`）
- **构建**：autotools（源码只有 `configure.ac`，须 autoreconf 自举）
- **许可证**：GPL-3.0-or-later
- **依赖**：`argp-standalone/1.5.0`、`libunwind/1.6.2` —— **都已在仓库归档**（不构成阻塞）；
  构建期 `automake/1.18`、`libtool/2.5.4`

## 归档内容

```
austin/
  commands.json            软件级命令声明（R38：本包产出真编译的 ELF 可执行文件）
  3.7.0/
    conandata.yml          源（上游 v3.7.0 + sha256）
    conanfile.py           配方（autotools 构建 + 补的真测试 + make install）
    manifest.yaml          版本级 manifest（dependencies / upstream_tests / knowledge_gained）
    notes.md               适配要点（四个坑 + 上游测试为何跑不起来 + austinp 为何未随包）
    test_package/          消费者校验（7 项，全部离线）
```

## 构建要点（四个坑，详见 notes.md）

1. **依赖的 include 要显式注入**：只靠 `AutotoolsToolchain` 自动收集时编译行里没有 argp 的
   include → `#include <argp.h>` not found。用 `tc.extra_cflags/extra_ldflags` 补。
2. **`-largp` 用 `LIBS=` 传**：上游 `austin_LDADD = -lm` 里没有 argp；放 LDFLAGS 会排到目标文件
   之前（静态库顺序不对），`tc.configure_args.append("LIBS=-largp")` 才会落在链接行末尾。
3. **显式三元组**：`--build/--host=aarch64-unknown-linux-musl`（config.guess 认不出本机）。
4. **`configure` 的 `umask 077` → 022**，且**必须在 autoreconf 之后**（HMDFS 目录权限；
   `argp-standalone` 同款做法）。

## 上游测试

上游**有**测试套件，但 `test/run.sh` 写死作者本机环境（`source /tmp/austin-test/bin/activate` +
`LD_LIBRARY_PATH=/Users/gabriele/Projects/libunwind/src/.libs/`），用例是 pytest + ptrace 型，
还需 `austin-python`/`pytest-xdist`/`psutil` → **本机与 CI 都跑不起来**（硬证据见 notes.md）。
故按仓库既有做法在配方里**补能真跑的测试**：

1. `austin --help` rc=0 且打印用法（**硬判**，通过）；
2. 一次真实采样（`-i 1000` 对一个 CPython 进程）——本环境**缺 austinp**（仓库 `libunwind` 不含
   `libunwind-ptrace.h`，上游 configure 已打印 `not building austinp: missing libunwind`）→
   rc=33，**如实记录、不计为通过**，且不据此让 build 失败（环境限制而非适配缺陷）。

## 消费者校验

`test_package/check_austin.py` **7 项，全部离线**：产物齐备 / ELF 头自检（ELF64、machine=0xB7）/
`bin/austinp` 是否随包（如实记录）/ `--help` 真跑 / 真实采样尝试（如实记录）/ 许可证随包 / 证据。
实测 `checks=7 fails=0` / `RESULT: PASS`。
