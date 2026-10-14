# asterisk-ldap 22.10.1 — HarmonyOS PC (OHOS aarch64) 适配笔记

## 这个包是什么

`asterisk-ldap` 是 Asterisk 22.10.1 的 **LDAP Realtime 配置模块**包，交付一个
可加载模块：

```
lib/asterisk/modules/res_config_ldap.so
```

上游源码为 `asterisk/asterisk` tag `22.10.1`（`res/res_config_ldap.c`，GPL-2.0-only）。
它把 Asterisk 的 Realtime 配置后端接到 OpenLDAP 目录服务上（`realtime` 配置
驱动 + CLI 命令）。仓库既有的 asterisk 家族采用"每个可选依赖一个模块包"的
切分方式（asterisk-curl / asterisk-pgsql / asterisk-tds / asterisk-srtp /
asterisk-speex / asterisk-espeak / asterisk-flite），本包同构：只编译并打包
LDAP 模块，不构建 asterisk 主程序。

## 上游测试入口核验（R51）

Asterisk 的自动化测试是 in-tree 单元测试框架，用例以 `AST_TEST_DEFINE(...)` 注册：

```
$ ls tests | wc -l                                         # 99 个条目
$ ls tests/test_*.c | wc -l                                # 95 个测试模块
$ grep -rh "^AST_TEST_DEFINE(" --include="*.c" . | wc -l   # 707 个用例 ← 全树源码清点口径
$ grep -rh "^AST_TEST_DEFINE(" tests/*.c | wc -l           # 633（其中 tests/ 子集）
$ grep -ril ldap tests/                                    # 仅 tests/CI/buildAsterisk.sh
```

- **上游用例总数 = 707**（源码清点口径：全树 `*.c` 中以行首 `AST_TEST_DEFINE(` 注册的
  用例数；等价写法 `grep -rho "AST_TEST_DEFINE([A-Za-z0-9_]*)" --include="*.c" . | wc -l`
  同为 707）。分布：`tests/*.c` 633 个（95 个文件），其余 74 个分布在 `res/`、`main/`、
  `funcs/`、`bridges/`、`apps/`（含 `res/res_geolocation`、`res/parking`）等 25 个 `.c`
  文件里。**申报口径必须用全树 707**——只报 `tests/` 子集 633 会被平台按「少报」驳回
  （pc-pr-review rule4：上游实测 N=707 > 声明 N）。
- 真实入口：`tests/CI/buildAsterisk.sh`（menuselect `--enable TEST_FRAMEWORK
  --enable-category MENUSELECT_TESTS` 后构建）+ `tests/CI/runUnittests.sh`，
  后者执行 `asterisk -rx "test execute all"`，再 `test show results failed` /
  `test generate results xml`。
- **res_config_ldap 没有专属上游用例**：`grep -ril ldap tests/` 只命中
  `tests/CI/buildAsterisk.sh`（CI 构建参数），95 个 `test_*.c` 中无一涉及
  LDAP；`main/ res/ funcs/ apps/ channels/ codecs/ addons/` 下也没有 LDAP 的
  `test_*.c`；707 个注册里没有一个服务于 `res_config_ldap`。
- 因此**本模块相关上游用例数 = 0**，而**上游用例总数 = 707**（两个数字口径不同，
  申报表必须分别列清，不能把「本模块 0」写成上游合计）。707 个用例需要
  **完整 asterisk 核心**（`-o asterisk/*:with_test_framework=True`，见
  `archives/a/asterisk/22.10.1` 的 `notes.md`）以及运行中的 PBX 才能执行。本模块包
  **只编译 res_config_ldap.so**（不构建核心），故 707 个上游用例**未执行** ——
  如实声明（非跳过、非通过率计入），完整清单与入口见 `reports/upstream-tests.md`。

`test_package` 的 13 项检查是消费者视角的产物验证，**不替代**上游测试统计。

## 依赖

| 依赖 | 作用 | ohpcd |
|---|---|---|
| `openldap/2.6.7` | res_config_ldap 链接目标（ldap.h / ldap_* / ber_free） | ✅ 已发布 |
| `libedit/20240808` | Asterisk 主 configure 硬要求（pkg-config 探测） | ✅ |
| `libxml2/2.15.3` | menuselect 子 configure 硬要求 | ✅ |
| `ncurses/6.6` | 提供 libedit 引用的 tinfo 符号 | ✅ |
| `e2fsprogs/1.47.4` | libuuid | ✅ |
| `jansson/2.15.1.1` | Asterisk configure 硬要求 >= 2.11 | ✅ |
| `sqlite3/3.49.1` | Asterisk configure 硬要求 | ✅ |

W0：全部依赖已发布，`conan install --requires=openldap/2.6.7 --build=never`
实测可消费（recipe + binary 均下载成功），无 R36 阻塞。

`generate()` 把 openldap 的 include/lib/pkgconfig 拷进私有 prefix
（`build_folder/prefix`，**不注入共享系统前缀**），并改写 `.pc` 的 `prefix=`。

## 编译过程：三处真实失败与修复

### 1. `RAII_VAR` —— clang 不接受 GCC 风格的嵌套函数

**现象**（首个错误，原始输出）：

```
res_config_ldap.c:1037:2: error: function definition is not allowed here
        RAII_VAR(struct ast_variable *, fields, NULL, ast_variables_destroy);
        ^
include/asterisk/utils.h:983:42: note: expanded from macro 'RAII_VAR'
    void _dtor_ ## varname (vartype * v) { dtor(*v); }
                                         ^
1 error generated.
```

**根因**：`include/asterisk/utils.h` 的 `RAII_VAR` 有三个分支——上游用
`__clang__`（blocks 版，需 `-fblocks`）与 `__GNUC__`（**嵌套函数定义**版）。
既有 asterisk 模块补丁（0004）把 blocks 分支收窄到 `__BLOCKS__`，于是 clang
在未启用 blocks 时落入 `__GNUC__` 分支——而 **clang 从不支持嵌套函数定义**。
curl/pgsql 等模块恰好不使用 `RAII_VAR`，所以没暴露；`res_config_ldap.c:1037`
使用了它。

**修复**（新增补丁 `0009`）：为「clang 且无 blocks」增加一个可移植分支，用
`__attribute__((cleanup))` 实现，cleanup 回调对变量的**最终值**调用 dtor，
与上游两个分支语义一致，且不需要 blocks 运行时：

```c
struct _raii_cleanup_s { void *addr; void (*dtor)(void *); };
static inline void _raii_cleanup_run(struct _raii_cleanup_s *s)
{ if (NULL != s->dtor) s->dtor(*(void **)s->addr); }
#define RAII_VAR(vartype, varname, initval, dtor) \
    vartype varname = (initval); \
    struct _raii_cleanup_s _raii_h_ ## varname \
        __attribute__((cleanup(_raii_cleanup_run), unused)) = \
        { (void *)&(varname), (void (*)(void *))(dtor) }
```

**重新验证**：`res_config_ldap.c -> res_config_ldap.o` 编译通过，
`[LD] res_config_ldap.o -> res_config_ldap.so` 链接通过。

### 2. `-llber` —— lld 不从传递库解析符号

**根因**：configure 的 `AST_EXT_LIB_CHECK([LDAP], [ldap], [ldap_initialize],
[ldap.h])` 只产出 `-lldap`；而 `res_config_ldap.c` 直接调用 liblber 的
`ber_free`，且 lld 默认 `--no-copy-dt-needed-entries` 不会用 libldap 的
DT_NEEDED 传递库来解析符号。

**修复**：`LIBS += -llber`（让 configure 探测通过）+ 构建后按行重写
`makeopts` 的 `LDAP_LIB`/`LDAP_INCLUDE`：

```
LDAP_LIB=-L<prefix>/lib -lldap -llber
LDAP_INCLUDE=-I<prefix>/include
```

**验证**：产物 `DT_NEEDED` 同时包含 `libldap.so.2` 与 `liblber.so.2`，
且 `ber_free@OPENLDAP_2.200` 为未定义（运行期由 liblber 解析）。

### 3. configure 的 LDAP 探测会被 lld 瞬时错误打断

沿用 asterisk 家族的既有处置：configure 探测失败后重试（最多 3 次）+ 重新
执行 `config.status`；本次实测一次通过（日志中 `checking for mandatory
modules: LDAP... ok`）。

## 构建与打包

- 全量 Asterisk `configure`（`--with-ldap=<prefix>`、`--without-pjproject`），
  menuselect 子 configure，只 `make -C res ... res_config_ldap.so`；
- 注入 `packaging/menuselect.makedeps`（`MENUSELECT_DEPENDS_res_config_ldap=LDAP`），
  不覆盖 configure 生成的 `menuselect.makeopts`——让检测到 LDAP 后模块自然启用；
- `package()` 取 `lib/asterisk/modules/res_config_ldap.so`，并附 LICENSE/COPYING；
- `package_type = shared-library`，`cpp_info.libdirs = ["lib/asterisk/modules"]`，
  无 `commands.json`（非 CLI 包，R38/PF8 口径）。

## 模块 ABI：为什么 .so 不导出符号

`AST_MODULE_INFO()` 生成 `static struct ast_module_info __mod_info` 和一个
`__attribute__((constructor)) __reg_module()`，后者调用
`ast_module_register(&__mod_info)`。加载器（`main/loader.c`）只需 `dlopen()`
模块，构造函数即完成注册——**模块不导出任何动态符号是正确形态**
（`llvm-readelf --dyn-syms` 中 76 项全部为 UND 即为此）。

## 测试（test_package，13 项检查，全部实跑）

1. **静态校验**（`test_asterisk_ldap.py` + 自实现 ELF 解析器
   `elf_utils.py`，不依赖 binutils），8 项：
   - 模块位于 `lib/asterisk/modules/res_config_ldap.so`；
   - ELF64 LE / `e_machine=AArch64` / `ET_DYN`；
   - `DT_NEEDED` 含 `libldap.so.2` 与 `liblber.so.2`；
   - 未定义符号含 res_config_ldap 实际使用的 OpenLDAP API
     （`ldap_initialize`/`ldap_set_option`/`ldap_sasl_bind_s`/`ldap_search_ext_s`/
     `ldap_modify_ext_s`/`ldap_unbind_ext_s`/`ldap_msgfree`/`ber_free`）；
   - 未定义符号含 Asterisk 模块 ABI（`ast_module_register`/`ast_module_unregister`）；
   - `DT_INIT_ARRAY` 非空（构造函数自注册）；
   - 无 `DT_RPATH`/`DT_RUNPATH`（不泄漏构建机私有 prefix 路径）；
   - 绑定 `OPENLDAP_2.200` ABI 版本。

2. **动态加载测试（鸿蒙特有）**：`ldap_module_load.c` 由构建期按模块自身的
   未定义符号表**自动生成** Asterisk 核心 API 桩（33 个），用
   `-rdynamic -Wl,-E` 链接后 `dlopen(module, RTLD_NOW)`；构造函数的
   `ast_module_register()` 被桩记录，断言注册恰好一次、且
   `struct ast_module_info` 合法（name=`res_config_ldap`、description 非空、
   load/unload 存在）。5 项全部通过：

```
[ok]   dlopen(RTLD_NOW) succeeded — all shared libraries resolved
[ok]   module constructor called ast_module_register exactly once
[ok]   registered module name = 'res_config_ldap'
[ok]   module description = 'LDAP realtime interface'
[ok]   load/unload entry points and license key present
DYNAMIC LOAD TEST PASSED
```

`RTLD_NOW` 的即时绑定使成功即证明：OHOS 加载器能解析该模块**全部**依赖
（libldap.so.2 / liblber.so.2 / libc，含 musl 的 `__strlen_chk`/`__strchr_chk`）。

## 已知限制

1. 只打包 `res_config_ldap.so`，不含 asterisk 主程序与其余模块；运行时需与
   `archives/a/asterisk`（核心）配合使用。
2. 上游 in-tree 用例（**全树 707 个**，源码清点口径）未执行——它们需要以
   `-o asterisk/*:with_test_framework=True` 构建的核心与运行中的 PBX，超出本
   模块包范围（口径与分布见 `reports/upstream-tests.md`）。
3. 模块未被 ELF 签名：模块由 asterisk 进程在加载期 `dlopen`，实测本环境无需
   签名即可加载（动态加载测试通过）；核心包对主程序及其捆绑库做签名。

## 复现

```bash
conan create archives/a/asterisk-ldap/22.10.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd
```

`conanfile.py` 修改后先 `conan remove asterisk-ldap -c`，否则缓存中的旧 binary
会让 `conan create` 直接复用。
---

**编译结束**: 2026-10-10 14:59
**最终状态**: built
