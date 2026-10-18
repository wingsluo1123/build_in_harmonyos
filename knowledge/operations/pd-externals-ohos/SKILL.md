# SKILL: Pure Data 外部库 OHOS 适配（pd-externals-ohos）

> 版本 1.0.0 · 适用 Conan 2.x + 鸿蒙 PC（OHOS aarch64）三方库适配流程
> 定位：把「上游 Pd 外部库（pd-lib-builder）在 OHOS 上**必然失败**」，
> 提前成**一次静态/日志检测 + 一段可直接复制的配方片段 + 一套可断言的消费者测试**。

## 1. 一句话说明

Pd 外部库（`.pd_linux`）由 pd-lib-builder（`Makefile.pdlibbuilder`）构建，它在配置期
用 `$(CC) -dumpmachine` 探测目标三元组、默认 `CC = $(PLATFORM)-cc|gcc`。
OHOS 目标机**没有 `cc`/`gcc`**（只有内置 clang），因此在编译任何源码之前就硬失败：

```
Makefile.pdlibbuilder:764: *** Command "cc -dumpmachine" did not return a target triplet,
needed for a build.  Is compiler "cc" installed in your PATH?
```

即便绕过编译器，`PDINCLUDEDIR` 也必须指向**含 Pd 内部头的头集**（`s_stuff.h`、`g_canvas.h`、
`m_imp.h`、`x_vexp.h`）——仓内 `libpd` 包只装 `include/libpd`，**缺 `s_stuff.h`**，
用它会得到 `fatal error: 's_stuff.h' file not found`。外部对象由 Pd 宿主 dlopen，
因此消费者侧还有第三层：musl 下 `libpd.so` 的符号必须进入进程全局域。

本 SKILL 做三件事：**检测**（`scripts/pd_external_guard.py`）→ **处方**（`templates/` 三份）
→ **复现验证**（`scripts/reproduce_poc.sh` 双态）。

## 2. 触发场景（何时该用它）

| 触发 | 具体表现 |
|---|---|
| 源码特征 | 仓库根有 `Makefile.pdlibbuilder`（或 `pd-lib-builder/`），`Makefile` 里有 `lib.name =` / `class.sources =` / `PDLIBBUILDER_DIR` |
| 构建日志 | `Command "cc -dumpmachine" did not return a target triplet`、`Makefile.pdlibbuilder:NNN: ***` |
| 编译日志 | `fatal error: 's_stuff.h' file not found`（头集来源选错，如用了 libpd 包） |
| 消费者日志 | `Error relocating …: pd_error: symbol not found` / `gensym: symbol not found` |
| 宿主日志 | `vbap: couldn't create`（产物未加载或 setup 符号缺失） |
| 上游测试 | `unittests/*.pd` 依赖 `testtools/unit-test-frame` 与 GUI 宿主，CI 无 |

## 3. 检测（自动识别，无需人工干预）

```bash
G=knowledge/operations/pd-externals-ohos/scripts/pd_external_guard.py

# ① 构建日志 → 变体 + 处方（退出码 2=命中，0=未命中）
python3 "$G" log <build.log>
python3 "$G" log <build.log> --json

# ② 上游源码目录 → 是否 Pd 外部库（pd-lib-builder 特征 + <name>_setup 符号）
python3 "$G" source <src_dir>

# ③ 配方目录 → RISK（未注入 CC/PDINCLUDEDIR）/ GUARDED / NOT_PD_EXTERNAL
python3 "$G" recipe archives/p/pd-vbap/1.2.1

# ④ 自检与策略表
python3 "$G" selftest
python3 "$G" policy
```

**变体判定表**：`A`=编译器/三元组（主签名）· `B`=Pd 头集缺失 · `C`=消费者符号作用域（musl）·
`D`=宿主加载失败 · `-`=仅确认走 pd-lib-builder（需结合 A/B/C/D）。

## 4. 处理策略（按变体选，可组合）

| 变体 | 策略 | 落点 |
|---|---|---|
| A 编译器 | 配方内**显式**传 `CC`（取 Conan 的 clang，R33 禁止裸用 shell 变量）+ `-j1`（E525） | `templates/pdlibbuilder_make_snippet.py` |
| B 头集 | `PDINCLUDEDIR = <puredata 包>/include/pd`；**不要用 libpd 包**（缺 `s_stuff.h`）；puredata 的 `cpp_info.includedirs` 为空，须用 `package_folder` 拼 | 同上 |
| C 消费者 | 测试程序不链接 libpd：运行时 `dlopen(libpd.so)`+`dlsym`，运行步注入 `LD_PRELOAD=<libpd.so>`（编译/链接步禁注入依赖库目录） | `templates/consumer-libpd-test.md.tmpl` |
| D 宿主加载 | 产物与 `*.pd` 同目录（Pd 优先搜补丁自身目录）；确认 `<name>_setup` 存在 | 同上 |
| 不可解 | 仅 Max/MSP 专属实现、需 GUI 图形栈等 → 按规范标记（含证据） | `templates/env-unsupported-marker.md.tmpl` |

## 5. 复现与双态验证

```bash
bash knowledge/operations/pd-externals-ohos/scripts/reproduce_poc.sh
#   --only naive|guarded       只跑单态
#   --src <已解压源码目录>      复用已解压源码（默认按 codeload 下载样例库）
#   --work <工作目录>           指定工作目录（默认 $TMPDIR 下）
```

| 态 | 语义 | 期望 |
|---|---|---|
| 态 1 | 裸 `make`（无 CC/PDINCLUDEDIR，等价未适配） | 失败，且检测器 `log` 能自动识别（退出码 2，变体 A） |
| 态 2 | `make -j1 CC=clang PDINCLUDEDIR=<puredata>/include/pd` | 产出三个 `.pd_linux`，检测器判 `CLEAN` |

脚本自带：可写 `TMPDIR`、日志**全部重定向到文件且脚本内无任何管道**（规避 SIGPIPE 与 `| head`
截断）、仓库根与工作目录由**脚本位置**推导（无写死绝对路径），Pd 头集用
`conan install --requires=puredata/0.54.1 --deployer=full_deploy` 落地后再自适应定位 `include/pd`。

## 6. 自测

```bash
python3 knowledge/operations/pd-externals-ohos/tests/test_pd_external_guard.py
```

覆盖：日志三分支（A/C/干净）判定与退出码、源码模式正负样例（Pd 外部库 vs 普通 C 程序）、
配方模式 RISK/GUARDED 及缺失项、`selftest` 内置用例。

## 7. 限制与不适用场景

- **不含 Pd 宿主本体适配**：`puredata` / `libpd` 自身的适配不在本 SKILL 范围（只作为依赖使用）。
- **不解决取源问题**：源码拉取失败属 `conan-source-fetch-compat`（TLS/反爬）那一类。
- **不解决依赖未发布**：`dependency_missing` 走依赖链流程（R36）。
- **不替代上游测试**：上游 `.pd` 单测需要 `testtools/unit-test-frame` + GUI 宿主，
  本 SKILL 提供的是 libpd headless 消费者测试（可断言数值），两者关系见模板第 5 节。
- **LD_PRELOAD 只限运行步**：生产构建/编译/链接步骤不得注入依赖库目录（铁律）。
- **仅 Max/MSP 专属实现不可适配**：需按模板留证据，不硬猜。

## 8. 文件清单

```
knowledge/operations/pd-externals-ohos/
├── SKILL.md                                    本文件（技能入口）
├── README.md                                   完整文档：问题画像/适用库范围/检测逻辑/复现/样例结果
├── scripts/pd_external_guard.py                ① 检测器（log / source / recipe / policy / selftest）
├── scripts/reproduce_poc.sh                    ③ 复现脚本（双态：裸 make 失败 / 适配后成功）
├── templates/pdlibbuilder_make_snippet.py      ② 策略 A+B：配方片段（CC + PDINCLUDEDIR）
├── templates/consumer-libpd-test.md.tmpl       ② 策略 C+D：消费者测试规范（含 musl 作用域实测表）
├── templates/env-unsupported-marker.md.tmpl    ② 不可适配时的标记规范与证据要求
└── tests/test_pd_external_guard.py             自测（fixtures：naive 源码 / 干净日志 / 消费者日志）
```
