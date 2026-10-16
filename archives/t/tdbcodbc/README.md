# tdbcodbc

**tdbcodbc** — TDBC（Tcl Database Connectivity）的 ODBC 驱动桥，把 Tcl 的数据库
接口标准接到任意 ODBC 驱动管理器与 ODBC 驱动上。

- 上游：<https://core.tcl-lang.org/tdbcodbc/>
- 版本：1.1.14
- 构建系统：autotools（TEA — Tcl Extension Architecture）
- 依赖：`tcl/8.6.16`、`tdbc/1.1.14`（build + run）、`unixodbc/2.3.12`（run）

## 说明

本包是 `tdbc` 基础包的**驱动实现**之一。Tcl 侧提供 `tdbc::odbc::connection` /
`statement` / `resultset` 三个 TclOO 类（继承 tdbc 基类），以及
`tdbc::odbc::drivers` / `datasources` / `datasource` 三个驱动管理器命令；C 侧提供
扩展入口 `Tdbcodbc_Init` 与 ODBC 符号 stub 表。

同族驱动包：

| 驱动包 | 数据库客户端依赖 |
|--------|-----------------|
| **tdbcodbc（本包）** | **unixodbc（+ 任意 ODBC 驱动）** |
| tdbcmysql | mysql-client |
| tdbcpostgres | libpq |
| tdbcsqlite3 | sqlite3 |

### 与 unixODBC 的耦合方式（重要）

上游**不在链接期依赖 unixODBC**：`generic/fakesql.h` 自带一份 ODBC 类型声明，
`generic/odbcStubInit.c` 在运行期 dlopen 驱动管理器并用 `Tcl_FindSymbol` 解析
30 个 `SQL*` 符号。因此产物 `DT_NEEDED` 只有 `libc.so`。

但**运行期硬依赖**：首次 ODBC 调用时 `GetHEnv()` → `OdbcInitStubs()` 必须能
dlopen `libodbc.so.2`（驱动管理器）与 `libodbcinst.so.2`（安装器库，可选），
否则所有 `tdbc::odbc::*` 命令失败。所以 `unixodbc` 仍必须声明为 requires。

候选库名表没有 `__OHOS__` 分支，OHOS 走 Linux 路径：由 `libodbc` +
`info sharedlibextension`(`.so`) + ABI 后缀 `.2` 命中 soname `libodbc.so.2`。

## OHOS 适配要点

- TEA 的 `configure`/`config.status` 用 `umask 077` 建临时目录，HMDFS 权限归一化后
  不可写 → 补丁改 `022`（与 tcl、tdbc 同源问题）。
- TEA 的 `tcl.m4` 无 HarmonyOS 分支，`uname -s` 含 `HarmonyOS` 使
  `SHLIB_LD`/`SHLIB_SUFFIX` 为空 → 传 `tcl_cv_sys_version=Linux-6.6`。
- `TEA_PREFIX` 会继承 tclConfig.sh 的 `TCL_EXEC_PREFIX` → 显式
  `--prefix`/`--exec_prefix`，安装经 `DESTDIR` 落到本包 staging。
- 已发布的 `tdbc` 包里 `tdbcConfig.sh` 记录的是**它自己打包时**的 prefix
  （`/usr/local`）与**构建机** conan cache 绝对路径，直接 source 会得到失效的
  `tdbc_INCLUDE_SPEC` / `tdbc_STUB_LIB_SPEC`；命令行 `VAR=` 覆盖会被 source 冲掉，
  只能用 `CPPFLAGS` / `LDFLAGS` 补真实包目录。
- `unixodbc` 未声明 buildenv_info，`build()` 内跑上游测试前需在 `generate()` 里把
  它的 libdir 注入 build 作用域的 `LD_LIBRARY_PATH`。
- OHOS 不支持 make jobserver 的 mkfifo → 构建统一 `make -j1`。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/tdbcodbc1.1.14/libtdbcodbc1.1.14.so` | Tcl 扩展共享库（tclsh 经 `pkgIndex.tcl` dlopen） |
| `lib/tdbcodbc1.1.14/{pkgIndex.tcl,tdbcodbc.tcl}` | Tcl 包索引 / ODBC 桥的 TclOO 类定义 |
| `include/{fakesql.h,odbcStubs.h}` | 上游声明安装的公共头 |
| `share/man/mann/tdbc_odbc.n` | 参考手册 |

库类型（无 `bin/` 可执行产物）→ 不需要 `commands.json`（R38 / CI L0k）。

## 使用

```tcl
package require tdbc::odbc 1.1.14

# 枚举驱动管理器里已注册的 ODBC 驱动与数据源
puts [tdbc::odbc::drivers]
puts [tdbc::odbc::datasources]

# 连接（需要 unixODBC 里已注册的驱动）
tdbc::odbc::connection create db "DRIVER=SQLite3;Database=/tmp/x.db"
db allrows {SELECT 1}
```

> 注意：本包只提供 ODBC **桥**，实际能连什么数据库取决于目标机上注册了哪些 ODBC
> 驱动。制品仓当前只有驱动管理器（`unixodbc`），尚无 SQLite/MySQL 等 ODBC 驱动包。

### 消费方必读：TCLLIBPATH 是空格分隔的 Tcl 列表

Tcl 的 `init.tcl` 用 `set auto_path $env(TCLLIBPATH)` 直接把它当 **Tcl 列表**解析，
分隔符是**空格**，不是 `:`。而 Conan 的 `runenv_info.prepend_path` 用 `os.pathsep`
（Linux 上为 `:`）拼接，且 `conan/tools/env/environment.py` 的 `get_str()` 对 path
型变量恒定用 pathsep join、忽略自定义 separator。本包依赖图里有两个 Tcl 扩展
（`tdbcodbc` 与 `tdbc`）各自前置自己的 `lib/`，于是 conanrun 环境里的 `TCLLIBPATH`
形如 `<tdbcodbc>/lib:<tdbc>/lib` —— Tcl 会把它当成**一个**不存在的目录，
`tclPkgUnknown` 的 `glob -directory $dir */pkgIndex.tcl` 扫不到任何 pkgIndex.tcl，
`package require tdbc::odbc` 直接报 `can't find package`（CI #91604 实测）。

因此下游消费方（含本包 `test_package`）需按 Tcl 语义显式重设：

```bash
TCLLIBPATH="<tdbcodbc pkg>/lib <tdbc pkg>/lib" tclsh8.6 your_script.tcl
```

只有一个 Tcl 扩展包时不会产生 `:`，所以这个坑只在「依赖图里有 >= 2 个 Tcl 扩展包」
时暴露 —— `tdbc/1.1.14` 自己的 test_package 正是因此没有踩到。

## 参考资料

- 上游主页 / Fossil 仓库：<https://core.tcl-lang.org/tdbcodbc/>
- TDBC 基础包：<https://core.tcl-lang.org/tdbc/>
- unixODBC：<https://www.unixodbc.org/>
- 同族已归档配方：`archives/t/tdbc/1.1.14/`、`archives/t/tcl/8.6.16/`、`archives/u/unixodbc/2.3.12/`
