# 纯 Makefile（无 configure）项目在 14 步驱动 Step5 必报「安装无产物」：prefix 与 install(1) 两层错位

> Draft: `DRAFT-DTE-191-RAW-MAKEFILE-DRIVER-DESTDIR-PREFIX`
> Stem: `dte-1.9.1-raw-makefile-driver-destdir-prefix` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-DTE-191-RAW-MAKEFILE-DRIVER-DESTDIR-PREFIX
- **严重度**: 2
- **类别**: build-system|packaging|ohos-platform
- **触发工具**: ohc|make|sh
- **阶段**: installation|packaging
- **实证**: dte 1.9.1（2026-10-08，OHOS aarch64，clang 15.0.4）

## 错误特征（稳定签名）

第一层（前缀错位）——`make install` 明明成功，驱动仍判失败：

```
make: *** No rule to make target 'install-binPROGRAMS'.  Stop.      ← 三段 fallback 的第一段，属干扰信息
 INSTALL  …/test-install-dte-1.9.1/usr/local/bin/dte                  ← 实际装到了 $DESTDIR/usr/local
 ❌ 安装无产物 (staging: …/test-install-dte-1.9.1/storage/Users/currentUser/usr/local)
 ❌ 安装无产物
[13:46:05] ═══ [5/14] make install (DESTDIR mode) ═══
```

第二层（install(1) 缺席）：

```
make: install: No such file or directory
make: *** [GNUmakefile:30: install] Error 127
```

| 观测点 | 读数 |
|--------|------|
| `which install`（默认 PATH） | 不存在（PATH 不含 `/bin`，toybox 版只在 `/bin/install`） |
| `make install DESTDIR=<tmp>` 后产物 | `<tmp>/usr/local/bin/dte`（上游默认 prefix） |
| 驱动检查路径 `staging_prefix` | `<tmp>/<HOME>/usr/local`（$DEFAULT_PREFIX 展开） |
| 修后（`export prefix=$DEFAULT_PREFIX`） | `Step5 ✅ 安装完成: bin=1 lib=0` |

## 根因

驱动的 Step5 为 autotools 而写：`configure --prefix=$DEFAULT_PREFIX` 把绝对前缀烧进二进制，
`DESTDIR + prefix` 因此落在 `staging_prefix = test_prefix/<DEFAULT_PREFIX 去掉前导 />`。
纯 Makefile 项目没有 configure，`make install` 走上游自带的 `prefix ?= /usr/local`，两者的拼接结果
天然对不上。叠加 `$(INSTALL)` 依赖一个不在 PATH 里的 `install(1)`，三段 fallback 全部落空，
最终以 `RuntimeError("安装无产物")` 结束并 exit 2。

关键杠杆：**GNU make 把来自环境的变量视为已定义**，上游的 `prefix ?= …` 不再覆盖它 ——
所以无需改上游 makefile、无需补丁，一个环境变量即可把安装前缀对齐。

## 已尝试方案（含失败）

1. ❌ 只加 install shim（`ln -s /bin/install` 垫 PATH）：`make install` 成功了，产物仍在
   `$DESTDIR/usr/local/bin`，驱动照旧报「安装无产物」——证明两层是独立的，缺一不可。
2. ❌ 照模板把 `LDLIBS`/`LDFLAGS` 当万能注入点：与本题无关（那是链接期问题），不解决安装路径。
3. ✅ `export prefix=$DEFAULT_PREFIX` + PATH 垫 `install` shim ⇒ Step5 `bin=1` ✅。
4. ✅ 配方侧彻底规避 install(1)：`package()` 手工 `copy()` `bin/dte` 与三个 man 页面再 `chmod 0755`
   ——CI worker 同样没有 install(1)，这条才是能进 CI 的正解。

## 推荐方案

**方法**: `env-prefix-injection-plus-install-shim-plus-manual-package-copy`

1. `export prefix=$DEFAULT_PREFIX`（驱动侧，仅影响本地 Step5；`?=` 不覆盖环境变量）。
2. 任务级 shim 目录 `ln -s /bin/install <shim>/install` 并置于 PATH 最前 —— ⛔ 不要写 `~/usr/local/bin`
   （基础设施区，需用户授权）。
3. 配方 `package()` 用 `copy()` + `os.chmod(0o755)` 复刻 install 布局，不依赖 `install(1)`。
4. `CC` 显式传（裸 `make` 解析到 make 内建 `cc`，本机没有）——该子坑已有既有条目，本文只引用。

## 影响范围 / 反例 / 解除条件

- **适用**：上游只有 `GNUmakefile`/`Makefile`、无 `configure`、install 目标按 `$(prefix)` 展开的包。
- **反例（不适用）**：autotools/CMake 项目 —— 它们在 configure 阶段就吃掉 `--prefix`/`-DCMAKE_INSTALL_PREFIX`，
  天然与 staging_prefix 对齐；有独立 `PREFIX=` 变量命名的包（如 abduco 的 `PREFIX=`）也不受影响。
- **解除条件**：上游哪天提供 configure 或把 prefix 作为命令行必填项，本机制自动失效。
- **风险**：`prefix` 是常见环境变量名，若机器上恰好残留其他任务的 `prefix` 值会串味 ——
  一律在起驱动的脚本里显式 `export prefix="$DEFAULT_PREFIX"`，不要靠继承。

## 查重与新增价值

四范围查重（2026-10-08）：

- **范围1** `经验文档/适配经验汇总.md`（按编号检索「安装无产物 / DESTDIR / staging_prefix」）：仅命中 header-only
  场景的「无产物」讨论，无 raw-makefile 驱动期症状。
- **范围2** `knowledge/graph/index.tsv`（768 条）：`E392 raw-makefile-conan-recipe-pattern` 覆盖的是
  **conan 配方侧** raw-makefile 写法（cwd/source_folder/build_folder、install、copy），
  `E098/E108` 覆盖 `install`/`ginstall` 不可用，`E317/E336/E491` 覆盖 DESTDIR 布局 —— **均未覆盖
  「驱动 Step5 的 staging 前缀与上游默认 prefix 错位 ⇒ 环境变量注入」这一症状**。
- **范围3** `经验库/14-最终防错清单.md`、`适配检查清单.md`（Makefile 段 #1/#2/#3）、`手册/07`：
  Makefile 段要求「显式传 CC」「无 install 目标时手工 copy」，但没有「有 install 目标却因
  install(1) 缺席 + 前缀错位而失败」的完整因果链。
- **范围4** `OHOS行为探针清单.md`：探针 #5（pty/termios）由本任务实测**无偏差**
  （`openpty`/`tcgetattr`/`TIOCGWINSZ`/`TIOCSCTTY`+`/dev/tty` 全部符合 glibc 语义），与本条无重叠。

**本 PR 另复用的既有知识**（不另立条目，符合「一 PR 一知识」）：
`E503`（`--version`/`--help` 长选项补丁，libubox jshn 先例）——本包 `src/main.c` 照此补了
`argc == 2` 形态的长选项别名，Step8 staging 冒烟与 CI L2 因此转绿；
`E098/E108`（install 不可用族）、检查清单 Makefile 段 #1（CC 显式）、
`经验库 12b`（`tools.build:compiler_executables` 子键读取必须整读 dict）均已在本任务命中并复用。

**新增价值**：给出**驱动期（而非配方期）**的完整因果链与三步修法，让后续每一个 raw-makefile 任务
不必再烧一轮 Step5 才明白「安装成功 ≠ 驱动认账」。

## 关联

- **知识库扩展 Issue**: #3842 — https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3842
- **实证任务**: dte 1.9.1（同 PR 内成对交付 `.kv`/`.md`）
