# DRAFT-jdim-0.10.1-aclocal-path-libtool-m4-clobber：tool_requires 里 autoconf-archive 的 `ACLOCAL_PATH` **define_path** 顶掉 libtool 的 **append_path**，导致 `aclocal.m4` 缺 `libtool.m4`、automake 全线报 `RANLIB undefined`

> Status: **Draft**（待审核 promote）｜ severity: `2` ｜ category: `ohos, toolchain, conan, autotools, m4` ｜ Updated: 2026-10-18
> 对应: `knowledge/drafts/DRAFT-jdim-0.10.1-aclocal-path-libtool-m4-clobber.kv`
> 来源: `archives/j/jdim/0.10.1`（jdim 0.10.1 / tag `JDim-v0.10.1`，Autotools 自举）

---

## 触发面

- trigger_tool: `conan|autoreconf|aclocal|automake|libtool|autoconf-archive`
- phase: `configuration|build`（`build()` 第一步 `autoreconf`）
- 前置形态：`build_requirements()` 里**同时**有
  `tool_requires("autoconf-archive/<ver>")` 与 `tool_requires("libtool/<ver>")`，
  且上游 `configure.ac` 用 **`LT_INIT`**（libtool 化）而**不是**显式 `AC_PROG_RANLIB`，
  且 tag archive 只有 `configure.ac`（无 `configure`）必须自举。

**匹配关键词**：RANLIB undefined、LT_INIT、AC_PROG_RANLIB、noinst_LIBRARIES、
ACLOCAL_PATH、define_path、append_path、autoconf-archive、libtool.m4、aclocal.m4、
autoreconf、PKG_CHECK_MODULES、pkg.m4、buildenv_info、conanbuildenv

## 错误签名（error_signature）

```text
src/<dir>/Makefile.am:1: error: library used but 'RANLIB' is undefined
src/<dir>/Makefile.am:1:   The usual way to define 'RANLIB' is to add 'AC_PROG_RANLIB'
src/<dir>/Makefile.am:1:   to 'configure.ac' and run 'autoconf' again.
autoreconf: error: <conan cache>/p/autom.../p/bin/automake failed with exit status: 1
```

同一缺陷的**第二张面孔**（漏 `pkg.m4` 时）：

```text
./configure: line 20134: syntax error near unexpected token `GTKMM,'
./configure: line 20134: `PKG_CHECK_MODULES(GTKMM, gtkmm-3.0 >= 3.24.0)'
```

## 根因（root_cause）

Conan 2 的 `Environment` 合并语义**不对称**：`buildenv_info.define_path("ACLOCAL_PATH", X)`
是**赋值**，`buildenv_info.append_path("ACLOCAL_PATH", X)` 是**追加**。

- `libtool/2.5.4`（ohpcd）在 `package_info()` 里用 `append_path` 追加自己的
  `<pkg>/share/aclocal`（内含 `libtool.m4`、`ltoptions.m4`、`ltsugar.m4` 等）；
- `autoconf-archive/2024.10.16`（ohpcd）在 `package_info()` 里用 **`define_path`**
  声明 `ACLOCAL_PATH` 指向自己的 `<pkg>/share/aclocal`（内含 `ax_*.m4`）。

两者都是 build 上下文依赖时，**最终 `ACLOCAL_PATH` 只剩 autoconf-archive 一项**。
实测证据（jdim run5，conan 2.29.1，OHOS aarch64）：

```
# conan 生成的 env 脚本，第 20 行 —— 只有一项，libtool 的目录不见了
$ grep -n ACLOCAL_PATH <build>/build-release/conan/conanbuildenv-release-armv8.sh
20:export ACLOCAL_PATH="<cache>/p/autoc.../p/share/aclocal"
```

（对照：同文件第 21–26 行 `LIBTOOLIZE`、`_lt_pkgdatadir`、`AUTOMAKE`、`ACLOCAL`、
`PERL5LIB` 都是 libtool/automake 的路径，说明 libtool 的 buildenv **确实参与了合并**，
只是 `ACLOCAL_PATH` 这一项被 define 覆盖掉了。）

因果链闭合（可机械核验）：

```
$ grep -c 'AC_DEFUN(\[LT_INIT\]' aclocal.m4      -> 0      # libtool.m4 没进 aclocal.m4
$ grep -c 'AX_CXX_COMPILE_STDCXX' aclocal.m4     -> 34     # autoconf-archive 的宏在
```

automake 判定"上游是否使用了 RANLIB 供给方"是看 `aclocal.m4` 里有没有 `LT_INIT`
（libtool 化）或 `AC_PROG_RANLIB` 的定义；`LT_INIT` 缺失 ⇒ automake 认为
`RANLIB` 未定义 ⇒ 每一个 `noinst_LIBRARIES`（或 `lib*_a_SOURCES`）目录各报一条
`library used but 'RANLIB' is undefined`，`autoreconf` 以 automake 退出码 1 中止。
**注意：这不是"上游 configure.ac 写错"**——`LT_INIT` 本身就是 RANLIB 的合法供给方，
缺的是**传递到 aclocal 的 m4 搜索路径**。

同一根因的第二张面孔：`pkg.m4`（`PKG_CHECK_MODULES` 的宏定义）来自 **pkg-config**，
它装在 SDK 前缀（`<sdk>/pkg-config.org/pkg-config_<ver>/share/aclocal/pkg.m4`），
**不在 Conan 工具图里**；`ACLOCAL_PATH` 被覆盖后同样找不到它，autoconf 不展开
`PKG_CHECK_MODULES`，生成的 `configure` 里残留宏字面量 ⇒ 运行时报
`syntax error near unexpected token 'GTKMM,'`。

## 影响范围（affected_scope）

- **一类**，不是单个包：任何"`tool_requires(autoconf-archive)` + `tool_requires(libtool)` +
  上游用 `LT_INIT` + tarball 无 `configure`"的 autotools 包，在 OHOS aarch64 +
  Conan 2.29.1 下**必然**复现（与网络、权限、SDK 版本无关，纯 env 合并语义）。
- 只在**自举**（`autoreconf`）路径出现；若上游 tarball 已带生成好的 `configure`，
  则不经过 aclocal，症状消失——所以"本包以前能过"不能反证本条不成立。
- jdim 实测：`src/` 下 15 个 `noinst_LIBRARIES` 目录 + 顶层 `Makefile.am`
  全部命中，一次 `autoreconf` 报满屏；修好后 `configure` 一次通过（见下）。

## 推荐方案（rec_approach: `merge-aclocal-path-with-explicit-I`）

**双保险**（不依赖 env 合并顺序/Conan 版本）：

1. **一次性 `define_path` 写全量**：在 `generate()` 里自行收集
   `libtool` / `automake` / `autoconf-archive` 三个 tool_requires 的
   `<pkg>/share/aclocal`，**再加上 pkg-config 的 `pkg.m4` 目录**
   （用 `shutil.which("pkg-config")` 反推前缀，再 glob
   `<prefix>/pkg-config.org/*/share/aclocal` 与 `<prefix>/*/share/aclocal`，
   **不硬编码 `/data/service/hnp/...`**），拼成 `:` 连接串**一次**
   `buildenv_info.define_path("ACLOCAL_PATH", <全量>)`。
   这样无论包内 define/append 谁先谁后，最终值都包含全部目录。
2. **给 `autoreconf` 显式 `-I`**：`autoreconf -fi -I <dir1> -I <dir2> …`，
   把同一批目录直接交给 `aclocal`。即使 conanbuild env 在别的 Conan 版本里
   又改了合并语义，`aclocal` 也一定能找到 `libtool.m4` 与 `pkg.m4`。

配方侧落点（jdim 0.10.1 实际形态，可作模板）：

```python
def _aclocal_dirs(self):          # libtool / automake / autoconf-archive
    dirs = []
    for dep in self.dependencies.values():
        if dep.ref.name not in ("libtool", "automake", "autoconf-archive"):
            continue
        cand = os.path.join(dep.package_folder, "share", "aclocal")
        if os.path.isdir(cand) and cand not in dirs:
            dirs.append(cand)
    return dirs

def _pkg_m4_dirs(self):           # SDK pkg-config 的 pkg.m4（不在工具图里）
    out, cands = [], []
    for tool in ("pkg-config", "pkgconf"):
        path = shutil.which(tool)
        if not path:
            continue
        prefix = os.path.dirname(os.path.dirname(os.path.realpath(path)))
        cands += [os.path.join(prefix, "share", "aclocal")]
        cands += glob.glob(os.path.join(prefix, "pkg-config.org", "*", "share", "aclocal"))
        cands += glob.glob(os.path.join(prefix, "*", "share", "aclocal"))
    for c in cands:
        if os.path.isfile(os.path.join(c, "pkg.m4")) and c not in out:
            out.append(c)
    return out

def generate(self):
    dirs = self._aclocal_dirs() + [d for d in self._pkg_m4_dirs() if d not in self._aclocal_dirs()]
    if dirs:
        self.buildenv_info.define_path("ACLOCAL_PATH", ":".join(dirs))   # ← 全量 define
    ...

def build(self):
    args = ["-fi"]
    for d in self._m4_dirs():        # ← 第二道保险
        args += ["-I", d]
    Autotools(self).autoreconf(args=args)
```

**证伪/验证判据**（原样可跑）：

```text
# 1) 机制层：ACLOCAL_PATH 是否被覆盖成单项
grep -n ACLOCAL_PATH <build>/build-release/conan/conanbuildenv-*.sh
# 2) 后果层：aclocal.m4 里两个宏的计数
grep -c 'AC_DEFUN(\[LT_INIT\]'        aclocal.m4   # 修复后 >= 1
grep -c 'AX_CXX_COMPILE_STDCXX'       aclocal.m4   # 修复前后都是 34
grep -c 'PKG_CHECK_MODULES' configure              # 修复后 = 0（全部展开）
# 3) 9 秒级复现/回归探针（带 tool_requires 的完整 env）
autoreconf --force --install -fi \
  -I <libtool pkg>/share/aclocal \
  -I <autoconf-archive pkg>/share/aclocal \
  -I <sdk>/pkg-config.org/pkg-config_<ver>/share/aclocal
# 修复前：automake failed with exit status 1（RANLIB undefined）
# 修复后：rc=0，生成 configure（jdim 实测 699322 B）
```

jdim 上的实测闭环：

| 步骤 | 修复前 | 修复后 |
|---|---|---|
| `conanbuildenv-*.sh` 的 `ACLOCAL_PATH` | 1 项（只剩 autoconf-archive） | 3 项（libtool + autoconf-archive + pkg-config） |
| `aclocal.m4` 中 `AC_DEFUN([LT_INIT]` | **0** | **1** |
| `aclocal.m4` 中 `AX_CXX_COMPILE_STDCXX` | 34 | 34 |
| `autoreconf -fi -I …` | rc≠0（automake exit 1） | **rc=0**，`configure` 699322 B |
| 生成的 `configure` 里 `PKG_CHECK_MODULES` 字面量 | 存在（未展开） | **0** |
| `./configure`（真实 conan env） | 停在 `PKG_CHECK_MODULES(GTKMM,…)` 语法错 | **rc=0**，`config.status` 产出全部 Makefile + `config.h` |

## 兜底（fallback: `vendor-m4-into-recipe`）

把 `libtool.m4` / `pkg.m4`（必要时连 `lt*.m4`）作为配方 `exports_sources` 的一部分
（`m4/` 目录）随包提交，`generate()` 里把该目录注入 `ACLOCAL_PATH`。
**缺点**：把第三方 m4 复制进归档、PR diff 变大、宏版本要人工跟进；
仅在 `tool_requires` 路径不可用（例如某版本 Conan 彻底不合并依赖的 buildenv）时才用。

## 关联（causes / similar_to）

- `causes: []`、`caused_by: []`、`similar_to: []`：
  本条目与既有条目的**症状签名不同**——既有 autotools 条目多讲
  `configure` 运行期问题（`config.guess` 受限、`umask 077` 不可写、`getcwd` 失败、
  `pkg.m4` 缺失的语法错），本条讲的是 **`aclocal` 阶段的 m4 搜索路径被 env 合并语义吃掉**，
  其首选修法（`define_path` 全量 + `autoreconf -I` 双保险）在知识库里此前没有。
- 与"`pkg.m4` 缺失 → `PKG_CHECK_MODULES` 语法错"是**同根因的两张面孔**，
  故本条目把两者写在同一条（同一修法一次修好），而不是拆成两条。
- `principles: P014, P020`（构建工具必须来自 Conan 工具链/显式声明，而非"碰巧在 PATH 上"）。
