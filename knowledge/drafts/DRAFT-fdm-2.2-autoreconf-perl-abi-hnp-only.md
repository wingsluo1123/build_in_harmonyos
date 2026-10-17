# DRAFT-fdm-2.2-autoreconf-perl-abi-hnp-only: OHOS 上 autoreconf 自举的 perl 双版本 ABI 冲突 —— 不声明 autoconf/m4、把 perl 收敛到 SDK 那一支

> 实证包：fdm 2.2（GitHub tag 归档只有 `configure.ac`，必须 `autoreconf` 自举）。
> 判定：B=create（`B判定=create`，症状同族存在但解法不同，见文末查重）。

## 错误特征（稳定签名）

```
Can't load '…/perl/5.42.2/…/aarch64-linux-thread-multi/auto/Cwd/Cwd.so' for module Cwd:
Error relocating …/Cwd.so: Perl_my_cxt_init: symbol not found
 at …/XSLoader.pm line 94.
 at …/File/Path.pm line 6.
BEGIN failed--compilation aborted at …/p/autom…/p/bin/.aclocal-real line 31.
.autoreconf-real: error: …/bin/aclocal failed with exit status: 255
autoreconf: error: aclocal failed
```

触发条件：`build()` 里跑 `autoreconf -fi`，且 conanbuild 环境同时含有
`tool_requires("autoconf/…")`（会连带拉入 OHOS 构建的 `perl/5.42.2`）与
`tool_requires("automake/…")`（提供 aclocal/automake）。

## 根因（逐条实测，可复现）

OHOS 上有两支 perl：

| 支 | 位置 | 版本 | 谁在用 |
|---|---|---|---|
| SDK | `/data/service/hnp/bin/perl` | **5.42.0** | conan automake 的 `bin/aclocal`、`bin/automake` |
| conan | 制品仓 `perl/5.42.2` | **5.42.2** | conan autoconf 的 `bin/autoconf`、`bin/autom4te` |

conan 聚合的 `conanbuildenv` 把 `PERL5LIB` 指向 conan perl 的 lib（含 XS `.so`）。
于是同一套自举工具里：

1. **conan automake** 的包装是 `#!/bin/sh`，内部 `exec` 的 `.aclocal-real` /
   `.automake-real` 的 shebang **硬编码** `#!/data/service/hnp/bin/perl`
   （`head -1` 实测）⇒ 这两个工具永远跑在 SDK perl 5.42.0 上；
2. 5.42.0 加载 PERL5LIB 里的 5.42.2 XS（`Cwd.so`）即 `Perl_my_cxt_init: symbol not found`
   ⇒ aclocal 在生成 `aclocal.m4` 之前就崩；
3. **conan autoconf** 的 `.autoconf-real` / `.autom4te-real` shebang 指向 conan perl，
   该 perl 重定位后 `@INC` 前缀为空（`Can't locate strict.pm in @INC … //lib/perl5/5.42.2`），
   必须靠完整的 conan `PERL5LIB` 才能工作。

⇒ 两条链各要一支 perl，**同一自举流程里无法共存**。

## 试过且失败的方案（别再走）

1. **把 conan 工具 bin 前置到 PATH**（`DRAFT-20001-conan-autoconf-perl-path-abi-ohos`
   给出的解法）：实测无效 —— `.aclocal-real` 用的是**绝对 shebang**，
   不是 `#!/usr/bin/env perl`，PATH 顺序改变不了解释器。
2. **收窄 `PERL5LIB` 只留 automake 纯 Perl 模块目录**：aclocal/automake 通过，但
   conan 的 `.autom4te-real`/`.autoconf-real` 随即找不到核心模块
   （`Can't locate strict.pm in @INC`）。
3. **conan 全家桶（autoconf+automake+libtool+bison）+ `autoreconf`**：即原始失败形态。

## 正解（推荐方案）

**不引入第二支 perl**：`build_requirements()` 只声明

```python
self.tool_requires("automake/1.18")   # 提供 aclocal + automake
self.tool_requires("libtool/2.5.4")   # 提供 libtoolize
self.tool_requires("bison/3.8.2")     # 提供 yacc（parse.y -> parse.c 需要）
# 故意不声明 autoconf 与 m4：SDK /data/service/hnp/bin 已自带 autoconf 2.72 / autoreconf / m4
```

此时 conanbuild 的 `PERL5LIB` 只来自 automake 包（指向其 `share/automake-1.18`，
纯 Perl、与任何 perl 5.x 兼容），`autoreconf`/`autoconf`/`autom4te` 走 SDK 的
5.42.0，`aclocal`/`automake` 走 conan 包（硬编码 shebang 也指向 5.42.0）⇒
全链一支 perl，自举一次通过：

```
configure.ac:10: installing 'etc/config.guess'
… Makefile.am: installing 'etc/depcomp'
RC=0  →  configure(201288 B) + aclocal.m4 + Makefile.in + etc/ 辅助脚本
```

`build()` 里只需：

```python
self.run('mkdir -p etc && autoreconf -fi', cwd=self.source_folder, env="conanbuild")
```

（`etc/` 是 `AC_CONFIG_AUX_DIR(etc)` 指定的辅助目录，tag 归档里不存在，先建。）

## 验证

- 复现/修复对照：同一台 OHOS PC、同一份 fdm 2.2 源码，三种工具组合各跑一次
  `autoreconf -fi`：conan 全家桶 ✗ / 收窄 PERL5LIB + conan autoconf ✗ /
  **automake+libtool+bison only ✓**；
- 版本取证：`/data/service/hnp/bin/perl -e 'print $^V'` → `v5.42.0`；
  conan `perl/5.42.2` → `v5.42.2`；
- shebang 取证：`head -1 $(dirname $ACLOCAL)/.aclocal-real` →
  `#!/data/service/hnp/bin/perl`；`head -1 $(dirname $AUTOCONF)/.autoconf-real` →
  `#! …/.conan2/p/perl…/bin/perl`；
- 端到端：`conan create`（干净源码下载 → 自举 → configure → make → make check →
  install → test_package）通过。

## 禁止

- ❌ `tool_requires("autoconf/…")`：只要还需要 aclocal/automake，自举必崩。
- ❌ 用「PATH 前置 conan 工具 bin」当作解法：改变不了解释器，且掩盖双 perl 根因。
- ❌ 用 `env -i`/改系统 perl/`ln -sf` 覆盖 `/data/service/hnp/bin/perl` 来绕：
  系统工具属基础设施，配方不得改动。

## 兜底方案（仅在目标机既无 SDK autoconf、又必须声明 conan autoconf 时）

逐个驱动工具并各自钉死解释器与 `PERL5LIB`：

```sh
AM_SHARE=$(ls -d "$(dirname "$AUTOMAKE")"/../share/automake-* | sed -n 1p)
env PERL5LIB="$AM_SHARE" "$ACLOCAL" --force
env PERL5LIB="$AM_SHARE" "$AUTOMAKE" --add-missing --copy --foreign
"$AUTOCONF"
```

代价：绑定 conan 包装脚本的内部文件名（`.aclocal-real`/`.automake-real`），
可移植性差。

## 适用范围 / 反例 / 解除条件

- 范围：OHOS 上任何「源码归档不含生成的 configure、必须 autoreconf 自举」的
  Autotools 包（GitHub tag archive 是主形态）；CI worker 无系统
  automake/aclocal/libtoolize（`accel-config/4.1.9` 配方注释实证），automake 必须
  来自 conan，冲突必然出现。
- 反例（不适用）：release tarball 自带 `configure` 的包 —— 不跑 autoreconf，
  不会触发。
- 解除条件：制品仓提供与 SDK perl ABI 一致的 perl、或 conan automake 改用
  `#!/usr/bin/env perl` 包装时，本条自动失效。

## 查重与新增价值（B 判定依据）

四范围查重（2026-10-15 实测）：

| 范围 | 命中 |
|---|---|
| `knowledge/graph/index.tsv` + `E*.kv` | 无 perl/autoreconf ABI 条目（E041/E071/E089/E110/E116/E175/E178/E229/E248/E351/E514/E521 均为 autoreconf 其它症状） |
| `knowledge/drafts/*.kv` | `DRAFT-20001-conan-autoconf-perl-path-abi-ohos.kv` —— **同症状、不同解法**（见下） |
| `经验文档/B草稿库/`（30+ 通用机制） | 无 perl/autoreconf 相关条目 |
| 归档表 / 主表同族包 | 无同机制已交付条目 |

与 `DRAFT-20001` 的差异：该草稿给的解法是「把 build 依赖的
`package_folder/bin` 前置到 PATH」；本条实测证明该解法**无效**（绝对 shebang），
并给出另一条可行解（不引入第二支 perl）与三次组合对照实验。按手册
「症状同但解法不同 ⇒ 判 create」申报；同时把 `E490`（autotools helper 执行位）
与 `E011`（umask 077 临时目录）列为 similar_to（同包另两个适配点，非重复）。
