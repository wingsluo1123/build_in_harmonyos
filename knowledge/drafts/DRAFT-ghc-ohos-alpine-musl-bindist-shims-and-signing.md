# ghc-ohos：musl bindist 自举 + shim 层 + 自签时机

> 配套结构化条目：`DRAFT-ghc-ohos-alpine-musl-bindist-shims-and-signing.kv`

## 为什么必须用 alpine3_18 musl bindist

OHOS 是纯 musl。GHC 官方的 `aarch64-deb10` / `aarch64-deb12` 变体动态链接
glibc，运行时需要解释器 `/lib/ld-linux-aarch64.so.1`：

```
$ ./ghc-9.12.2/bin/ghc --version
/bin/sh: ./ghc-9.12.2/bin/ghc: cannot execute: required file not found
```

**只有 `aarch64-alpine3_18-linux` 变体能在 OHOS 执行**（E105/E172，pandoc
适配时已实证）。其 musl 运行时依赖取自**同版本 alpine v3.18** 的 APK：
`gmp`、`libffi`、`libncursesw`、`ncurses-terminfo-base`。

## 坑 1：601 MB bindist 的分片并行下载

`downloads.haskell.org` 单连接限速约 **20-60 KB/s**，且该域名**不在 CI 镜像
清单内**——直接下载要数小时。解法是 HTTP Range 分片并行（24 片）。

**关键坑**：部分代理会**无视 `Range` 直接返回 200 + 整包内容**。下载器必须
逐片校验长度并识别这种情况：

```python
if status == 200 and got == size:
    os.replace(part, dest)   # 这是完整文件，直接保留
    return "FULL"
if got == want:
    return "OK"
```

否则会把"恰好只有第一片在写整包"的结果与其它分片拼接，得到损坏文件。

## 坑 2：外来 ELF 自签 —— 时机是**最后一次 copy() 之后**

OHOS 执行外来 ELF 需要 `.codesign` 段：

```bash
llvm-objcopy --remove-section .codesign <elf>
binary-sign-tool sign -inFile <elf> -outFile <elf>.signed -selfSign 1
```

bindist 内有 100+ 个 ELF 需要签名。**但**：

> Conan 的 `copy()` 会重写文件、**破坏签名**（E212 族）。

因此签名必须是 `package()` 的**最后一步**（所有 `copy()` 完成之后），
且**消费方不得再 copy 这些文件**。把签名放在 copy 之前 = 白签。

## 坑 3：SDK clang wrapper 必须绕过

SDK 的 `clang` 是一个 **`$0` 相对路径的 wrapper**，且**无条件追加
`-Wl,--code-sign`**。这在 GHC 的 C 预处理阶段（配合 `-Werror`）会直接失败。
所以必须提供 gcc/g++/cc shim，直接调用 `clang-15`：

| 模式 | shim 行为 |
|---|---|
| `-dumpversion` / `--version` / `-print*` | 原样转给 `clang-15` |
| `-c` / `-S` / `-E`（编译） | `--sysroot=... -D__MUSL__` |
| 链接 | 追加 `-L<运行库>`、`libclang_rt.builtins`、`misc_stubs.o`、原子符号 defsym |

三个必须处理的细节：

1. **展开 `@response-file`**：GHC 9.12 用带引号的应答文件传参数
   （`tr "\n" " "` + 去引号），否则 clang 把 `@file` 当字面量。
2. **归档输入经 `-Wl,` 传递**：否则 `-x c` 的链接调用会把 `.a` 当源码。
3. **原子符号 `--defsym` 别名**：bindist 的目标文件引用 GCC-13 时代的
   `__aarch64_{cas,ldadd,ldclr,ldeor,ldset,swp}{1,2,4,8}_sync`，而 clang-15 的
   compiler-rt **只有** `relax/acq/rel/acq_rel`：

   ```
   -Wl,--defsym,__aarch64_ldadd8_sync=__aarch64_ldadd8_acq_rel
   -Wl,--defsym,__aarch64_cas16_sync=__aarch64_cas16_acq_rel
   ```

## 坑 4：`misc_stubs.c` 补 OHOS musl 缺的符号

```c
void dlinfo(void) {}
int posix_spawn_file_actions_addchdir_np(void *a, const char *p) {
    (void)a; (void)p; return 0;
}
```

## 坑 5：mktemp / time shim

- **mktemp**：hmdfs 上 `mktemp -d` 建出的目录属主是本会话却**不可写**，且
  同会话 `chmod` 是空操作 → shim 用 `umask 0 && mkdir` 自行实现 `-d`。
- **time**：OHOS toybox 的 `time` **不支持 `-a/-o/-f`**，而构建脚本按 GNU time
  语法调用 → shim 只剥掉 time 自己的前导选项。

## 坑 6：APK 解包不能用 `get()`

APK 是**带签名的 gzip tar**，不是单一压缩流；`get()` 会报 `BadZipFile`。
必须 `download()` + `tarfile`（配方另备 `zipfile` 回退）。

## 平台硬限制：runghc / GHCi 完全不可用

OHOS **禁止可执行的匿名内存** → libffi 的 `ffi_closure_alloc` 失败 →
`runghc` 与 GHCi 无法加载对象。

**影响**：Hackage 包安装**不能**用 `runghc Setup.hs` / Cabal 解释器路径，
必须 **`ghc --make` 编译 Setup 脚本**再执行。任何依赖 runghc 的构建流程都要改写。

## 验收：真实编译冒烟才是决定性证据

test_package 的三步：

| # | 步骤 | 断言 |
|---|---|---|
| 1 | `ghc --version` | 含 `9.12.2` |
| 2 | `ghc --print-libdir` | 成功（包数据库/安装路径可用） |
| 3 | `ghc --make Main.hs -o hello` 并**运行** | 输出 `GHC-HELLO-SUM=55` |

第 3 条一次性证明 **shim + 应答文件展开 + 原子符号 defsym + musl 运行库 +
ELF 自签**整条链路可用。

## 仓规要点

| 规则 | 处理 |
|---|---|
| L0k / R38 | `package_type="application"` 且有 `bin/` → 必须有软件级 `commands.json` |
| L0e | `test_package/MANIFEST.yml` 必备 |
| L1b | 测试输出需含 `PASS`（大小写敏感） |
| PF2 | bindist / APK **不得进仓**（仅构建期下载） |
| R32 | `settings.os` 按 `("Linux","OHOS")` 判断 |
| L0p | settings 四项齐全 |

## 与后续包的关系

本包是**工具链**：后续 Haskell 软件（如 postgrest）以
`tool_requires("ghc-ohos/9.12.2")` 复用，属**独立 PR**（JC6/PF1：一个 PR 一个包）。
