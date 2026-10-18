# DRAFT-gnu-efi-4.0.4: 手写 Makefile 的「双前缀 install」+ 生成物不随 install 重生成 + in-tree VERSION 漂移

- **来源**：gnu-efi 4.0.4 适配（2026-10-16）
- **领域**：构建系统 / 打包 / pkg-config / 版本元数据（手写 Makefile 项目）
- **查重结论**：`knowledge/graph/` 无 `INSTALLROOT` 命中、无「in-tree VERSION 与 tag 漂移」条目；
  最接近的 `E108`（OHOS 无 `install(1)` ⇒ `INSTALL := install` 报 `Error 127`）是**另一条机制**
  （本包以显式 `INSTALL=ginstall` 处理，不替代本条）；草稿池
  `DRAFT-PKG-VER-makefile-install-cmd-absent-makevar-override` 讲的是"安装命令写死、只能靠
  makevar 覆盖"，与本条的**双层安装根 + 生成物陈旧 + 版本漂移**无重叠 ⇒ 按 `create` 申报。

## 现象（三条各自可复现）

以 gnu-efi 4.0.4 的树为例，按 Conan 惯例打包：

```bash
make -j4 ARCH=aarch64 CC=clang HOSTCC=clang AS=clang LD=ld.lld \
     AR=llvm-ar RANLIB=llvm-ranlib OBJCOPY=objcopy INSTALL=ginstall
make install DESTDIR="$PKG" ARCH=aarch64 ... INSTALL=ginstall
```

① **布局差一层**：`find "$PKG" -maxdepth 3 -type d` 只有

```
/usr
/usr/local
/usr/local/lib
```

即 `libefi.a`/`libgnuefi.a`/头文件全落在 `<package_folder>/usr/local/…`，而配方按
`cpp_info.libdirs = ["lib"]` 去找 `<package_folder>/lib` —— 下游链接必然失败。

② **.pc 是陈旧货**：装出来的 `lib/pkgconfig/gnu-efi.pc` 原文为

```
prefix=/usr/local
exec_prefix=/usr/local
includedir=/usr/local/include
libdir=/usr/local/lib
Version: 4.0.3
```

③ **版本漂移**：`Version: 4.0.3`，而包/上游 tag 是 **4.0.4**
（`Makefile:45` 写着 `export VERSION = 4.0.3`；GitHub tag `4.0.4` =
commit `37cd8f069bde6715eebdc5e38a8f15ee6de5edcf`）。

## 根因

gnu-efi 的 `Make.defaults` 把安装路径拆成**两层前缀**：

```makefile
DESTDIR ?= /
ifeq ($(origin INSTALLROOT),undefined)
INSTALLROOT = $(DESTDIR)          # ← DESTDIR 只是 INSTALLROOT 的回退值
endif
PREFIX       := /usr/local        # ← 内层前缀，硬编码
LIBDIR       := $(EXEC_PREFIX)/lib
INCLUDEDIR   := $(PREFIX)/include
```

而安装规则写的是 `$(INSTALL) -m 644 libefi.a $(INSTALLROOT)$(LIBDIR)`
（`lib/Makefile`、`inc/Makefile`、`gnuefi/Makefile`、`apps/Makefile` 同构）。
⇒ `INSTALLROOT` 只提供**外层根**，内层 `/usr/local` 仍在；只传 `DESTDIR=<pkgdir>`
（Conan 惯例）就会多出一层 `usr/local/`。

同理，`gnu-efi.pc` 由 `gnuefi/Makefile` 的 `gnu-efi.pc:` 规则在 **`make` 阶段**生成，
而 `install:` 目标**不依赖它**（`$(INSTALL) -m 644 gnu-efi.pc …` 直接拷贝现成文件）。
⇒ 想靠 `make install PREFIX=<别的值>` 改 .pc 内容是不生效的：装出去的永远是上一轮
`make` 时写下的前缀。这条"陈旧生成物"会把前缀错误**藏起来**——只看
`make` 中间产物会以为已经对。

`Version:` 则直接来自 `VERSION` 变量（`-e 's:@VERSION@:$(VERSION):g'`），
上游 tag 升到 4.0.4 时忘了同步 Makefile 里的 4.0.3。

## 修复

**① 打包时两个前缀同时给**（外层根 = 包目录，内层前缀清空）：

```python
self.run('make install INSTALLROOT="%s" PREFIX=/ %s' % (self.package_folder, make_vars))
```

实测 `make install INSTALLROOT=<T2> PREFIX=/` 后目录树为 `<T2>/lib`、`<T2>/include`、
`<T2>/lib/pkgconfig`，`rc=0`。注意 `PREFIX=/` 会让内部拼出的
`$(INCLUDEDIR)=//include`、`$(LIBDIR)=//lib`，只是路径里多个 `/`，不影响结果
（编译期头文件搜索走 `-I$(TOPDIR)/inc`，与 `INCLUDEDIR` 无关）。

**② 把 .pc 改写成可重定位**（不要留构建期绝对路径在包里）：

```python
text = text.replace("includedir=/usr/local/include", "includedir=${prefix}/include")
text = text.replace("libdir=/usr/local/lib",             "libdir=${prefix}/lib")
text = text.replace("exec_prefix=/usr/local",            "exec_prefix=${prefix}")
text = text.replace("prefix=/usr/local",                 "prefix=${pcfiledir}/../..")
```

**③ 版本漂移：对齐交付元数据 + 如实披露上游滞后**（不是"保留错版本"、也不是"改上游源码"）：

```python
# conanfile: 与 ② 的 .pc 改写配套
"VERSION": self.version,     # 传进 make 命令行（命令行覆盖上游 export VERSION）
```

`gnu-efi.pc` 的 `Version:` 直接来自 `VERSION` 变量，因此把它钉到**真实发布版本**，
交付的元数据才与包版本一致 —— 否则下游 `pkg-config --modversion gnu-efi` 会读到
与包/tag 不符的版本号。**同时**在 `notes.md` 与 PR `## 补充说明` 如实披露
"上游源码树 `VERSION=4.0.3` 未随 tag 4.0.4 同步"，因为该滞后是上游事实、不因配方覆盖而消失。
⛔ 不要走两条歪路：① 交付 `Version:` 与包版本不一致的 .pc；② 用 `sed`/patch 去改上游
`Makefile`/源码（既是改上游源文件，也把上游滞后这件事掩盖了）。

**验证**：装出来的 .pc 原文 + `find <pkg> -maxdepth 2 -type d` + 消费者测试
（用包内 `crt0-efi-aarch64.o` + `elf_aarch64_efi.lds` + `libefi.a` + `libgnuefi.a`
链一个真 UEFI 应用，`objcopy -O efi-app-aarch64` 后断言 PE32+ / machine=0xAA64 /
subsystem=10）。本包实测：包内 `gnu-efi.pc` 为 `prefix=${pcfiledir}/../..` +
`Version: 4.0.4`，消费者测试打印 `assertions 16/16`。

## 适用边界与反例

- 仅在"`INSTALLROOT`(或 `DESTDIR`) 外层 + 硬编码 `PREFIX` 内层"的 install 规则上成立；
  上游若已规范化 `$(DESTDIR)$(PREFIX)` 且 `PREFIX` 可覆盖为相对值，直接传 `DESTDIR` 即可。
- `PREFIX=/` 不影响编译期搜索路径，但对任何**运行期**读 `PREFIX` 的脚本要复核。
- **生成物陈旧的验证纪律**：凡"元数据在 `make` 阶段生成、`install` 只做拷贝"的项目，
  必须读**装出来**的文件，不能读构建目录里的中间产物。
- 反例（本包实测）：`make` 用默认 `PREFIX=/usr/local` 时 `.pc` 就写成 `/usr/local`；
  若你只改了 install 行的 `PREFIX`，`.pc` 不会跟着变 —— 这正是本条要防的假绿。

## 与既有条目的关系

- `E108`（OHOS 无 `install(1)`，`INSTALL := install` → `Error 127`）：**另一条机制**。
  本包 `make install` 首先撞的是 `make[1]: install: No such file or directory` /
  `Error 127`，解法是显式 `INSTALL=ginstall`（GNU coreutils；本机 `command -v install`
  为空、`ginstall` 在）。本条不含该机制，两条互不替代。
- `DRAFT-PKG-VER-makefile-install-cmd-absent-makevar-override`：讲"写死的安装命令只能靠
  makevar 覆盖"，是本条的**前置条件**之一（本项目恰好可由 `INSTALL=` 覆盖），非同一结论。
