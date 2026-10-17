# DRAFT-skktools-gdbm-ndbm-compat-flat-header-libs-probe — autotools 库探测 ndbm/dbm 兼容接口时，Conan gdbm 包的「平铺头 + 符号在 compat 库 + --with-gdbm 分支 early-skip」三坑叠加与归一路径

> **Contributor**: codex | **Status**: DRAFT | **Updated**: 2026-10-16
> **Severity**: 🟡 medium | **Category**: autotools / configure / dependency / ndbm / gdbm / ohos

## 相关既有条目（同族差异化定位）

本 skill 与「依赖探测」族共享「autotools 探测看不到 Conan 依赖」的背景，但本条目是
**ndbm/dbm 兼容接口（`dbm_open`/`datum`/`DBM`/`gdbm/ndbm.h`）在 Conan gdbm 包下的三坑叠加**
——非重复条目；申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **DRAFT-E2186-autotools-deps-missing-dep-flags** | 草稿 | AutotoolsToolchain 不注入依赖 `-I/-L`，AC_CHECK_LIB 探测失败 | 同族（都要显式注入依赖 flags），但本条增量是 **ndbm 头平铺 + 符号在 compat 库 + configure 分支 early-skip** 三个更具体的坑，且注入 flags 之外还须 shim 头 + 预置 `ac_cv_*` + 预置 `LIBS` |
| **DRAFT-ncdc-1.25-glib-pc-name-autotools-ac-check-lib** | 草稿 | glib pkg-config 名不匹配 + AC_CHECK_LIB 只覆盖一半 | 非本题——那是 pkg-config 模块名/glib 链路，本条是 **ndbm/dbm 兼容接口**（无 .pc，纯 `AC_CHECK_LIB`/`AC_CHECK_HEADERS` 路径） |
| **ac_cv_* 缓存变量预置族**（rpl_malloc / ac_cv_path__libcurl_config / utmpx 等） | 草稿/正式 | 交叉编译探测误判 → 缓存变量覆盖 | 同族手法（`ac_cv_*` 预置），但本条符号与机理不同——是 `ac_cv_lib_gdbm_dbm_open`/`ac_cv_lib_gdbm_compat_dbm_open` 预置**迫使 with-gdbm 分支走到头检查**，不是覆盖一个误判值 |

> 全库查证（2026-10-16，主仓库 `knowledge/drafts/` 全量 + 各 worktree）：
> `dbm_open` / `ndbm` / `gdbm_compat` / `HAVE_GDBM_NDBM_H` 命中 **0 条**——无正面撞车；本条目为真增量。

## Scope（何时用）

在 OHOS（或任何 Linux/musl）上用 autotools 构建、`configure.ac` 探测 ndbm/dbm 兼容接口
（典型：`AC_CHECK_LIB(gdbm, dbm_open)`、`AC_CHECK_LIB(gdbm_compat, dbm_open)`、
`AC_CHECK_HEADERS(gdbm/ndbm.h)`，源码里 `#include <gdbm/ndbm.h>` 并用 `DBM`/`datum`/`dbm_open`），
且依赖 **Conan 的 gdbm 包**时，若出现：

- 编译报 `unknown type name 'DBM'` / `use of undeclared identifier 'datum'`（头未定义）；
- configure 日志 `ac_cv_header_gdbm_ndbm_h=no` 且 `unable to find library -lgdbm`；
- 明明 `libgdbm_compat.a` 存在、`dbm_open` 就在里面，链接却报 `undefined symbol: dbm_open`。

典型实例：skktools 1.3.4（skkdic-expr 用 ndbm 接口做词典合并，依赖 gdbm/1.23）。

## Symptom

```text
skkdic-expr.c:91:1: error: unknown type name 'DBM'
skkdic-expr.c:194:6: error: expected function body after function declarator
     datum key;
configure:11605: clang ... conftest.c -lgdbm
ld.lld: error: unable to find library -lgdbm_compat   # 或 -lgdbm
ac_cv_header_gdbm_ndbm_h=no
```

## Root Cause

三个坑**叠加**，只修其中一个仍然链接失败：

1. **头平铺**：Conan 的 gdbm 包（`--enable-libgdbm-compat` 构建）把 ndbm 兼容头**平铺**到
   `include/ndbm.h`（外加 `include/dbm.h`），而**不是**上游源码树里的 `gdbm/ndbm.h` 路径。
   configure 的 `AC_CHECK_HEADERS(gdbm/ndbm.h)` 探不到 → `HAVE_GDBM_NDBM_H` 不定义 →
   源码 `#include <gdbm/ndbm.h>` 无头可含 → `DBM`/`datum` 未声明。
2. **符号在 compat 库**：`dbm_open`/`dbm_close` 等符号在 `libgdbm_compat.a`，不在
   `libgdbm.a`。configure 的 `AC_CHECK_LIB(gdbm, dbm_open)` 直接失败，掉进 ndbm/db
   探测链，最后 `LIBS` 为空。
3. **--with-gdbm 分支 early-skip**：上游 `configure.ac` 的 `--with-gdbm=yes` 分支写法是
   `AC_CHECK_LIB(gdbm, dbm_open, , AC_CHECK_LIB(gdbm_compat, dbm_open,,, -lgdbm))`，
   且**只有当 `ac_cv_lib_gdbm_compat_dbm_open=yes` 时**才执行后续
   `AC_CHECK_HEADERS(gdbm/ndbm.h)` 并 `LIBS="$LIBS -lgdbm"`。若预置了 `LIBS=-lgdbm_compat`
   使第一条 `AC_CHECK_LIB(gdbm, dbm_open)` 意外成功，`ac_cv_lib_gdbm_compat_dbm_open`
   就**不会被设置**，头检查被跳过、`LIBS` 只追加 `-lgdbm`（缺 compat）→ 编译期无头、
   链接期 `dbm_open` 仍 undefined。

## Recommended Solution

**主方案：三件套（shim 头 + ac_cv 预置 + LIBS 预置），缺一不可。**

在 `generate()` 里：

1. 生成 `gdbm/ndbm.h` shim（内容 `#include <ndbm.h>`）放进一个临时 include 目录，并把该
   目录 + 依赖包 include 目录追加进 `extra_cflags`（或 CPPFLAGS）——让
   `AC_CHECK_HEADERS(gdbm/ndbm.h)` 能命中、`HAVE_GDBM_NDBM_H` 被定义。
2. 预置 `ac_cv_lib_gdbm_dbm_open=yes` 与 `ac_cv_lib_gdbm_compat_dbm_open=yes`——迫使
   `--with-gdbm` 分支**走到** `AC_CHECK_HEADERS(gdbm/ndbm.h)`（被 shim 满足）。
3. 预置 `LIBS=-lgdbm_compat`——configure 最终 `LIBS="-lgdbm_compat -lgdbm"`，静态链接
   顺序正确（compat 在前、gdbm 在后），`dbm_open` 与 `gdbm_*` 闭包都能解析。

```python
# conanfile.py generate() 内（依赖 gdbm/1.23）
import shutil
shim_dir = os.path.join(self.build_folder, "compat-include")
os.makedirs(os.path.join(shim_dir, "gdbm"), exist_ok=True)
with open(os.path.join(shim_dir, "gdbm", "ndbm.h"), "w", newline="\n") as fh:
    fh.write("#include <ndbm.h>\n")

tc.extra_cflags = (tc.extra_cflags or []) + ["-I" + shim_dir]  # 再并上依赖 include 目录
env = tc.environment()
env.define("LIBS", "-lgdbm_compat")
env.define("ac_cv_lib_gdbm_dbm_open", "yes")
env.define("ac_cv_lib_gdbm_compat_dbm_open", "yes")
tc.generate(env)
```

**依赖版本关键约束**：必须用 **gdbm/1.23**（其配方 `--enable-libgdbm-compat` 提供
`ndbm.h`/`dbm.h` + `libgdbm_compat.a`）。**gdbm/1.24 用 `--disable-libgdbm-compat`**，
不提供 ndbm 兼容头/库，无法用于需要 ndbm 接口的库——这是依赖选型错误，不是代码缺陷。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **skktools/1.3.4-0.20210220** | 主验证（本 PR） | ✅ 三件套后 configure 定义 `HAVE_GDBM_NDBM_H=1`、`HAVE_LIBGDBM=1`；skkdic-expr/skkdic-expr2 等 4 工具全部链接成功；上游 golden 测试 4/4 通过、test_package 16/16、shadow CI L0-L5 全 pass |

## 测试覆盖边界

- shim 头与 `ac_cv_*` 预置只影响 **configure 探测层**，不改库行为（ndbm 语义由
  libgdbm_compat 提供，与上游 Linux 一致）；
- 预置 `ac_cv_lib_gdbm_dbm_open=yes` 需先在设备上实测为真（`dbm_open` 确在 compat 库、
  头确平铺），**不能凭空预置**；否则会把「依赖缺失」掩盖成「探测通过」，最终链接才崩；
- 声明通过率时以 conan create 全流程 + 上游测试 + test_package 为实证，不以「configure
  过了」为准。
