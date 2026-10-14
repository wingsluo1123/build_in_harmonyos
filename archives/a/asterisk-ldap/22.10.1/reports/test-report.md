# 测试报告 — asterisk-ldap 22.10.1（HarmonyOS PC / OHOS aarch64）

> **项目**: asterisk-ldap (asterisk/asterisk, res_config_ldap)
> **测试日期**: 2026-10-10
> **测试环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64（clang 15.0.4 / musl libc）
> **测试类型**: 上游入口核验 + conan create/verify + 消费者静态校验 + 鸿蒙动态加载测试

---

## 一、测试摘要

### 1.1 上游测试入口（核验）

| 指标 | 数值 | 说明 |
|:----:|:----:|:-----|
| 上游测试框架 | in-tree 单元测试 | `tests/CI/buildAsterisk.sh` + `tests/CI/runUnittests.sh` |
| 上游测试模块数 | 95 | `ls tests/test_*.c` |
| **上游用例总数（申报口径）** | **707** | **全树源码清点口径**：`grep -rh "^AST_TEST_DEFINE(" --include="*.c" . \| wc -l` = 707（`tests/*.c` 633 / 95 文件 + `res/main/funcs/bridges/apps` 74 / 25 文件）；与平台实测读数一致 |
| 本模块上游用例数 | 0 | `grep -ril ldap tests/` 仅命中 CI 构建脚本；707 个注册无一涉及 LDAP |
| 上游用例执行情况 | **未执行（N′=0）**（如实声明） | 需完整核心（`-o asterisk/*:with_test_framework=True`）+ 运行中的 PBX；本模块包只构建 res_config_ldap.so，注册用例的源文件不在编译范围内 |

逐文件清点（文件 / 用例数 / 用例名）见 `reports/upstream-tests.md`。
运行命令（针对完整核心构建）：`./sbin/asterisk -rx "test execute all"`。

### 1.2 适配后测试（test_package，13 项检查）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 静态 ELF 校验 | 8 | 100% |
| 动态加载检查（鸿蒙特有） | 5 | 100% |
| 通过 (PASS) | 13 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**通过率**: ✅ **100%**（`conan create` 中 test_package 自动执行）

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。交付物 `res_config_ldap.so` 在 OHOS 上：ELF/动态段结构正确、绑定
OpenLDAP 与 Asterisk 模块 ABI、无构建机路径泄漏，并且**能被 OHOS 加载器以
RTLD_NOW 成功加载并完成模块自注册**。

### 2.2 可用功能清单

```
✅ 编译链接  : res/res_config_ldap.o -> res_config_ldap.so
✅ 打包      : lib/asterisk/modules/res_config_ldap.so（+ LICENSE/COPYING）
✅ 静态结构  : AArch64 ET_DYN / DT_NEEDED libldap+lber / OPENLDAP_2.200
✅ 动态加载  : dlopen(RTLD_NOW) 成功；构造函数 ast_module_register 注册 res_config_ldap
```

### 2.3 已知限制

1. 只打包 LDAP 模块，不含 asterisk 主程序（需与 `archives/a/asterisk` 配合）；
2. 上游 **707** 个 in-tree 用例未执行（N′=0；需完整核心 + 运行中 PBX，见 1.1；未执行的 707 项不宣称通过）；
3. 模块未做 ELF 签名——由 asterisk 进程在加载期 dlopen，实测无需签名即可加载。

---

## 三、测试详情

### 3.1 执行的命令与日志

```bash
# 干净构建 + 消费者测试
conan create archives/a/asterisk-ldap/22.10.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd
# → configure: "checking for mandatory modules: LDAP... ok"
# → [CC] res_config_ldap.c -> res_config_ldap.o
# → [LD] res_config_ldap.o -> res_config_ldap.so

# 配方验证
python3 scripts/ohc-run.py conan-verify asterisk-ldap 22.10.1

# 收尾（含 W3 本地 CI 模拟）
python3 scripts/ohc-run.py finish asterisk-ldap 22.10.1 built
```

日志路径：

- `reports/conan-create.log`（conan create 完整输出）
- `reports/conan-verify-report.md`（G0-G4 + L2/L4/L5）
- `reports/w3-local-ci.log`（W3 本地 CI 模拟）
- `reports/upstream-tests.md`（上游清单取证）

### 3.2 通过的测试（test_package，13 项）

| # | 测试项 | 验证内容 | 结果 |
|:-:|--------|----------|:----:|
| 1 | module packaged at lib/asterisk/modules/res_config_ldap.so | 产物位置 | ✅ PASS |
| 2 | ELF header: AArch64 shared object (ET_DYN) | e_machine=183 / e_type=3 | ✅ PASS |
| 3 | DT_NEEDED contains libldap.so.2 and liblber.so.2 | OpenLDAP 绑定 | ✅ PASS |
| 4 | binds the OpenLDAP API used by res_config_ldap (8 syms) | ldap_initialize / ldap_set_option / ldap_sasl_bind_s / ldap_search_ext_s / ldap_modify_ext_s / ldap_unbind_ext_s / ldap_msgfree / ber_free | ✅ PASS |
| 5 | binds the Asterisk module ABI | ast_module_register / ast_module_unregister | ✅ PASS |
| 6 | DT_INIT_ARRAY present and non-empty | 构造函数自注册机制 | ✅ PASS |
| 7 | no DT_RPATH/DT_RUNPATH | 无构建机路径泄漏 | ✅ PASS |
| 8 | OpenLDAP ABI version OPENLDAP_2.200 is bound | ABI 版本绑定 | ✅ PASS |
| 9 | dlopen(RTLD_NOW) succeeded | OHOS 加载器解析全部依赖（libldap/liblber/libc） | ✅ PASS |
| 10 | module constructor called ast_module_register exactly once | 模块自注册 | ✅ PASS |
| 11 | registered module name = 'res_config_ldap' | 模块身份 | ✅ PASS |
| 12 | module description = 'LDAP realtime interface' | info 结构有效 | ✅ PASS |
| 13 | load/unload entry points and license key present | 模块 ABI 完整 | ✅ PASS |

### 3.3 失败的测试

无。

### 3.4 跳过的测试

无（上游套件不适用本模块——见 1.1，已如实声明而非"跳过"）。

---

## 四、关键问题分析

### 问题 1: `error: function definition is not allowed here`（RAII_VAR）

**现象**：
```
res_config_ldap.c:1037:2: error: function definition is not allowed here
        RAII_VAR(struct ast_variable *, fields, NULL, ast_variables_destroy);
include/asterisk/utils.h:983:42: note: expanded from macro 'RAII_VAR'
    void _dtor_ ## varname (vartype * v) { dtor(*v); }
1 error generated.
```

**根因**：既有 asterisk 模块补丁把 `RAII_VAR` 的 blocks 分支收窄到 `__BLOCKS__`，
clang（未启用 blocks）因此落入 `__GNUC__` 分支，而该分支用**嵌套函数定义**——
clang 不支持。curl/pgsql 等模块不使用 `RAII_VAR` 故未暴露。

**修复**：新增补丁 `0009`，为「clang 且无 blocks」提供
`__attribute__((cleanup))` 版实现（语义同上游：对变量最终值调用 dtor）。

**重新验证**：编译 + 链接通过。

### 问题 2: `ber_free` 未解析（lld 不用传递库解析符号）

**根因**：configure 的 LDAP 检查只给 `-lldap`；`res_config_ldap.c` 直接调用
liblber 的 `ber_free`；lld 默认 `--no-copy-dt-needed-entries`。

**修复**：`LIBS += -llber` + 重写 `makeopts` 的 `LDAP_LIB=-L<prefix>/lib -lldap -llber`。

**重新验证**：产物 `DT_NEEDED` 含 `liblber.so.2`，`ber_free@OPENLDAP_2.200` 由
liblber 在加载期解析（动态加载测试通过佐证）。

---

## 五、测试环境

```
软件版本:   asterisk-ldap 22.10.1 (asterisk/asterisk tag 22.10.1, res/res_config_ldap.c)
构建系统:   autotools（Asterisk 全量 configure + menuselect，只编译 res_config_ldap.so）
编译器:     clang 15.0.4 (OHOS SDK, aarch64-unknown-linux-ohos, musl libc)
依赖:       openldap/2.6.7 + libedit/20240808 + libxml2/2.15.3 + ncurses/6.6
           + e2fsprogs/1.47.4 + jansson/2.15.1.1 + sqlite3/3.49.1
产物:       lib/asterisk/modules/res_config_ldap.so
```

---

*报告生成时间: 2026-10-10*
