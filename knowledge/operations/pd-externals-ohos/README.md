# pd-externals-ohos — Pure Data 外部库 OHOS 适配（一类共性问题的知识库拓展）

> 拓展日期：2026-10-01 · 工具链：OHOS clang 15.0.4（`/data/service/hnp/bin/clang`，target `aarch64-unknown-linux-ohos`）
> 样例库：`archives/p/pd-vbap/1.2.1`（本 PR 的适配产物） · 依赖包：`puredata/0.54.1`（`6b129b06…`）、`libpd/0.16.1`（`01d92cf3…`）

## 1. 这是什么

把「**上游 Pd 外部库（用 pd-lib-builder 构建）在 OHOS 上必然失败**」这一反复出现的适配问题，
固化成可复用的一类知识：**自动识别（检测器）+ 现成处理策略（配方片段/消费者测试规范）+ 可复现验证（双态脚本）**。

对标先例：`skills/conan-source-fetch-compat`（源码取回兼容性类）。

## 2. 问题画像：三级失败链

| 级 | 触发点 | 真实现象（实测） | 变体 |
|---|---|---|---|
| ① 构建系统 | pd-lib-builder 用 `$(CC) -dumpmachine` 探测目标三元组，且默认 `CC = $(PLATFORM)-cc\|gcc`（`Makefile.pdlibbuilder:388/392`）；OHOS 无 `cc`/`gcc` | `make: cc: No such file or directory` → `Makefile.pdlibbuilder:764: *** Command "cc -dumpmachine" did not return a target triplet, needed for a build.` —— **在编译任何源码之前就失败** | A |
| ② 头集 | 外部对象直接 include Pd 内部头（如 `vbap.c:14 #include "s_stuff.h"`）；仓内 `libpd` 包只装 `include/libpd`，**不含 `s_stuff.h`** | `vbap.c:14:10: fatal error: 's_stuff.h' file not found` | B |
| ③ 消费者 | 外部对象的 `class_new`/`gensym`/`pd_error` 等符号由 Pd 引擎提供；musl 下 `dlopen` 的 `RTLD_GLOBAL` 不进入全局符号域 | `Error relocating …/vbap.pd_linux: pd_error: symbol not found`；Pd 控制台 `vbap: couldn't create` | C/D |

三级之间存在依赖关系：① 挡住所有 Pd 外部库；② 是「选错头集来源」的次生问题；③ 只影响消费者测试的构造方式。

## 3. 为什么判定为「一类共性」而不是单库补丁

1. **失败源在共享的 vendored 构建系统文件里**：pd-lib-builder 由上游各外部库**各自 vendor 同一份**
   `Makefile.pdlibbuilder`（样例库与上游 pd 发行版内的版本均为 0.6.0）。失败发生在该文件**解析阶段**
   （`target.triplet := $(shell $(CC) -dumpmachine)`），与宿主库自身的 C 代码无关 → 对生态内所有使用
   pd-lib-builder 的库同构成立（zexy / cyclone / iemlib / iemnet / hcs / …）。
2. **检测器不是「名字匹配」而是「特征匹配」**：识别 `Makefile.pdlibbuilder`（或 `pd-lib-builder/`）、
   `lib.name =` / `class.sources =` / `PDLIBBUILDER_DIR`、以及 `<name>_setup` 符号 —— 换库不必改代码。
3. **本仓现状（如实说明）**：`archives/` 下 `pd-vbap` 是**第一个** Pd 外部库
   （全仓检索 `pdlibbuilder|pd-lib-builder|PDLIBBUILDER_DIR` = 0 命中），因此本拓展的实证样例为
   `pd-vbap 1.2.1`（双态实测见 §6）；同类第二样例 `pd-zexy 2.4.4` 按「一个 PR 一个软件」规则另行适配，
   本 PR 仅打通机制与工具链。**不虚构未验证的同族实测数据。**

## 4. 检测逻辑

```bash
G=knowledge/operations/pd-externals-ohos/scripts/pd_external_guard.py
python3 "$G" log    <build.log>          # 构建/消费者日志 → 变体 + 处方
python3 "$G" source <src_dir>           # 上游源码 → 是否 Pd 外部库（含 setup 符号/头依赖）
python3 "$G" recipe archives/p/pd-vbap/1.2.1   # 配方 → RISK / GUARDED / NOT_PD_EXTERNAL
python3 "$G" policy                     # 打印 A/B/C/D 策略
python3 "$G" selftest                   # 内置正负样例
```

- **退出码约定**：`2` = 命中（需要处理）· `0` = 未命中 · `1` = 用法/IO 错误 → 便于 CI/脚本串联。
- **变体**：`A`（编译器/三元组）· `B`（Pd 头集缺失）· `C`（消费者符号作用域）· `D`（宿主加载失败）·
  `-`（仅确认使用 pd-lib-builder，需结合 A/B/C/D 判定）。
- **误报边界**：变体 `-`（`PDLIBBUILDER_LANDING`）单独命中不判失败；日志模式对「已适配成功的构建」
  返回 `CLEAN`（实测态 2 = `CLEAN / exit 0`）；`source` 模式对普通 C 工程返回 `NOT_PD_EXTERNAL`。

## 5. 处理策略

| 变体 | 策略 | 交付物 |
|---|---|---|
| A | 配方内**显式** `CC`（取 Conan 的 clang；R33 禁止裸用 shell `${CC}`）+ `-j1`（E525） | `templates/pdlibbuilder_make_snippet.py` |
| B | `PDINCLUDEDIR = <puredata 包>/include/pd`；**不要用 libpd 包编译**（缺 `s_stuff.h`）；`puredata` 是 `package_type=application` 且 `cpp_info.includedirs` **为空**，必须 `package_folder` 拼路径 | 同上 |
| C | 消费者测试不链接 libpd：运行时 `dlopen(libpd.so)`+`dlsym`；运行步注入 `LD_PRELOAD=<libpd.so>`（编译/链接步禁注入依赖库目录） | `templates/consumer-libpd-test.md.tmpl` |
| D | 产物与 `*.pd` 同目录（Pd 优先搜补丁自身目录）；确认 `<name>_setup` 存在 | 同上 |
| 不可解 | 仅 Max/MSP 专属实现、需 GUI 图形栈等 | `templates/env-unsupported-marker.md.tmpl` |

`libpd` 与 `puredata` 两个包的能力差异（实测）：

| 包 | 头 | 用途 |
|---|---|---|
| `puredata/0.54.1` | `include/m_pd.h` + `include/pd/{s_stuff.h,g_canvas.h,m_imp.h,x_vexp.h,s_net.h,g_all_guis.h,g_undo.h}`，另有 `bin/pd` | ✅ **编译外部对象**（含 Pd 内部头） |
| `libpd/0.16.1` | `include/libpd/{PdBase.hpp,z_libpd.h,m_pd.h,m_imp.h,g_canvas.h,util/…}`，`lib/libpd.so` | ✅ **消费者测试**（嵌入式引擎，导出 `pd_error`/`gensym`/`libpd_*`）；❌ 不含 `s_stuff.h` |

## 6. 样例库双态实测（`scripts/reproduce_poc.sh`）

```bash
sh knowledge/operations/pd-externals-ohos/scripts/reproduce_poc.sh     # 退出码 0 = 双态均符合预期
```

| 态 | 命令 | 实测结果 |
|---|---|---|
| 态 1 未适配 | `env -u CC -u CXX -u CFLAGS make -j1`（等价干净 CI：无 `CC` 注入） | `make rc=2`；签名行 `Makefile.pdlibbuilder:764: *** Command "cc -dumpmachine" did not return a target triplet…`；检测器 `rc=2` → `VERDICT=PD_EXTERNAL_INCOMPATIBLE`，`variants=A`，`codes=PDLIBBUILDER_CC_NOT_FOUND,PDLIBBUILDER_NO_TRIPLET` |
| 态 2 适配后 | `make -j1 CC=clang PDINCLUDEDIR=<puredata>/include/pd` | `make rc=0`；产出 `define_loudspeakers.pd_linux`(31040B)、`rvbap.pd_linux`(31040B)、`vbap.pd_linux`(43328B)；检测器 `rc=0` → `VERDICT=CLEAN` |

脚本自带约束（可被 `tests/` 静态断言）：`TMPDIR` 可写性检查；**无任何管道**（规避 SIGPIPE 与 `| head` 截断空日志）；
不写死绝对路径（仓库根由脚本位置推导）；源码取自官方源 `codeload.github.com/pure-data/vbap`
（`v1.2.1`，48504B，sha256 `7a754a9c…d6d1` 逐字节校验）；`conan install --deployer=full_deploy` 取 `puredata` 头集；
`--only naive|guarded` 可单跑，`--src` 可指定本地源码。

## 7. 自测

```bash
python3 knowledge/operations/pd-externals-ohos/tests/test_pd_external_guard.py    # 32 项断言
```

覆盖：日志四态（A / B / C / 干净）与混合态优先级、源码模式正负样例（Pd 外部库 vs 普通 C 程序）、
缺失目录的异常路径、配方模式 `RISK`/`GUARDED`/`NOT_PD_EXTERNAL` 与缺失项清单、
`selftest` 内置用例、策略表与签名表完整性、交付物齐备性、复现脚本静态约束（无管道/官源+sha256/无绝对路径/TMPDIR）。
第三方测试的实现细节（libpd 消费者测试的符号作用域实测表）见 `templates/consumer-libpd-test.md.tmpl`。

## 8. 使用方法

1. 拉源码后跑 `pd_external_guard.py source <src_dir>`：命中 → 走本 SKILL 策略，未命中 → 常规流程；
2. 按变体套用 `templates/`：配方片段（A/B）+ 消费者测试规范（C/D）；
3. 适配完成后跑 `reproduce_poc.sh` 与 `tests/`，把 `VERDICT` 与双态结论写进 `notes.md`；
4. 若最终仍不可解，按 `env-unsupported-marker.md.tmpl` 留证据上报（status `env_unsupported`）。

## 9. 与其它知识条目的边界

| 问题 | 归属 |
|---|---|
| 源码站不可达 / 老 TLS / 反爬 | `skills/conan-source-fetch-compat`（不是本类） |
| 依赖包未发布到制品仓 | `dependency_missing` + R36 依赖链流程 |
| 系统同名库动态链接污染 | R26（本类不涉及；外部对象仅依赖 libc） |
| `self.run()` 裸用 `${CC}`/`${CFLAGS}` | R33（本类策略 A 的强制前提） |
| OHOS 并发构建不稳 | E525（策略统一 `-j1`） |

## 10. 限制与不适用

- 不含 `puredata`/`libpd` **自身**的适配（本 SKILL 只把它们当依赖使用）；
- 上游 `.pd` 单测需要 `testtools/unit-test-frame` + GUI 宿主（`puredata` 包不分发该目录，CI 无），
  本 SKILL 给的是 libpd headless 消费者测试，**不替代**上游测试清点（R51 三步法照做）；
- `LD_PRELOAD` **只限运行 e2e 二进制那一步**，生产构建/编译/链接步不得注入依赖库目录（铁律）；
- 仅 Max/MSP 专属实现、需 GUI 图形栈的库 → 按标记模板留证，不硬猜。

## 11. 留档

- 检测器：`scripts/pd_external_guard.py`（log/source/recipe/policy/selftest，纯标准库）
- 复现：`scripts/reproduce_poc.sh`（双态，退出码 0/1）
- 自测：`tests/test_pd_external_guard.py`（32 项）
- 实测留档：态 2 的 `PDINCLUDEDIR=…/full_deploy/host/puredata/0.54.1/Release/armv8/include/pd`
- 知识草稿：`knowledge/drafts/E999-draft-<agent>-pd-externals-ohos.{kv,md}`
