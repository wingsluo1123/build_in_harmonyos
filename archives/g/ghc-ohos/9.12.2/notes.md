# ghc-ohos 9.12.2 — OpenHarmony PC 适配笔记

> 本文档记录**实际执行并验证**的内容。规划与未验证项单独标注，不混入结论。

## 概览

| 项 | 值 |
|---|---|
| 包名 | ghc-ohos |
| 版本 | 9.12.2 |
| 上游 | GHC（Glasgow Haskell Compiler），https://www.haskell.org/ghc/ |
| 源码 | `https://downloads.haskell.org/~ghc/9.12.2/ghc-9.12.2-aarch64-alpine3_18-linux.tar.gz` |
| sha256 | `1e7188253aceda41836242207c943c56d7fdaf1ebe83149b1dbb71bdc41fba7e` |
| 大小 | 601,250,114 字节（573.4 MiB） |
| 构建系统 | 自定义（bindist 展开 + shim 层，不做上游编译） |
| 产物 | GHC 完整工具链（bin/ + lib/）+ 四个 musl 运行库 + 五个 shim |

## 为什么独立成包

对齐仓内 `flang-ohos` / `rust-toolchain` 惯例：工具链独立成包，任何 Haskell
软件都可 `tool_requires("ghc-ohos/9.12.2")` 复用，避免每个包各自自举。

## 软件简介

GHC 是 Haskell 编译器。本包只交付**编译器与运行时**，不安装任何 Hackage 包。

## 为什么必须用 alpine3_18 musl bindist

OHOS 是纯 musl。GHC 官方的 `aarch64-deb10` / `aarch64-deb12` 变体动态链接
glibc，运行时需要 `/lib/ld-linux-aarch64.so.1`，在 OHOS 上无法执行
（E105/E172，pandoc 适配时已实证）；`aarch64-alpine3_18-linux` 是**唯一可在
OHOS 执行的官方 aarch64 bindist**。

其 musl 运行时依赖取自**同版本 alpine v3.18** 的 APK（与 bindist 构建环境一致）：

| APK | 用途 |
|---|---|
| `gmp-6.2.1-r3` | GHC 的 Integer/大数运算 |
| `libffi-3.4.4-r2` | FFI 支撑 |
| `libncursesw-6.4_p20230506-r0` | GHCi/终端 |
| `ncurses-terminfo-base-6.4_p20230506-r0` | terminfo 数据库 |

**本包不需要 tcl/tcl-dev**（那是 Bluetcl 的依赖），故 conandata 不列。

## 六个技术要点（均已实现）

### 1. 601 MB bindist 的分片并行下载

`downloads.haskell.org` **单连接限速约 20-60 KB/s**，且该域名**不在 CI 镜像
清单内**——直接 `get()` 会耗时数小时。配方用 HTTP Range 分片并行下载
（24 片，`ThreadPoolExecutor`），并处理一个真实存在的坑：

> **部分代理无视 Range 直接返回 200 + 整包内容。** 下载器逐片校验长度，一旦
> 发现 `status == 200 && got == size`，即认定该响应是完整文件并保留，
> 不再拼接分片。

下载完成后校验官方 sha256。

### 2. 外来 ELF 必须自签 —— 且必须在最后一次 `copy()` 之后

OHOS 执行外来 ELF 需要 `.codesign` 段：

```
llvm-objcopy --remove-section .codesign <elf>
binary-sign-tool sign -inFile <elf> -outFile <elf>.signed -selfSign 1
```

bindist 里有 100+ 个 ELF，全部需要签名。

> **关键**：**签名必须在最后一次 `copy()` 之后**。Conan 的 `copy()` 会重写
> 文件、破坏签名（E212 族）。配方因此把 `_sign_tree(package_folder)` 放在
> `package()` 的**最后一步**（所有 copy 做完之后），且**消费方不得再 copy 这些
> 文件**。

### 3. musl 运行库的 APK 解包方式

APK 是**带签名的 gzip tar**（不是单一压缩流）。用 `get()` 会报
`BadZipFile`——必须 `download()` + `tarfile`（配方另备 `zipfile` 回退分支）。

### 4. gcc/g++/cc shim —— 本适配最精巧的部分

SDK 的 `clang` 是一个 **`$0` 相对路径的 wrapper**，且**无条件追加
`-Wl,--code-sign`**。这在 GHC 的 C 预处理阶段（配合 `-Werror`）会直接失败。
因此必须提供 shim，绕过 wrapper 直接调用 `clang-15`：

| 模式 | 处理 |
|---|---|
| `-dumpversion`/`--version`/`-print*` 等查询 | 直接转 `clang-15` |
| `-c` / `-S` / `-E`（编译阶段） | 只加 `--sysroot` + `-D__MUSL__` |
| 链接 | 再加 `-L<运行库目录>`、`libclang_rt.builtins`、`misc_stubs.o`、原子符号 `--defsym` |

三个额外细节（缺一不可）：

- **展开 GHC 的 `@response-file`**：GHC 9.12 用带引号的应答文件传阶段参数，
  shim 必须展开（`tr "\n" " "` + 去引号），否则 clang 把 `@file` 当字面量。
- **归档输入经 `-Wl,` 传递**：否则 `-x c` 的链接调用会把 `.a` 当源码。
- **原子符号 `--defsym` 别名**：bindist 的目标文件引用 GCC-13 时代的
  `__aarch64_{cas,ldadd,ldclr,ldeor,ldset,swp}{1,2,4,8}_sync`，而 clang-15 的
  compiler-rt **只有** `relax/acq/rel/acq_rel` 变体。用 `--defsym` 把它们
  别名到 `_acq_rel`（另加 `__aarch64_cas16_sync`）。

### 5. mktemp / time shim（hmdfs 与 toybox 的坑）

- **mktemp**：hmdfs 上 `mktemp -d` 会把新目录 chmod 0700，而 uid 映射的
  文件系统随即拒绝本会话访问（且**同会话 chmod 是空操作**）。shim 用
  `umask 0 && mkdir` 自行实现 `-d`。
- **time**：OHOS 的 toybox `time` **不支持 `-a/-o/-f`**，而构建脚本按 GNU time
  语法调用。shim 只剥掉 time 自己的前导选项，其余原样执行。

### 6. `misc_stubs.c` —— 补 OHOS musl 缺的两个符号

```c
void dlinfo(void) {}
int posix_spawn_file_actions_addchdir_np(void *a, const char *p) { return 0; }
```

GHC 的运行时目标文件引用它们，而 OHOS musl 不提供。

## 平台限制（重要）

### runghc / GHCi 在本平台**完全不可用**

OHOS **禁止可执行的匿名内存**，libffi 的闭包机制需要它 →
`ffi_closure_alloc` 失败 → `runghc` 与 GHCi 无法加载对象。

**影响**：Hackage 包的安装**不能用** `runghc Setup.hs` 或 Cabal 的解释器路径，
必须 **`ghc --make` 编译 Setup 脚本**再执行。任何设计上依赖 runghc 的构建
流程都需要改写。

## 验收标准（本包 test_package 实现）

| # | 验收项 | 实现 |
|---|--------|------|
| 1 | `ghc --version` 报确切版本 | 断言含 `9.12.2` |
| 2 | 包数据库/安装路径可用 | `ghc --print-libdir` 成功 |
| 3 | **真实编译冒烟** | `ghc --make Main.hs -o hello` 编译真实 Haskell 程序并**运行**，断言输出 `GHC-HELLO-SUM=55` |

第 3 条是决定性的：它一次性证明 **shim + 应答文件展开 + 原子符号 defsym +
musl 运行库 + ELF 自签**整条链路可用。

## 仓规要点

| 规则 | 本包处理 |
|---|---|
| L0k / R38 | `package_type="application"` + `bin/` 工具 → 必须有软件级 `commands.json` ✅ |
| L0e | `test_package/MANIFEST.yml` 必备 |
| L1b | 测试输出需含 **`PASS`**（大小写敏感） |
| PF2 | **bindist / APK 不得进仓**（只在构建期下载）✅ |
| R32 | `settings.os` 按 `("Linux", "OHOS")` 判断 ✅ |
| L0p | settings 四项齐全 ✅ |

## 与后续包的关系

本包是**工具链**：后续 Haskell 软件包（如 postgrest）以
`tool_requires("ghc-ohos/9.12.2")` 复用，属**独立 PR**（JC6/PF1：一个 PR 一个包）。
