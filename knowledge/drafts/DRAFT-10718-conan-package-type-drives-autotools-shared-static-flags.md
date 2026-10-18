# DRAFT-10718：包型一个字段，把 autotools 构建从"共享+静态"降级成"纯静态"

> Contributor: Lee-BX | Status: Draft | Updated: 2026-10-14
> Source: slurm-wlm 25.11.4 HarmonyOS PC 适配（`archives/s/slurm-wlm/25.11.4`）
> 对应：`knowledge/drafts/DRAFT-10718-conan-package-type-drives-autotools-shared-static-flags.kv`
> 相关：DRAFT-12592（application 包型让 CMakeDeps 不传播 headers/libs —— 同一条轴的另一面）

## 现象

slurm-wlm 25.11.4 的配方在 `package_type = "application"` 时 `conan create` 全绿；
为了让消费者的 CMakeDeps 变量正常（依据 DRAFT-12592 的建议），把包型改成 `"library"` 后，
同一个配方立刻在**与包型毫无字面关联**的地方失败：

```text
libtool: warning: Linking the shared library lib_ref.la against the static library .../libmusl_account_shim.a is not portable!
libtool: link: ar cr .libs/lib_ref.a /…/libmusl_account_shim.a        # ← 只有这个成员，help.bino 不见了
ld.lld: error: undefined symbol: _binary_help_txt_start
>>> referenced by options.c:241 (…/src/sacct/options.c:241)
clang-15: error: linker command failed with exit code 1
make[3]: *** [Makefile:633: sacct] Error 1
```

同时（另一条更隐蔽的后果）单元测试开始报"找不到插件"：

```text
topo-test: error: plugin_load_from_file: dlopen(.../certgen_script.so): Error relocating ...: slurm_get_log_level: symbol not found
serializer-test: fatal: serializer_required: could not find plugin for application/json
```

## 根因

Conan 的 `AutotoolsToolchain` 会把**计算出来的包类型**翻成 autotools 开关：

```python
# conan/tools/gnu/autotoolstoolchain.py（2.29.1）
if self._conanfile.package_type is PackageType.SHARED:
    args.extend(["--enable-shared", "--disable-static"])
elif self._conanfile.package_type is PackageType.STATIC:
    args.extend(["--disable-shared", "--enable-static"])
```

`package_type` 由 recipe 的 `package_type` 属性 + `options["shared"]` 共同判定：
`package_type="library"` + `shared=False` → `PackageType.STATIC`。
于是 configure 实际收到 `--disable-shared --enable-static`：

```text
$ grep -m1 "  \$ .*configure" <build>/config.log | tr ' ' '\n' | grep -E "shared|static"
--disable-shared
--enable-static
$ grep -m1 "^enable_shared" <build>/config.status
enable_shared='no'
$ grep -m1 "^build_libtool_libs" <build>/libtool
build_libtool_libs=no          # ← 生成的 libtool 脚本被"降级"
```

`build_libtool_libs=no` 带来两个连锁反应：

### ① 可加载模块（插件 .so）根本不产出

autotools 里 `pkglib_LTLIBRARIES` + `-module` 的插件（slurm 的 `lib/slurm/*.so`：
`sched/backfill`、`select/cons_tres`、`serializer/json` …）在纯静态模式下只产出 `.a/.o`：

```text
$ ls <build>/src/plugins/serializer/json/.libs
serializer_json.a  serializer_json.la  serializer_json.lai  serializer_json.o     # 没有 .so
```

运行时按 `PluginDir` 找插件、校验目录、`dlopen` 的代码路径随之失败，
但报错是"目录不存在/找不到插件/无法解析配置"，完全不提包型。

### ② "二进制 blob 伪 .lo" 的归档丢成员

slurm 用这套技巧把帮助文本塞进程序：

```make
help.bino: help.txt
	ld -r -o help.bino -z noexecstack --format=binary help.txt
	objcopy --rename-section .data=.rodata,alloc,load,readonly,data,contents help.bino
lib_ref.lo:            # 手写"伪 .lo"骗过 libtool
	echo "pic_object='help.bino'" >> lib_ref.lo
```

`build_libtool_libs=yes` 时 libtool 会把 blob 放进便捷归档：

```text
libtool: link: ar cr .libs/lib_ref.a help.bino usage.bino     # ✅
```

`build_libtool_libs=no` 之后同一条规则只剩其它参数：

```text
libtool: link: ar cr .libs/lib_ref.a <别的参数>                # ❌ blob 不在成员里
```

于是 `sacct` 链接报 `_binary_help_txt_start/_end` 未定义。

## 与 DRAFT-12592 的取舍

| 结论 | 出发点是 | 适用条件 |
|------|----------|----------|
| DRAFT-12592：双形态包用 `package_type="library"` | 让 CMakeDeps 正常传播 headers/libs | 构建能被 `--disable-shared/--disable-static` 影响而**不坏** |
| 本条：保留 `package_type="application"` | 保住 autotools 自身的 `enable-shared=yes` | 产物里有 `-module` 插件 / 依赖 blob 伪 `.lo` / 需要 .a+.so 并存 |

**以产物形态为准**：先 `ls` 插件目录确认是否真的需要 `.so`，再决定包型。
若两者都要（既要 CMakeDeps 传播、又要插件 .so），第三种选择是"与产物一致的包型"
（只发共享库 → shared-library 包型）或显式追加 `--enable-shared --enable-static` 覆盖。

## 判定流程

```sh
# 1) 包型是否被翻译成了开关
grep -m1 "  \$ .*configure" <build>/config.log | tr ' ' '\n' | grep -E "shared|static"
# 2) 生成的 libtool 结论
grep -m1 "^build_libtool_libs" <build>/libtool ; grep -m1 "^enable_shared" <build>/config.status
# 3) 插件 .so 是否产出
ls -d <build>/src/plugins/*/*/.libs ; ls <build>/src/plugins/serializer/json/.libs/*.so
# 4) blob 归档成员
grep -m1 "ar cr .libs/lib_ref.a" <构建日志>
```

## 处置

```python
class SlurmWlmConan(ConanFile):
    # 保持 application：Conan 不会注入 --disable-shared/--enable-static，
    # autotools 走自身默认（enable-shared=yes），一次构建同时得到 .a 与插件 .so
    package_type = "application"
```

代价：application 包型下 CMakeDeps 不传播 include/libs（DRAFT-12592），
在 `test_package` 里显式指向依赖的 `package_folder`（include/lib）即可，
消费者用例的真实性不受影响。

## 实测证据（slurm-wlm 25.11.4）

| 配置 | configure 开关 | 插件 .so | sacct 链接 | conan create |
|------|----------------|----------|-----------|--------------|
| `application`（现配置） | 无（enable_shared=yes，实测） | ✅ `serializer_json.so`/`serializer_yaml.so` 产出 | ✅ | ✅ rc=0 |
| `library` + `shared=False` | `--disable-shared --enable-static` | ❌ 只有 `.a/.o` | ❌ `_binary_help_txt_start` 未定义 | ❌ rc=1 |

## 通用化建议

1. 看到 autotools 包"某些 .so 没被构建"或"以二进制 blob 注入符号的程序链接失败"，
   先 `grep` 一下 configure 的实际开关与生成的 `libtool` 里 `build_libtool_libs` 的值。
2. 包型（package_type）不是"元数据噪音"，它会真实改变 autotools 的 configure 参数；
   改包型前后都要重新看一眼 configure 命令行。
3. 当知识库里的包型建议与本包产物形态冲突时，以产物为准，并把取舍写进配方注释与 notes，
   避免后来者再改一次。
