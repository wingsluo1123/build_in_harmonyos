# patches/ — swift-toolchain-ohos：**补丁面两条（包内前门 flag 表 ＋ 载荷绝对路径相对化）**

## 这两条是什么

| 件 | 目标 | 干什么 |
|---|---|---|
| `0001-swiftc-shared-flag-table.patch`（**7,968 B**，2 hunk，＋90/−11 行） | 载荷自带的包内前门 `swiftc.sh`（**2,594 B → 7,335 B**） | 把前门的 flag 表补成与载荷自带 `example/build.sh` **同一张五组表**：`-target`／`-use-ld`；Swift 运行时 `-I` 与 cxx `-L`；`_FoundationCShims` `-I`；icu `-I`／module-map；vfs-overlay；dispatch `-I`×5；额外 rpath×4 |
| `0002-payload-relocatable-paths.patch`（**3,765 B**，4 hunk，＋7/−5 行） | 载荷里**会被解析**的 4 个文本文件 | ① `build/swift/lib/swift/SwiftGlibc/module.modulemap` 的 3 条 header 改成**相对 modulemap 自身目录**（`../ohos/aarch64/SwiftGlibc.h` 等）；② `toolchain/bin/{ohos-clang,ohos-clang++,llvm-ranlib}` 的 exec 目标改成 **`$0` 相对**（`llvm-ranlib` 的 shebang 从构建机 bash 改成 `/bin/sh`） |

★ 判据是**可测读数**，不是"看着像"：
`T2_SHOW_FLAGS=1 sh <pkg>/swiftc.sh <example/build.sh 的逐字 argv>` ⇒ **`T2_FLAG_TABLE_ADDED=0`**
（同一读数在"调用方什么都不给"时是 **59**）。⇒ 两张表**构造性重合**。

★ 修法为什么是"共用一张表"而不是"补 4 个 flag"：r104 的 10 个消融变体显示
**必要组按程序而定**（`minus G4a` 逐字复现 r103 的 `missing required module '_FoundationCShims'`，
`minus G4d`／`minus G4e` 复现 `missing required module 'Dispatch'`，`minus G3` 在链接期发作），
而 `G1`／`G4b`／`G4c`／`G5` 对那个最小程序**不是必需** ⇒ 照最小集补 flag，**下一个程序**还会踩到表里剩下的组。

## 0002：为什么把 header 改成相对路径，而不是"加一个 `-fmodule-map-file=`"

真机 CI #97027 的 E3 原文指名 `SwiftGlibc/module.modulemap:29` 的 `header` 是**构建机绝对路径**：

```
SwiftGlibc/module.modulemap:29:10: error: header '…/swift-clean-llvm15-full-candidate-20260915-205500/build/swift/lib/swift/ohos/aarch64/SwiftGlibc.h' not found
```

* **相对化**：clang 解析 module map 里的相对 header 时，**基准是 module map 自身所在目录** ⇒
  `header "../ohos/aarch64/SwiftGlibc.h"` 就是包内那份头文件，包搬到任何绝对路径都仍可解析。
  同一载荷里的 `build/swift/lib/swift/ohos/aarch64/glibc.modulemap` **本来就是这个形态**
  （`header "SwiftGlibc.h"`），所以这是**跟随载荷自己的写法**，不是新发明。
* **`-Xcc -fmodule-map-file=`**：属"加参数"，会与 clang 自己的 module map 搜索/模块缓存产生
  两份同名的 `SwiftGlibc` 来源，且调用方一旦自己给了 `-fmodule-map-file=` 就会重复；脆。
* ★ 实测（本机，同一份载荷，四个变体）：相对形态编译通过；把相对名改成不存在的名字后
  clang 报同形错误；**把包内 `SwiftGlibc.h` 移走**后转红、放回后转绿 ⇒ 判据绑定在**包内**文件上，
  不是借了构建机那棵老树。

★ 另外三个 wrapper 是 class-B（执行时才解析）：`ohos-clang`／`ohos-clang++` 的 `exec` 目标与
`llvm-ranlib` 的 shebang/exec 都指向构建机，干净设备上直接 `inaccessible`。改成 `$0` 相对后，
在搬移过的前缀里 `ohos-clang --version` 与 `llvm-ranlib` 都能跑（同一轮实测）。

## 机制：为什么补丁打在 `swiftc.sh` 上，而不是源码上

本包是**预编译载荷包**：载荷（最小集 **189,124,959 B**）已经是在 OHOS 上构建并打好补丁的产物，
driver 这一层**没有源码可以打补丁**。本层**可改**、且被 `test_package` 的 11 项断言真跑到的可执行面，
就是载荷自带的**包内前门** `swiftc.sh`。因此：

* `conandata.yml` 的 `patches` 是**平铺列表**，**恰 2 条**（每条 `patch_file` / `patch_description` / `patch_type` / `strip: 1`）；
* `apply_conandata_patches(self)`（在 `build()` 内）按该段逐条应用 —— 真 create 日志里有
  `Apply patch (portability): …` 两行；
* `export_sources()` 的**方法体**是 `export_conandata_patches(self)` ⇒ **"导出的"与"打的"是同一份清单**，
  不会被 `patches/*` 这种通配符悄悄放大。

★ **G1 字面量**（`scripts/ohc/conan_verify.py:484-493`）要求配方出现 `export_sources` 与
`apply_conandata_patches` 两个字面量；并且 **Conan 2 里 `export_sources` 必须是方法**
（属性写法在 `export` 那一步当场抛 `ERROR: conanfile 'export_sources' must be a method`）。
这两条在 `archives/r/rust-toolchain/1.97.1/conanfile.py` 里**都不存在** ⇒ 照抄先例会 FAIL。

## 为什么仍然保留这个目录

1. **形态对齐**：全仓有 **3,487** 个版本目录带 `patches/`，本包与之同形；
2. **给后续留位**：若后续轮次把 **A3 补丁面**（`swift-foundation/Sources/_FoundationCShims`）并入本包，
   直接在本目录加文件、在 `conandata.yml` 的 `patches:` 列表里加一条即可。
   ★ 措辞澄清：**「`conanfile.py` 不用改」指的是它的方法体不用改**（清单唯一来源是 `conandata.yml`），
   **不是**"整个文件不用动" —— 新增补丁时 `conanfile.py` 头部与 docstring 里的补丁面描述**应当同步**。

## 本包**不带**的补丁面（它们属于 Foundation 轮，不属于 driver 轮）

| 区 | 件数 | 内容 | 去处 |
|---|---|---|---|
| A1 | 13 | `swift-corelibs-foundation/Sources/Foundation` | Foundation 轮 |
| A2 | 5 | `swift-corelibs-foundation/Sources/CoreFoundation` | Foundation 轮 |
| A3 | 1 文件 + 1 行 | `swift-foundation/Sources/_FoundationCShims`（`fts_ohos.c` 9,933 B ＋ `CMakeLists.txt` +15 B） | ★ 用户 2026-09-27 裁定**纳入 driver 轮补丁面**，但**按「＋1 文件 ＋1 行」计成本** |

★ **`$Q101/prep/patches/` 下的 20 个 `.patch` 是草案**（供 Foundation 轮与 driver 轮取材用），
**不是**本目录的内容。把两者混在一起，会让"driver 有没有补丁面"这个事实变得不可判。
★ 本目录**现在**的内容就是上表那**两条**：`0001-swiftc-shared-flag-table.patch`
与 `0002-payload-relocatable-paths.patch`（0002 是 locale-r112 新增，见上面「0002：为什么…」一节）。
