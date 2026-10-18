# swift-toolchain-ohos — OpenHarmony 编译档案（★ 预备件，未落 archives/）

> ★★ **本目录是 `$Q101/prep/` 下的"预备件"，不是已落地的配方。**
> 本轮（locale-r101）**不写目标仓库**（`archives/` 与 `build_in_harmonyos` 任何路径）。
> 落地动作等验收方对 P2 六问的答复（见 `notes.md` 的 PENDING-P2 清单）。
> 依据常设项 **0-129**：预备件与落地件必须物理分离，且任何写入目标仓库的动作都要单独一轮。

## ★ 目录布局（已在预备阶段就按**真实 archives 形状**摆好）

```text
$Q101/prep/
├── README.md                  ← 本档（预备件入口，不落地）
├── notes.md                   ← 落地说明与 PENDING-P2 清单（不落地）
├── crate/                     ← ★ 这一棵**原样**映射到 archives/
│   └── swift-toolchain-ohos/          == archives/s/swift-toolchain-ohos/
│       ├── commands.json              （软件级，R38/L0k）
│       ├── manifest.yaml              （软件级，CI L0e / PF3）
│       ├── README.md                  （软件级）
│       └── 6.0.3/                     == archives/s/swift-toolchain-ohos/6.0.3/
│           ├── conanfile.py           （版本级，G1 八字面量）
│           ├── conandata.yml          （版本级，真 sha256 ＋ URL 占位）
│           ├── notes.md               （版本级门禁对应表）
│           ├── patches/               （恰两条：前门 flag 表 ＋ 载荷绝对路径相对化，见其中 README.md）
│           └── test_package/
│               ├── conanfile.py
│               ├── MANIFEST.yml       （assertion_count = 11）
│               └── test_swift_toolchain.sh
└── patches/                   ← ★ 取材草案 20 个 .patch（**不落地**，供 Foundation/driver 轮）
```

★ **为什么预备件就按真实形状摆**：落地轮的动作退化成一次 `cp -r`，
且 `prep_checks.py` 能对着**与 CI 完全相同的相对路径**跑 G1/PF8/PF9
（`archive_dir` / 版本目录名 / `PF9` 的五段路径判据都依赖相对结构）。


## 软件简介

OHOS 自建 **Swift 6.0.3 工具链**最小集，作为 `tool_requires` 供 Foundation / swiftPM
等下游配方在竞赛 CI（无系统 Swift）中构建使用。

**路径 B（贡献创新）：平台基础设施包，非现成三方库适配。**
同族先例：`archives/r/rust-toolchain/1.97.1`。

**与 rust-toolchain 先例的唯一实质差别**：rust 有官方 dist tarball 可下载；
**OHOS 的 Swift 工具链是我们自建的，上游没有对应发行物** ⇒ 载荷托管位置需要验收方裁定。

## 载荷（最小集十组，r96 §3.1 / r98 冻结）

```text
file bytes   : 189,124,959 B      （单文件；408,000,000 B 上限 ⇒ 余量 53.65%）
sha256       : 922277ac19fe3e2a8ff56c4d5a8ce27c6d3f32cbdf1dfbe2cd872dfbcd2c63b8
unfolded     : 665,087,747 B      （不含生成物 .t2work/；含则为 665,088,207 B）
members      : 3,893              （3,823 regular files + 70 symlinks）
manifest sha : d699ba4262a7baf9b1544a3bcde0c84bc6aec2a009928c240631aa937f24aab3
```

| 组 | 包内路径 | 件数 | 谁会用 |
|---|---|---|---|
| A0 | `env.sh` `swiftc.sh` `build-demo.sh` `VERIFY.py` | 4 | 消费者入口（自定位 wrapper） |
| A1 | `ring/` | 40 | Foundation 平面本体（`plane/lib` 9 库 + `plane/modules` 模块） |
| A2 | `instrument/` | 60 | **交付默认编译器**（`bin/swiftc` 等 20 件） |
| A3 | `hostlibs/host55/` | 68 | 仪器 `RUNPATH[0]` 宿主库 |
| A4 | `toolchain/` | 1,083 | clang 15 / lld / `resource/15.0.4` / `cxx`（libc++） |
| A5 | `sysroot/ohos/` | 1,985 | `-sdk` |
| A6 | `build/swift/lib/swift/` | 89 | Swift 运行时闭包与其模块（`ohos/` 46 件） |
| A7 | `_FoundationCShims` / `icuSources` / `build/dispatch` | 295 | 三个头面 |
| E1 | `example/` | 4 | 自带 demo（`build.sh` `main.swift` `model.swift` `checks.swift`） |
| E5 | `source/libdispatch/` | 265 | 源码面 |

## 门禁自查

一条命令跑规则级门禁自查（`$Q101/src/prep_checks.py`）：

```
python3 $Q101/src/prep_checks.py $Q101/prep --all
python3 $Q101/src/prep_checks.py $Q101/prep --negatives
```

## ★ 消费者义务（三条 —— 违反任一条都会在装载期或运行期死）

1. **编译必须走包根 `swiftc.sh`，不要调裸 `swiftc`。**
   `swiftc.sh` 会在调用方**没有**给的情况下补上 `-sdk` / `-resource-dir` /
   `-tools-directory` / `-I ring/plane/modules` / `-L ring/plane/lib` /
   `-rpath ring/plane/lib` / `-plugin-path ring/plugin`（它从不重复调用方给过的选项）。

2. **链接期与运行期都要能看见 `ring/plane/lib`，且产物必须带指向它的 RUNPATH。**
   环的 `DT_NEEDED` 里有 `libswiftCore.so` 族与 `libc++_shared.so`；
   `swiftc.sh` 默认加 `-Xlinker -rpath -Xlinker <pkg>/ring/plane/lib`。
   本包的 `package_info()` 把 `lib/swift/ohos` 与 `toolchain/cxx` 放进 `libdirs`，
   但 **`ring/plane/lib` 不进 `libdirs`** —— 它是运行期契约，消费方必须自己把它加进 RUNPATH。

3. **绝不要把编译器的库路径导出成 `LD_LIBRARY_PATH`。**
   实测后果：`build/swift/lib/swift/ohos` 与 `instrument/lib` 里有**同名但不同构建**的
   `libdispatch.so` / `libBlocksRuntime.so`；一旦导出，新建的客户端会解析到错的副本并在装载期死：
   `Error relocating <ring>/plane/lib/libFoundation.so: _NSConcreteGlobalBlock: symbol not found`（`RUN_RC=127`）。
   编译器需要那条路径，**客户端不能有**。`env.sh` 把它存在 `T2_TOOLCHAIN_LD_LIBRARY_PATH`
   （不导出），由 `swiftc.sh` 只加在**编译器进程**上。

另有一条环境义务：**`TMPDIR` 必须可写**。本机 `/tmp` 是 0 字节只读挂载，
`env.sh` 默认把 `TMPDIR` 指向包内（`$T2_ROOT/.t2work`），除非调用方已经设过。

## 已剔除

已剔除 5 件 `lldb`（含 3 件 64 位，合计省 44.3 MB 压缩体积）。
剔除后四条链全绿：自带 demo 35 项、环夹具 24 例、判官、自建消费者。

## 已知限制

- 载荷为**宿主架构相关**（aarch64 OHOS 宿主）。
- 工具链为**预编译快照**：`env.sh` 把编译期烘死的绝对 RUNPATH 全部指回包内副本，
  故任意绝对路径解包即可工作；但**包路径本身若被移动后又被硬编码进消费方产物**，需重链。
- 二进制上传制品仓需 CI Release 机器凭据（`commands.json` 的 `binary: false` 即表示
  **尚未发布到制品仓**）。

## PENDING-P2（答复到位前不得落地）

见 `notes.md`。三处占位：**载荷托管 URL**、**版本号形态**、**`.swift` 测试源准入**。
