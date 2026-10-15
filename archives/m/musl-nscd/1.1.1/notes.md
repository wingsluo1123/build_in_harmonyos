# musl-nscd 1.1.1 适配笔记

## 编译环境

- 构建系统: makefile（musl 风格手写 `configure` + 顶层 `Makefile`，**非 Autotools**）
- 编译日期: 2026-10-14
- 平台: HarmonyOS / OHOS 6.0，aarch64（armv8），**原生编译**（非交叉编译）
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`）
- 状态: built

## 语言预检（R47）

```text
python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight musl-nscd 1.1.1 \
    --src <源码目录> --lang c
→ 语言匹配: task=c, detected=c        (exit 0)

expected        = c
detected_language = c
language_evidence:
  build_system  = "make"
  manifest      = "顶层 Makefile（无更强 manifest）"
  source_stats  = "源文件 15 个（c:15, bash:2），主体占比 100%"
```

## 上游测试清点（R51 第 1 步）

| 检查项 | 结果 | 证据 |
|--------|------|------|
| `make check` 目标 | **不存在** | `grep -nE '^check\|^test\|check:' Makefile` → 无命中（exit 1） |
| `ctest` / `pytest` / `meson test` | 不存在 | 归档内无 `CMakeLists.txt`、无 `tests/` 目录、无测试框架注册 |
| `port/*.c` 的性质 | **编译期特征探针，非测试** | `port/{gr_passwd,pw_gecos,pw_passwd}.c` 内容均为 `#ifdef TEST ... #else typedef int x; #endif`；Makefile 的 `obj/test/%` 规则以 `-DTEST` 编译它们，`tools/gen_config.sh` 再按「`obj/test/port/<name>` 文件是否非空」生成 `obj/include/config.h` 的 `HAVE_<NAME>` 宏；探针**只编译不运行** |
| 上游测试用例数 | **0** | — |

> `obj/test/%` 规则带 `|| cat </dev/null >$@` 兜底：探针编译失败会被**静默**写成空文件，
> 对应宏退化为 `#undef`，构建不报错。因此配方 `build()` 额外校验「探针产物」与
> 「生成的宏」严格一致（`obj/include/config.h` 中 `#define HAVE_X 1` ↔ 探针文件非空，
> `#undef HAVE_X` ↔ 探针文件为空），确保 `pw_passwd` / `pw_gecos` / `gr_passwd`
> 这三个 ABI 特征在本平台真的探测过，而不是静默退化。

## 编译步骤

上游是 in-source 构建：`configure` 在源码目录写 `config.mak`，`make` 在源码目录生成 `obj/`。

```bash
# 配方 build() 实际执行的命令（cwd = 源码目录）
sh ./configure --prefix=/ CC=<tools.build:compiler_executables:c>
make -j1
# 上游验证：探针产物 ↔ config.h 宏一致性
# （package() 阶段）
make install DESTDIR=<package_folder>
```

- **R1 参数最小化**：自研 `configure` 只需 `--prefix`。用 `--prefix=/` 让
  `sbindir`/`includedir`/`mandir` 落在包根下，安装期用 `DESTDIR` 隔离到
  `package_folder`，从而精确控制打包内容（`sbin/nscd`、`include/nss.h`、
  `share/man/man8/musl-nscd.8`）。
- **R9 `-j1`**：并行 make 在 HMDFS 上会踩 jobserver fifo EPERM。
- **R33**：Makefile 直接用 `$(CC)`，自研 `configure` 只认 `CC=` 变量，
  Conan Toolchain 无法注入编译器。配方在 `generate()` 中从
  `tools.build:compiler_executables` 取 `CC`/`AR`/`RANLIB` 并写入 conanbuild
  env 脚本，不依赖 shell 里的 `$CC`/`$CFLAGS`（release worker 上可能为空）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` / `conan-init` 把构建系统猜成 `autotools`，生成的配方套用了 Autotools 模板（`autotools.configure()` + `--enable-static/--disable-shared` + `package_type = "library"`） | 上游有名为 `configure` 的脚本，启发式据此判为 Autotools；实际无 `configure.ac`/`Makefile.in`，是 musl 风格手写 configure + Makefile | 按 ADAPTATION_GUIDE §2 决策树人工纠正为 makefile 项目，重写配方（`sh ./configure` + `make`，`package_type = "application"`）。注意上游 `configure` 对未知的 `--enable-*`/`--disable-*` 是**静默忽略**，套错模板不会报错只会少传参数，属隐性坑 |
| 2 | `conan-init` 生成的 `test_package/` 是空壳（`printf("test ...: OK")` + `CMakeLists.txt` 链接不存在的库） | 模板按「库」类型生成 | 重写为消费者端到端测试：桩 NSS 模块 + NSCD 协议客户端 + 真实启动守护进程 |
| 3 | 上游无任何测试套件 | Makefile 无 check/test 目标 | 按 R51 清点留证（见上表）+ 补全 32 项端到端断言；配方 `build()` 增加探针一致性校验 |
| 4 | 守护进程默认读 `/etc/nsswitch.conf`、绑 `/var/run/nscd/socket` | 上游硬编码默认路径 | 测试与部署均用 `-c` / `-s` / `-p` 改道到 `$TMPDIR` 下的临时目录 |

## 源码修改

**无补丁**。上游 v1.1.1 在 OHOS 上开箱可编译：零外部依赖、纯 POSIX C，
OHOS libc 为 musl 派生，与上游设计目标一致。

## 依赖版本

无外部依赖。`configure` 会自探测 `-lpthread` / `-ll` / `-ly` / `-lxnet` / `-ldl`，
OHOS 上 `-ll` 与 `-ly` 不存在，会被自动跳过（仅 yacc/lex 重新生成语法分析器时才需要，
而归档内已带 `dist/` 预生成源）。

## 验证结果

```bash
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

- 编译状态: 通过
- 上游测试: 无（上游无测试套件，已在 MANIFEST.yml 声明并留清点证据）
- 补全测试: 32/32 通过（`test_package/test.sh` 的端到端用例）
- 交付物: `sbin/nscd`、`include/nss.h`、`share/man/man8/musl-nscd.8`、`licenses/COPYRIGHT`

## 交付物

| 文件 | 说明 |
|------|------|
| `sbin/nscd` | NSCD 协议守护进程 |
| `include/nss.h` | NSS 模块 API 头（`enum nss_status`） |
| `share/man/man8/musl-nscd.8` | 手册页 |
| `licenses/COPYRIGHT` | 上游 MIT 许可证原文 |

## 注意事项

- 上游 `configure` 不是 Autotools：未知的 `--enable-*` / `--disable-*` / `--with-*`
  **静默忽略**，参数写错不会报错，只会悄悄少传。
- 部署时 `nsswitch.conf` 中配置的服务名必须对应系统上真实存在的
  `libnss_<service>.so.2`；OHOS 默认不带任何 NSS 模块，`nscd` 在 `dlopen` 失败时
  会直接退出。
- `nsswitch.conf` 中的 `merge` 动作上游尚未实现（`main.c` 中显式 `die_fmt`），
  配置了会启动失败。
---

**编译结束**: 2026-10-14 18:51
**最终状态**: built
