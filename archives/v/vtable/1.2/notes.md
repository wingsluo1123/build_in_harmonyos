# vtable 1.2 适配笔记

## 1. 任务身份与源码

| 项 | 值 |
|----|----|
| 任务 slug | `vtable` / `1.2`（分支 `feat/vtable-1.2`，归档 `archives/v/vtable/1.2`） |
| 上游项目 | vtable-dumper 1.2 — <https://github.com/lvc/vtable-dumper> |
| 源码 | `https://github.com/lvc/vtable-dumper/archive/1.2/vtable-dumper-1.2.tar.gz` |
| SHA256 | `6993781b6a00936fc5f76dc0db4c410acb46b6d6e9836ddbe2e3c525c6dd1fd2`（16033 字节） |
| 许可证 | LGPL-2.1-or-later（上游 LICENSE 为 GPL/LGPL 双授权文本） |
| 主体语言 | C（`dump-vtable.c` 单文件，`lang-preflight` detected=c，cap=cpp 属兼容族） |
| 构建系统 | 手写 Makefile（无 configure/CMake） |

**命名的由来**：平台任务 slug 为 `vtable`，而上游项目名为 `vtable-dumper`。
按 PF9（分支名 = `<包名>-<版本>`）与 PF8（目录/配方 slug 一致性），本仓以
`vtable` 作为 Conan 包名与目录名，可执行文件保持上游真名 `vtable-dumper`。
上游身份经多源核对确认：Debian/Ubuntu/Arch/AUR/GNU Savannah/GitHub/PyPI/
npm/crates 中不存在名为 `vtable` 的 C/C++ 项目，唯一「C 项目 + 版本恰为
1.2」者是 lvc/vtable-dumper（Debian 源包 `vtable-dumper` 1.2-1.1 亦为其打包）。

## 2. 依赖（W0）

| 依赖 | 来源 | 验证 |
|------|------|------|
| libelf（`-lelf`） | Conan `elfutils/0.195.1` | ① recipe：`conan download elfutils/0.195.1 -r=ohpcd --only-recipe` 成功（rev `3c192719548b0d1405043678479578f6`）；② binary：`conan install --requires=elfutils/0.195.1 -r=ohpcd --build=never` 在 `ohos-aarch64` profile 下直接取得预编译包（pkgid `6e5dfa2a619f0274f77c7d1c368d12d9916309f4`），未触发源码重建 |
| libdl（`-ldl`） | 工具链 sysroot | `sysroot/usr/lib/aarch64-linux-ohos/libdl.a` 存在（空归档）；`dlopen/dlsym` 由 `libc.so` 提供，产物 `DT_NEEDED` 中无 libdl |
| libstdc++（`-lstdc++`） | **不可用**，OHOS 使用 libc++ | 上游 Makefile 硬编码 `-lstdc++`；OHOS 工具链提供 `libc++`（`libc++_shared.so`），产品 `DT_NEEDED` 为 `libc++_shared.so` |
| zstd（传递依赖） | Conan（elfutils 的 requires） | `libelf.so.1` 的 `DT_NEEDED` 含 `libzstd.so.1`，系统仅有 `libzstd.z.so`，故必须由 Conan 依赖链提供并在链接期写入 rpath |

## 3. 补丁（1 个）

`patches/0001-Makefile.patch`（portability）

- **根因**：上游 Makefile 第 11 行把 C++ 运行时写死为 `-lstdc++`，而 OHOS 工具链
  只提供 libc++；`__cxa_demangle`（源码 196 行 `extern` 声明，注释即写作
  "from libstdc++"）在 libc++ 中同样导出，缺的只是库名。
- **改法**：新增 `CXXLIB ?= -lstdc++` 变量并在链接行引用 `$(CXXLIB)`。
  **补丁本身不改变上游默认值**（未指定 `CXXLIB` 时仍为 `-lstdc++`）；
  本配方在 `build()` 中无条件覆盖为 `CXXLIB="-lc++"`——本仓只面向
  OHOS（`ohos-aarch64` profile），故不按平台分支取值。make 命令行变量，
  不修改源码逻辑、不引入平台宏，符合 R8 与 PF5）。
- 生成方式：`ohc-run.py refresh-patch --auto`（未手写 diff，R2/R3）。

## 4. 构建要点

```python
compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
cc = (compilers or {}).get("c", "clang")          # R33（取 dict 再取键；带 :c 后缀的键会抛 ConanException）
CFLAGS  = "-fPIC -O2 -I<elfutils include ...>"
LDFLAGS = "-L<dep lib ...> -Wl,--disable-new-dtags -Wl,-rpath,<dep lib ...>"
make -j1 CC=$cc CFLAGS=... LDFLAGS=... CXXLIB="-lc++"
```

- **rpath 为何用 `--disable-new-dtags`**：默认生成的 `DT_RUNPATH` 只作用于
  可执行文件自身的 `NEEDED`，不参与解析 `libelf.so.1` 的 `NEEDED`
  （`libzstd.so.1`）。改生成 `DT_RPATH` 后可执行文件的 rpath 会被继承到依赖
  链，实测：清空 `LD_LIBRARY_PATH` 后 `vtable-dumper -dumpversion` 与
  dump 全部正常（见第 6 节 C2）。
- **系统同名库核查（R26）**：设备 `/lib64/libelf.so` 的 SONAME 为 `libelf.so`
  （不是 `libelf.so.1`），且 `readelf --dyn-syms` 显示其未导出
  `gelf_getshdr` / `gelf_getsym` / `elf_version` 等符号，与 elfutils 的
  `libelf.so.1` 不构成加载歧义；本质是应用程序包，不产出会污染
  `/lib`、`/lib64` 的库文件，故无需静态化。
- **未采用静态链接**：`libelf.a` 静态链接会再拉入 zlib（实测
  `undefined symbol: deflateInit_`，来自 `elf_compress.o`），静态面会扩散到
  zlib/系统库，故保留动态链接 + rpath。

## 5. 上游测试清点（R51 第一步）

上游 tag 1.2 官方 tarball 共 6 个文件：

```
INSTALL  LICENSE  Makefile  README  dump-vtable.c  dump-vtable.h
```

- 无 `tests/` 目录、无 `test*.c`、无 CI 配置、无测试框架依赖；
- `Makefile` 目标仅 `all` / `install` / `uninstall` / `clean`；
- 实测 `make -n check` → `make: *** No rule to make target 'check'.  Stop.`

**结论：上游官方测试 = 0 项**（PR 的「上游库测试用例统计」按 0 如实填写，
不做任何反填）。功能验证由 `test_package/test.sh` 的 13 项消费者断言承担。

## 6. 消费者端到端测试（规则 12）

用例 **E2E-VTABLE-1**：`test_package/test.sh`（源码 `test.sh` +
`vtable_consumer.cpp`）。

- 用户场景：拿到安装后的 `vtable-dumper`，对一个真实的 C++ 共享库导出其
  虚函数表，确认工具能正确识别多态类的 vtable。
- 真实输入：`vtable_consumer.cpp` 定义两个多态类（`Document` 基类、
  `Invoice` 派生类，含覆盖与派生类专有虚函数），测试时用工具链真实编译成
  `libvtable_consumer.so`。
- 操作流程：`-dumpversion` → 编译消费者库 → `vtable-dumper ./libvtable_consumer.so`
  → 断言输出内容 → `-mangled` 模式复测 → 非 ELF 输入反例。
- 预期业务输出：`Vtable for Invoice` / `_ZTV7Invoice: 7 entries` 且逐行槽位
  数与 7 一致、成员函数 demangle 为 `Invoice::lineCount() const` 等；
  `Vtable for Document` / `_ZTV8Document: 6 entries` 同理。
- 判定依据：**输出内容**（该工具失败时也返回 0，退出码不可作为判据，已在
  C11/C12 用非 ELF 输入反证）。
- 运行方式：`conan create` 在本机（HarmonyOS PC / OHOS aarch64 原生构建，
  build=host=目标机）自动执行 `test_package`。

## 7. 关键实测记录

| 命令 | 结果 |
|------|------|
| `clang -fPIC -O2 -I<elfutils>/include -o vtable-dumper dump-vtable.c -L<elfutils>/lib -lelf -ldl -lc++` | rc=0；`DT_NEEDED`: `libelf.so.1`、`libc++_shared.so`、`libc.so` |
| `make -n check` | `No rule to make target 'check'`（上游无测试目标的实证） |
| `vtable-dumper -dumpversion` | `1.2` |
| `vtable-dumper ./libvtprobe.so` | `Vtable for Circle` / `_ZTV6Circle: 7 entries` 等，rc=0 |
| `vtable-dumper ./notelf.txt` | 输出 `Failed to read v-tables`（stdout），**rc 仍为 0** |
| `env -u LD_LIBRARY_PATH vtable-dumper -dumpversion`（RPATH 方案） | `1.2`，无缺失库报错 |

## 8. 已知限制

- 工具自身在错误输入下也返回 0（上游行为，未修改）；调用方需检查输出内容，
  本测试已按此断言并在 MANIFEST.yml 中说明。
- `-demangled` / `-mangled` 的输出依赖目标库能被 `dlopen`：目标库自身的
  依赖需可解析（上游 README 亦提示使用 `LD_LIBRARY_PATH`）。
---

**编译结束**: 2026-10-16 01:02
**最终状态**: built
