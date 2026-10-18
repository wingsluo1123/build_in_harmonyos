# E999（草稿）— Pure Data 外部库（pd-lib-builder）OHOS 适配

> 条目：`E999-draft-B183-pd-externals-ohos` · 严重度 2 · 状态：草稿（待主编 promote）
> 配套技能：`knowledge/operations/pd-externals-ohos/` · 样例库：`archives/p/pd-vbap/1.2.1`

## 1. 现象

Pd 外部库（产物 `<name>.pd_linux`）在 OHOS 上按上游默认方式构建时，会出现三类互不相同但同源的现象：

```
# ① 构建系统层（在任何源码被编译之前就失败）
make: cc: No such file or directory
Makefile.pdlibbuilder:764: *** Command "cc -dumpmachine" did not return a target triplet,
needed for a build.  Is compiler "cc" installed in your PATH?

# ② 头集层（选错头集来源）
vbap.c:14:10: fatal error: 's_stuff.h' file not found

# ③ 消费者层（dlopen 外部对象）
OSError: Error relocating .../vbap.pd_linux: pd_error: symbol not found
# 或 Pd 控制台：vbap: couldn't create
```

## 2. 根因

**① 构建系统**：生态内各外部库各自 vendor 同一份 `Makefile.pdlibbuilder`（0.6.0）。
它按 `target.triplet := $(shell $(CC) -dumpmachine)` 推导平台，且默认 `CC = $(PLATFORM)-cc|-gcc`
（第 388/392 行）。OHOS 目标机**没有 `cc`/`gcc`**（只有内置 clang），`$(shell …)` 取不到三元组 →
第 764 行 `***` 硬失败。失败发生在 Makefile **解析阶段**，与宿主库自身 C 代码无关
→ 对全部使用 pd-lib-builder 的库同构成立（zexy / cyclone / iemlib / iemnet / hcs / …）。

**② 头集**：外部对象要 include Pd **内部头**（`s_stuff.h`、`g_canvas.h`、`m_imp.h`、`x_vexp.h`）。
仓内 `libpd/0.16.1` 只装 `include/libpd/`（**不含 `s_stuff.h`**），`puredata/0.54.1` 才装
`include/pd/` 全套内部头。另外 `puredata` 是 `package_type = "application"`、`cpp_info.includedirs` 为空，
所以路径必须用 `dependency.package_folder + "include/pd"` 拼，不能走 `cpp_info.includedirs`。

**③ 消费者符号作用域**：外部对象**不链接** Pd，`class_new`/`gensym`/`pd_error`/`outlet_new` 等符号由宿主提供。
musl 下 `dlopen` 的 `RTLD_GLOBAL` **不**进入后续 `dlopen` 的全局符号域；已作为 DT_NEEDED 加载的对象
再次 `dlopen(..., RTLD_GLOBAL)` 也不会补登记（实测：链接 libpd 版与运行时 dlopen 版均失败，
`18` 项断言中 `15` 项失败）。唯一有效形态：对**运行步骤**注入 `LD_PRELOAD=<libpd.so>`
（等价宿主自身 `-rdynamic`）→ 实测 `18/18` 通过。

## 3. 适用范围

- 全部以 pd-lib-builder 构建的 Pd 外部库（如上列举）；
- 「把 libpd 当编译依赖」的任何配方（必然踩 ②）；
- 本仓现状：`pd-vbap 1.2.1` 为首个 Pd 外部库（全仓检索 `pdlibbuilder|pd-lib-builder` = 0 命中），
  即本类此前无知识覆盖 —— 正是本拓展要补的缺口。
- 与宿主平台无关（Linux/macOS 同构），但 OHOS 的「无 `cc` + musl + 只读 `/tmp` + 非 bash 环境」
  组合使其成为**必然失败**而非偶发。

## 4. 处理方案

### 主方案：显式注入编译器与 Pd 头集

```python
def build(self):
    dep = self.dependencies["puredata"]
    pd_include = os.path.join(dep.package_folder, "include", "pd")
    # R33：从 conf 取编译器。注意 conf 是整 dict（无 ':c' 子键），
    # 直接取子键会抛 ConanException，须 check_type=dict 取 dict 再取 'c'。
    compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
    cc = compilers.get("c") or "clang"
    self.run("make -j1 CC={} PDINCLUDEDIR={}".format(cc, pd_include), cwd=self.source_folder)
```

- 模板：`knowledge/operations/pd-externals-ohos/templates/pdlibbuilder_make_snippet.py`
- 生产样例：`archives/p/pd-vbap/1.2.1/conanfile.py`
- `-j1` 依 E525；编译器不得裸用 shell `${CC}`（R33：本地会话可能恰好导出 `CC=clang`，CI 干净环境没有）。

### 备方案：消费者测试用运行时加载 + 运行步预载

测试程序不链接 libpd：运行时 `dlopen(libpd.so, RTLD_NOW|RTLD_GLOBAL)` + `dlsym`；
运行 e2e 二进制那一步注入 `LD_PRELOAD=<libpd>/lib/libpd.so` 与 `LD_LIBRARY_PATH=<libpd>/lib`。
**编译/链接子进程禁止注入依赖库目录**（会顶掉 SDK 自带库，lld 崩溃）。

- 规范：`knowledge/operations/pd-externals-ohos/templates/consumer-libpd-test.md.tmpl`

### 不可解时

仅 Max/MSP 专属实现、需 GUI 图形栈等 → 按 `templates/env-unsupported-marker.md.tmpl` 留证
（检测器 `VERDICT` + 干净环境 `conan create` 日志 + 已尝试动作 + 源码行号），status 用 `env_unsupported`。

## 5. 禁止事项

| 禁止 | 缘由 |
|---|---|
| 依赖环境里恰好存在的 `CC`（不注入就 make） | 本地绿 CI 红；CI 干净环境无 `cc` |
| `PDINCLUDEDIR` 指向 libpd | 缺 `s_stuff.h`，失败现象与源码问题混淆 |
| 编译/链接步注入 `LD_LIBRARY_PATH`/`LD_PRELOAD` | 顶掉 SDK 自带库，lld 崩溃 |
| 外部对象写进 `cpp_info.libs` | 插件不是可链接库，消费者 `-lXXX` 必失败 |

## 6. 验证与证据（sample：pd-vbap 1.2.1）

```bash
sh knowledge/operations/pd-externals-ohos/scripts/reproduce_poc.sh      # rc=0 = 双态符合预期
python3 knowledge/operations/pd-externals-ohos/tests/test_pd_external_guard.py
```

| 态 | 命令 | 实测 |
|---|---|---|
| 态 1 | `env -u CC -u CXX -u CFLAGS make -j1` | `rc=2`，命中 `Makefile.pdlibbuilder:764`；检测器 `rc=2` → `PD_EXTERNAL_INCOMPATIBLE`，`variants=A` |
| 态 2 | `make -j1 CC=clang PDINCLUDEDIR=<puredata>/include/pd` | `rc=0`，产出 `define_loudspeakers.pd_linux`(31040B)/`rvbap.pd_linux`(31040B)/`vbap.pd_linux`(43328B)；检测器 `rc=0` → `CLEAN` |

消费者侧证据：`ctypes` 裸 dlopen 失败（`pd_error: symbol not found`）→ 运行步 `LD_PRELOAD=<libpd.so>`
后 18/18 断言通过（含增益平方和、声像方位落点等数值断言）。

## 7. 关联

- 技能入口：`knowledge/operations/pd-externals-ohos/SKILL.md`（完整文档 `README.md`）
- 依赖包：`puredata/0.54.1`（`6b129b06…`，含 Pd 内部头 + `bin/pd`）、`libpd/0.16.1`（`01d92cf3…`，消费者引擎）
- 相邻条目：`E999-draft-B183-conan-source-fetch`（源码取回类；触发面不同，暂不互链）
- 样例库适配归档：`archives/p/pd-vbap/1.2.1/`（notes.md 记录 R51 三步法与消费者测试结论）
