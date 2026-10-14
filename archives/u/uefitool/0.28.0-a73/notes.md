# uefitool 0.28.0-a73 — OpenHarmony PC 适配笔记

> 载体：`archives/u/uefitool/0.28.0-a73/`
> 目标平台：OpenHarmony PC（OHOS 6.0 / aarch64 / clang 15 / libc++ / **原生构建**）
> 结论速览：**零补丁**（上游源码一行不改，构建入口是适配侧新增的
> `cmake/CMakeLists.txt`）；包内只有 `bin/uefiextract`、`bin/uefifind` 两个可执行
> 文件 + `share/uefitool/guids.csv`；上游**没有**测试套件，全部功能证据来自
> 消费者用例（三层 28 条）。

> ⚠️ **状态说明（诚实标注）**：本档案**已全部取证完毕**（2026-10-04）。静态部分
> （上游事实、配方、固定装置、消费者用例设计、离线门禁）与**真机部分**（`conan create`、
> 适配侧 `ctest` 回显、消费者 28 条、ELF/`readelf` 取证、本地 CI 模拟 W3）的原始输出
> 都逐字回填在 **§6–§7**，任何一个数字都能指到具体命令与日志行；本文件不预填、不估算。
> 期间**被实测证伪或推翻的推断**（含一条已撤下的知识库草稿）在 §8 的「已否决的候选」
> 里留痕，便于复审对照。

---

## 1. 上游事实（对 tag `A73` 官方 tarball 的静态审计）

### 1.1 版本号的读法（第一件必须搞清的事）

上游 `LongSoft/UEFITool` 有两条并行分支，各自推版本号：

| 分支 | 版本号形态 | 例子 |
|---|---|---|
| `old_engine` | `0.xx.y` | `0.28.0` |
| `new_engine` | 快照 tag `A<n>`，`version.h` 里写 `"NE alpha <n>"` | **`A73`** |

本任务给的 `0.28.0-a73` 是**平台侧的命名**：`0.28.0` 取自 old_engine 的版本号，
`a73` 指 new_engine 的 tag `A73`。**源码必须取 tag `A73`**，取 `0.28.0` 那个 release
会拿到完全不同的代码树。产物 `--version` 打出来的是 `NE alpha 73 (<编译日期>)`。

### 1.2 源码包

| 项 | 值 |
|---|---|
| 官方 URL | `https://github.com/LongSoft/UEFITool/archive/refs/tags/A73.tar.gz` |
| tag | `A73` → commit `29796629` |
| 大小 | 2400878 bytes |
| sha256 | `81d9944d75e27d4afbc8559d9ba913552006fd21ce9cadf357a4a0f58e59507e` |
| 顶层目录 | `UEFITool-A73/`（单根目录，`strip_root=True` 可用） |
| 许可证 | BSD-2-Clause（仓库根 `LICENSE.md`，正文只有两个条件） |

三源（官方 / ghfast.top / gh-proxy.com）均按 `conandata.yml` 的形态书写，其中镜像项
一律写成「镜像前缀 + 官方完整 URL」。

### 1.3 构建定义：三个目标、零外部依赖

根 `CMakeLists.txt` **只有五行**：

```cmake
CMAKE_MINIMUM_REQUIRED(VERSION 3.22)
PROJECT(UEFITool_everything)
ADD_SUBDIRECTORY(UEFIExtract)
ADD_SUBDIRECTORY(UEFIFind)
ADD_SUBDIRECTORY(UEFITool)
```

| 目标 | 语言 | Qt | 用途 | 本包是否交付 |
|---|---|---|---|---|
| `UEFITool` | C++ | **Qt6 Widgets（REQUIRED）** | GUI（含 `QHexView` 子目录） | ❌ 不构建 |
| `UEFIExtract` | C++ | 无 | 批量解包 + 报告 + dump + guids | ✅ `bin/uefiextract` |
| `UEFIFind` | C++ | 无 | 按 GUID / hex pattern 检索 | ✅ `bin/uefifind` |

`UEFITool/CMakeLists.txt` 第 9 行是 `FIND_PACKAGE(Qt6 REQUIRED COMPONENTS Widgets)`
—— 这就是第 2 节要解决的**全部问题来源**。

**零外部依赖**：两个 CLI 子工程的 `PROJECT_SOURCES` 把第三方库全部以源码内联：

| 内嵌组件 | 位置 | 形态 |
|---|---|---|
| zlib | `common/zlib/*.c` | 18 个 C 文件 |
| Brotli | `common/brotli/common/*.c` + `dec/*.c` | 12 个 C 文件 |
| LZMA SDK | `common/LZMA/*.c` + `SDK/C/*.c` | 5 个 C 文件 |
| Tiano 解压 | `common/Tiano/EfiTianoDecompress.c` | 1 个 C 文件 |
| bstrlib | `common/bstrlib/*` | 1 C + 1 C++ |
| 消息摘要 | `common/digest/{sha1,sha256,sha512,sm3}.c` | 4 个 C 文件 |
| Kaitai 生成代码 | `common/generated/*.cpp` | **已入库**，不需 Kaitai 编译器 |

⇒ `UEFIExtract` = 38 个 C++ + 38 个 C；`UEFIFind` = 35 个 C++ + 38 个 C。
只需要「编译器 + CMake ≥ 3.22」，`requirements` 为空。

### 1.4 上游测试：**零**

| 检查 | 结果 |
|---|---|
| 全树 `meson.build` 里的 `test(` | **0 处** |
| 全树 `enable_testing()` / `add_test(` | **0 处** |
| `tests/` 或 `test/` 目录 | 不存在 |
| 唯一沾"测试"的文件 | `fuzzing/ffsparser_fuzzer.cpp`（libFuzzer 入口，**无种子语料**） |

⇒ `upstream_test_total = 0`。本档案**不伪造上游通过率**，PR 正文的「上游测试」列填 N/A。

### 1.5 `guids.csv` 的处境（本包的核心知识点）

- 文件 `common/guids.csv`：**12042 行**，格式 `<大写带连字符 GUID>,<名字>`，LF 行尾。
- 它**只**被 `UEFITool/uefitool.qrc` 引用一次：

  ```xml
  <file alias="guids.csv">../common/guids.csv</file>
  ```

  ⇒ 它被打进 **GUI 的 Qt 资源**，两个 CLI 子目录的 `INSTALL()` 里**没有**它。
- `UEFIExtract/uefiextract_main.cpp:51` 在 `main()` 的**第一行**：

  ```cpp
  int main(int argc, char *argv[])
  {
      initGuidDatabase("guids.csv");     // ← 相对路径，按 CWD 解析
      if (argc <= 1) { print_usage(); return 1; }
      ...
  ```

  注意它**早于** `argc` 检查 ⇒ 连 `uefiextract -v` 都会先去 CWD 找这个文件。
- 读失败时 `common/guiddatabase.cpp` **静默**：`readGuidDatabase()` 返回空串，
  `initGuidDatabase()` 把库 clear 后填充 0 条，**不报错、不中止、不改退出码**。
- 查表失败时 `common/ffs.cpp:233` 的 `guidToUString()` 回退到裸格式：

  ```cpp
  UString guidToUString(const EFI_GUID & guid, bool convertToString)
  {
      if (convertToString) {
          UString readableName = guidDatabaseLookup(guid);
          if (!readableName.isEmpty()) return readableName;
      }
      return usprintf("%08X-%04X-%04X-%02X%02X-%02X%02X%02X%02X%02X%02X", ...);
  }
  ```

  而 `common/ffs.h:25` 的声明里 `convertToString` **默认为 `true`**
  ⇒ `ffsparser.cpp:1520`（卷名）与 `ffsparser.cpp:2222`（文件名）都走查表路径。

**结论**：剥掉 GUI 之后，如果不想办法把 `guids.csv` 带上，工具**照样能跑、退出码
照样是 0、报告照样生成**，只是所有固件条目的可读名悄悄退化成裸 GUID 串。这是一种
最难发现的失败形态 —— 所以 §6 的 C 层用**双向**断言把它钉死。

---

## 2. 移植障碍与解法

### 2.1 ★ Qt6 GUI 子目录被无条件耦合进根工程

**症状**：在 OHOS PC（Qt 只有 qt5-qtbase / 5.15）上，对上游根工程跑 CMake configure：

```
CMake Error at UEFITool/CMakeLists.txt:9 (FIND_PACKAGE):
  By not providing "FindQt6.cmake" in CMAKE_MODULE_PATH this project has asked
  CMake to find a package configuration file provided by "Qt6", but CMake did
  not find one.
```

报错之后**整个工程停止**，连零 Qt 依赖的 `UEFIExtract` / `UEFIFind` 都到不了编译
—— 因为 `ADD_SUBDIRECTORY(UEFITool)` 与另外两个是**平级且无条件**的。

**解法**：新增一个薄构建入口 `cmake/CMakeLists.txt`（适配侧文件，**不在上游树里**）：

```cmake
cmake_minimum_required(VERSION 3.22)
project(uefitool CLI CXX C)

add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../UEFIExtract"
                 "${CMAKE_CURRENT_BINARY_DIR}/UEFIExtract")
add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../UEFIFind"
                 "${CMAKE_CURRENT_BINARY_DIR}/UEFIFind")

set_target_properties(UEFIExtract PROPERTIES OUTPUT_NAME "uefiextract")
set_target_properties(UEFIFind    PROPERTIES OUTPUT_NAME "uefifind")
```

配方侧用 `cmake.configure(build_script_folder="cmake")` 指过去，`export_sources()`
把这个文件随包带出。

**三条理由说明为什么这是对的做法**：

1. **不改上游一个字节** ⇒ `patches_applied` 为空，也就没有"补丁计数同步"
   （知识库坑 16.22）这一类问题；
2. **两个 CLI 是自足的**：`grep -rn "#include <Q" UEFIExtract/ UEFIFind/` 为空，
   它们的 `CMakeLists.txt` 里没有任何 `FIND_PACKAGE`；
3. **这就是"包面裁剪"**：GUI 目标在 OHOS 上既不可构建、也不是本任务需要的能力，
   把它排除掉是缩小而非削弱交付面（剥离 GUI 后解析器能力 100% 保留 —— 解析逻辑
   全在 `common/` 里，GUI 只是它的一个消费者）。

> ⚠️ 上游只在 `IF(UNIX)` 分支里做 `SET_TARGET_PROPERTIES(... OUTPUT_NAME uefiextract)`。
> 适配侧显式设置 `OUTPUT_NAME` 是为了让产物名在 OHOS 上也确定是小写的 ——
> 不依赖"OHOS 的 CMake 会把 `UNIX` 判为真"这一间接假设。

### 2.2 `guids.csv` 必须随包安装（否则沉默降级）

见 §1.5 的完整机制。处置：`package()` 里

```python
copy(self, "guids.csv",
     src=os.path.join(self.source_folder, "common"),
     dst=os.path.join(self.package_folder, "share", "uefitool"))
```

**为什么不干脆打进二进制？** 上游没有这么做（它选了 Qt 资源），我们不引入上游没有的
构建期代码生成步骤；把数据文件装到 `share/` 是 conan 场景下的常规做法，而且
`initGuidDatabase()` 本来就接受任意路径 —— 使用者在 CWD 放一份软链接/副本即可。
**为什么这是"必要且有效"而不是"多加了个文件"**：§6 的 C 层用同一张 fixture 在
「有名表 / 无名表」两个方向各断言一次，把它的作用变成可复现的证据。

### 2.3 OHOS 工具链三条常规处置

| # | 处置 | 理由 |
|---|---|---|
| 1 | `CMAKE_SYSTEM_NAME=Linux`（不新造 `OHOS`） | CMake 内置系统表没有 OHOS 条目；新造会让上游按 `cmake/os/${CMAKE_SYSTEM_NAME}.cmake` 找模块而落空。OHOS 侧由 conan toolchain 提供 sysroot |
| 2 | `CMAKE_SKIP_RPATH=ON` + `CMAKE_SKIP_INSTALL_RPATH=ON` | 本包**不产出任何第三方 `.so`**（brotli / LZMA / zlib / Tiano / bstrlib / digest 全部源码内联），产物 `NEEDED` 只剩平台自带的 `libc.so` 与 `libc++_shared.so`（真机 `readelf -d` 实测 **2 条**）⇒ 没有要靠 RPATH 才能定位的库；同时绕开「安装期重写 RPATH 写坏 ELF 的 `.note.ohos.ident` / `.codesign` 签名段」导致装出来二进制 `Operation not permitted`（rc=126，知识库 E077，qdl 2.7 同族实测）。真机实测结果：两个产物的 `RPATH`/`RUNPATH` 条目数均为 **0**，而 `.note.ohos.ident` 与 `.codesign` 段**都还在**，两件事同时成立 |
| 3 | `tools.build:jobs = 1` | `/storage/Users/**` 走 HMDFS，GNU make 的 jobserver fifo 建不出来（`mkfifo ... Operation not permitted`），表现为并行子任务集体 `Error 1` 且日志里一行编译器诊断都没有（R9 / E074） |

另加 `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`：OHOS 上避免 CMake 的编译器探测
阶段就去调用链接器。

### 2.4 构建步骤输出必须绑定到文件（同族先例）

`build()` 里的每一步都经 `_run_bound_step()` 执行，把输出绑到
`build_folder/logs/<label>.log`，失败时打印末 80 行再 `raise`，成功后按 500 行分块回显。

**为什么必须这样**：OHOS 真机同族实测（`archives/r/reliable/1.3.5`、
`archives/l/libfishcamp/1.2`）—— conan 把 recipe 进程的输出流继承给构建子进程时，
clang 会在第一个真正编译的翻译单元上**静默**非 0 退出（零诊断、make 只报 `Error 1`）。
**回显同样是必须的**：CI 的 L1b/L1c 要在 `conan create` 日志里 grep 到编译痕迹与测试
驱动痕迹，把输出全关进文件等于把证据抹掉。

### 2.5 ctest：把"零测试真空"换成三条真实用例

上游零测试 ⇒ 直接 `ctest` 会因"找不到测试"返回非 0，既让 `conan create` 失败，
日志里又只有一句 `No tests were found` —— 既不是证据，也不是有效的失败原因。

适配侧的 `cmake/CMakeLists.txt` 注册 3 条只依赖两个 CLI 自身退出码的冒烟用例：

| 用例名 | 命令 | 期望 |
|---|---|---|
| `uefitool-cli-version-extract` | `uefiextract -v` | 退出码 0 |
| `uefitool-cli-version-find` | `uefifind -v` | 退出码 0 |
| `uefitool-cli-usage-extract` | `uefiextract`（无参数） | 退出码 1（`WILL_FAIL` 反转） |

这三条**明确不是上游测试**，在 `MANIFEST.yml` 里单列为 `build_selftests`，
不计入上游测试数与消费者用例数。它们的作用是让 `ctest` 成为一条真实、确定、
与机器负载无关的证据链。

---

## 3. 配方决策表

| # | 决策 | 值 | 理由 |
|---|---|---|---|
| 1 | `package_type` | `application` | 没有库、没有公共头可链接（§1.3） |
| 2 | `requirements` | **空** | 零外部依赖（§1.3）；同仓先例 `archives/q/qdl/2.7`、`archives/2/2048.c/1.0.3` |
| 3 | `test_requires` / `tool_requires` | 无 | 只用环境自带的 bash + python3（conan 本体就跑在 Python 上） |
| 4 | `patches` | **空** | 上游零改动；构建入口是适配侧新增文件（§2.1） |
| 5 | `options` | 无 | 没有库语义，也就没有 `shared` / `fPIC` |
| 6 | `build_script_folder` | `"cmake"` | 指向适配侧入口（§2.1） |
| 7 | `CMAKE_SYSTEM_NAME` | `Linux`（OHOS 时） | 见 §2.3 第 1 条 |
| 8 | `CMAKE_SKIP_RPATH` / `_INSTALL_RPATH` | `ON` | 见 §2.3 第 2 条 |
| 9 | `CMAKE_TRY_COMPILE_TARGET_TYPE` | `STATIC_LIBRARY` | 避免探测期调链接器 |
| 10 | `tools.build:jobs` | `1` | 见 §2.3 第 3 条 |
| 11 | `package_info` | 只 `bindirs = ["bin"]` | 无可链接物；`libdirs` / `includedirs` 显式清空 |
| 12 | `commands.json` | 放**软件级** `archives/u/uefitool/` | L0k：`package_type = application` 需在版本目录或其父目录提供 |

---

## 4. 消费者用例设计（工具包语义）

这个包**没有库、没有公共头**，所以"消费者"只能是"拿到 `uefiextract` / `uefifind`
两个可执行文件的人"。`test_package/test.sh` 分三层，共 **28 条**检查。

### 4.1 A 层：CLI 契约（17 条）—— 期望值全部来自上游源码字面返回

| 检查 | 期望 | 源码依据 |
|---|---|---|
| `uefiextract -v` | rc=0，输出含 `NE alpha 73` | `uefiextract_main.cpp` 的 `-v` 分支 |
| `uefifind -v` | rc=0，输出含 `NE alpha 73` | `uefifind_main.cpp` |
| `uefiextract --help` | rc=0，用法含 `imagefile all` / `unpack` / `dump` / `report` / `guids` / `-m MODE_1` | `print_usage()` 原文 |
| `uefifind --help` | rc=0，用法含 `header \| body \| all` / `list \| count` / `patternsfile` | `print_usage()` 原文 |
| `uefiextract` 无参数 | **rc=1** | `if (argc <= 1) { print_usage(); return 1; }` |
| `uefifind` 无参数 | **rc=0** | `if (argc == 1) { print_usage(); return U_SUCCESS; }` |
| 二者查不存在的文件 | rc=5 | `U_FILE_OPEN = 5`（`common/basetypes.h`） |

★ **两个工具在"无参数"上的返回值刻意不对称（1 vs 0）** —— 这是最容易在写测试时
想当然的地方。本用例把两边各自钉住，等于把"我们真的读过 `main()`"变成可验证的。

版本断言只钉 `NE alpha 73` 这个 token：`PROGRAM_VERSION` 里带 `__DATE__`
（`"NE alpha 73 (Mon DD YYYY)"`），日期随构建时刻变化，钉全串必然是 flaky。

### 4.2 B 层：真实解析（8 条）—— 上游零语料，自己造

`make_fixture.py` 用**纯标准库**生成一张 4096 字节的最小合法 FFS2 固件卷：

| 偏移 | 内容 |
|---|---|
| `0x00` | `ZeroVector[16]`（全零） |
| `0x10` | `FileSystemGuid` = `78 E5 8C 8C 3D 8A 1C 4F 99 35 89 61 85 C3 2D D3`（= `EfiFirmwareFileSystem2Guid` 的 EFI_GUID 字节序） |
| `0x20` | `FvLength` = 4096 |
| `0x28` | `Signature` = `5F 46 56 48`（`_FVH`） |
| `0x2C` | `Attributes` = `0x00000800`（`EFI_FVB2_ERASE_POLARITY`） |
| `0x30` | `HeaderLength` = `0x48` |
| `0x32` | `Checksum`（`calculateChecksum16` 复刻上游算法） |
| `0x37` | `Revision` = 2（FFSv2） |
| `0x38` | `BlockMap`：一项 + 终止项（`NumBlocks=0`） |
| `0x48` | 一个 `EFI_FFS_FILE_HEADER`（24 字节）+ `EFI_COMMON_SECTION_HEADER`（4 字节）+ 段体 |
| 段体 | 4 字节魔数 `EF BE AD DE` + 32 字节 ASCII 标记 `UEFITOOL-OHOS-CONSUMER-PROBE-001` |

探测文件的 GUID 用自定义值 `A1B2C3D4-E5F6-4A5B-8C9D-0E1F2A3B4C5D`（**不在**
`guids.csv` 里，所以它的呈现形态与名表无关，可作稳定锚点）。

八条检查：fixture 生成（且 size == 4096）→ `report` rc=0 → 报告非空 →
报告含探测 GUID → `uefifind body count <魔数>` 命中 → `body list` 报出该 GUID →
查一个不存在的魔数得 `U_ITEM_NOT_FOUND(8)` → `dump` 落出非空目录树。

**为什么值得自己造这个 fixture**：它让"两个工具真的能解析固件"这件事有了一条
**不依赖任何外部固件样本**的证据链（既没有分发风险，也完全可复现）。

### 4.3 C 层：`guids.csv` 生效性（3 条）★ 最有分量

§1.5 说明了这个失败形态有多隐蔽（rc=0、报告正常、只有可读名消失）。所以做**双向**：

| # | 场景 | 断言 |
|---|---|---|
| 17 | CWD **无** `guids.csv` | 报告里的卷名必须是裸格式 `8C8CE578-8A3D-4F1C-9935-896185C32DD3` |
| 18 | 把随包的 `guids.csv` 拷进 CWD 后重跑 | 同一个卷必须变成 `EfiFirmwareFileSystem2Guid` |
| 19 | `uefiextract <img> guids` | 必须产出非空的 `<img>.guids.csv` |

锚点选**卷头**的 `FileSystemGuid` 而不是探测文件的自定义 GUID，是因为它正好在
`guids.csv` 的第 `8C8CE578-8A3D-4F1C-9935-896185C32DD3` 行，而卷名来自
`ffsparser.cpp:1520` 的 `guidToUString(volumeHeader->FileSystemGuid)`（默认查表）。

**第 18 条同时是"`package()` 装 `guids.csv` 到 `share/uefitool/` 是有效且必要的"
的证明** —— 路径由 `test_package/conanfile.py` 从
`self.dependencies[...].package_folder` 算出后作为 `$1` 传给 `test.sh`。

GUID 断言一律经 `norm()` 归一化（`tr -d '[:space:]-' | tr 'a-f' 'A-F'`），
不把断言绑死在 `guidToUString` 的大小写与连字符细节上。

---

## 5. 踩坑清单（速查）

| # | 坑 | 判据 / 症状 | 处置 |
|---|---|---|---|
| 1 | ★ 上游根工程无条件拉 Qt6 GUI 子目录 | 无 Qt6 平台 configure 即 `FIND_PACKAGE(Qt6 REQUIRED ...)` 失败，整树停摆 | 新增薄 `cmake/CMakeLists.txt` 只拉两个 CLI（§2.1） |
| 2 | ★ `guids.csv` 不随 CLI 安装，且按 CWD 解析 | 工具 rc=0、报告正常，但所有可读名退化成裸 GUID 串（**无任何报错**） | `package()` 装到 `share/uefitool/`；C 层双向断言（§2.2 / §4.3） |
| 3 | `initGuidDatabase()` 在 `main()` 首行，早于 `argc` 检查 | 连 `-v` 都会去 CWD 找 `guids.csv` | 知道这件事即可；CWD 里有脏 `guids.csv` 会污染所有子命令 |
| 4 | 上游零测试 | `ctest` 因"找不到测试"返回非 0，日志只有 `No tests were found` | 注册 3 条真实冒烟用例（§2.5） |
| 5 | 两个 CLI 的"无参数"退出码不对称 | `uefiextract` 返回 1、`uefifind` 返回 0 | 测试不能套同一模板，逐二进制实测（§4.1） |
| 6 | HMDFS 上 GNU make jobserver fifo 建不出来 | 并行子任务集体 `Error 1`，日志零编译器诊断 | `tools.build:jobs = 1`（R9 / E074） |
| 7 | 安装期重写 RPATH 写坏 ELF 签名 | 装出来的二进制 `Operation not permitted`（rc=126） | `CMAKE_SKIP_RPATH` / `CMAKE_SKIP_INSTALL_RPATH`（E077） |
| 8 | conan 继承输出流时 clang 静默退出 | 非 0 退出、零诊断、make 只报 `Error 1` | 构建步骤输出绑到文件再回显（§2.4） |
| 9 | 手写编译命令把 `-std=c++11` 套到整份 `PROJECT_SOURCES` | `invalid argument '-std=c++11' not allowed with 'C'`（38 个第三方 C 文件被判成 C++） | **仅本地校准时踩到**；CMake 路径按扩展名自动分派语言，无需处理 |
| 10 | 本地 `zig c++` 报 `error: CacheCheckFailed` | 同一条命令在**全新**缓存目录下必然成功 | 换 `ZIG_LOCAL_CACHE_DIR` / `ZIG_GLOBAL_CACHE_DIR` 到新名字（仅本地工具链问题） |
| 11 | ★ `uefiextract <img> guids` 在 GUID 库为空时打印用法并 `rc=1` | 参数本身完全合法，却被判成误用；`<img>.guids.csv` 根本不生成（收集函数取错字段 + 该分支缺终结 `return`） | 消费者用例分 C3 双向钉住（含 Volume Top File ⇒ `rc=0` 且文件非空并含 VTF GUID）；根因与最小修复见 `knowledge/drafts/DRAFT-uefitool-0.28.0-a73-guids-mode-text-vs-name-emptydb-fallthrough` |

---

## 6. 本地验证记录

| # | 验证项 | 方式 | 结果 |
|---|---|---|---|
| 1 | tarball 三源一致 | 官方 / ghfast.top / gh-proxy.com | ✅ sha256 均为 `81d9944d…507e` |
| 2 | fixture 字节级正确 | `make_fixture.py` 生成后逐字节核对（4096 B） | ✅ FV 头：`0x10` = `78e58c8c3d8a1c4f9935896185c32dd3`（FS GUID）、`0x20` = `00100000_00000000`（`FvLength`=4096）、`0x28` = `5f465648`（`_FVH`）、`0x30` = `4800`（`HeaderLength`=72）、`0x32` = `d1cd`（卷校验和）、`0x37` = `02`（**FFSv2**）。文件 1（探测，`0x48`，`Size`=`40`）头校验和 `0x58` = **`F0AA`**（`Header`=F0 正是解析器期望值、`File`=0xAA），体 `0x60` = 节头 `28000019` + 魔数 `EFBEADDE`。文件 2（VTF，`0x88`，GUID `2e06a01b79c782458566336ae8f78f09`、`Size`=`40`）头校验和 `0x98` = `C9AA`，体 `0xA0` = 节头 `28000019` + `CAFEBABE` + ASCII `UEFITOOL-OHOS-VTF-ANCHOR-0001`。尾部自 `0xC8` 起全 `0xFF`（3896 字节）；两个魔数各命中 1 次 |
| 3 | 两个 CLI 能真实解析该 fixture | 真机 `conan create` 的消费者用例（`report` / `dump` / `find` / `guids` 四种模式真实解析同一 fixture） | ✅ 28/28 全通过（`ALL CHECKS PASSED (28/28)`），原文见 §7.3 |
| 4 | 静态门禁（离线模拟 CI） | `verify_archive.py` + `--upstream-src …/UEFITool-A73` + `--header UEFITool/uefitool.h` + `--branch feat/uefitool-0.28.0-a73` | ✅ `ok=72 warn=2 fail=0`，`✅ 静态合规校验通过`（两个 warn 为预期项：test_package 无 C/C++ 源、档案不在仓库内故跳过 G0e） |

---

## 7. 真机执行记录（2026-10-04 完成）

下列 1–6 项**均已在真机执行完毕**，原始输出逐字回填在 7.1–7.10；
§7.1–§7.10 全部为实测原文，无一项待办。
（下方 7.x 各节里行首的两个空格来自下发脚本的缩进，不是手写排版。）

★ **两次真机全量复跑的关系**：§7.1–§7.7 记录的是 **Stage 2R**（配方 `#a75862c9…`）；
此后因 `readelf` 取证推翻了配方注释里"纯静态链接"的错误措辞、需要改
`conanfile.py`（**改 recipe 会换 hash**），又执行了 **Stage 5a** 完整复跑
（配方 `#bb0813fe…`），原文见 **§7.8**。提交到仓库的配方是后者。
两次的 `package_id` 与 package revision 完全相同、**两个二进制的 sha256 逐字节一致**
⇒ 注释修订确实只发生在文字层，产物未变。

执行顺序记录：

1. **通道（已恢复）**：`C:\ohpcd-serve\_server.py` 由 **PC 侧**监听 `0.0.0.0:8000`
   当服务端，真机是**被动轮询端**（`~/.ohget` + `alias g`）。★ 旧文档里的
   `10.29.57.12:8000` 不是真机地址，而是 PC 自己早前的一张虚拟网卡地址；校园网
   DHCP 变动后 PC 现为 `10.129.64.34:8000`（真机 `10.129.199.88`）。`ohget.sh`
   已改为**多候选自动探活**（`/ping` 回 `pong` 才算活），真机侧只需
   `MIRROR=http://10.129.64.34:8000 g up` + `g watch 5`。真机**无 SSH**
   （22/2222/8000/8080/5555 全关），一切下发只能走这条轮询通道。
2. **本地静态门禁** ✅ —— `verify_archive.py` 指向 `--upstream-src …/UEFITool-A73`、
   `--header UEFITool/uefitool.h`、`--branch feat/uefitool-0.28.0-a73`，结果
   `ok=72 warn=2 fail=0`（两个 warn 均为预期项）。
3. **真机 `conan create`** ✅ ——
   `conan create archives/u/uefitool/0.28.0-a73 -pr:h=…/ohos-aarch64 -pr:b=<同> --build="uefitool/*"`
   ⇒ `rc=0`；日志 353 行，编译痕迹 149 行，`ctest` 3/3，`error`/`warning` 命中均为 0。
   注释修订后 **Stage 5a 复跑**（日志 356 行）同样 `rc=0`、`ctest 3/3`、
   `error`/`warning` 均为 0，二进制 sha256 不变，原文见 §7.8。
4. **消费者用例** ✅ —— `bash test.sh <pkg>/share/uefitool/guids.csv` ⇒
   `28 checks run, 0 failed` / `ALL CHECKS PASSED (28/28)`。
5. **本地 CI 模拟（W3）** ✅ —— `CI_PACKAGES="archives/u/uefitool/0.28.0-a73" … zsh
   ci/conan/build_and_test.sh` ⇒ `CI_RC=0`、`Pass rate: 100.0% (1/1)`，见 §7.6。
   ⚠️ 该脚本是 `#!/usr/bin/zsh`，**必须用 `zsh` 跑**（用 bash 会在 `${+CI_PACKAGES}` 处
   bad substitution）。
6. **回填** ✅ —— 全部原始输出已逐字填进 §7.1–§7.10 与
   `reports/pr-body.md` 的「验证结果」表。

### 7.1 真机 `conan create` 原文 ✅

真机环境：`HarmonyOS aarch64 / OpenHarmony 6.0 / clang 15 / libc++ / 原生构建`；
conan **2.29.1**、cmake **4.1.2**、python3 `/storage/Users/currentUser/usr/local/bin/python3`；
仓库 `~/runner002/build_in_harmonyos`（执行时 HEAD 为 `feat/qdl-2.7` @ `f2713e9b81`，本包尚未切分支）。
命令：`conan create archives/u/uefitool/0.28.0-a73 -pr:h=…/ohos-aarch64 -pr:b=<同> --build="uefitool/*"`，
日志 `$HOME/uefitool-create-r2.log`（353 行）。

```
========== C. conan create（本步最耗时，日志同时落 /storage/Users/currentUser/uefitool-create-r2.log） ==========
conan create rc = 0
log = /storage/Users/currentUser/uefitool-create-r2.log  (353 行)
```

日志中段（ctest + 打包 + 测试包启动）：

```
  uefitool/0.28.0-a73: RUN: cmake --build "/storage/Users/currentUser/.conan2/p/b/uefit1998ec6d181ba/b/build/Release" --target test -- -j1
  
  uefitool/0.28.0-a73: --- ctest.log (12 lines) ---
  uefitool/0.28.0-a73: Running tests...
  Test project /storage/Users/currentUser/.conan2/p/b/uefit1998ec6d181ba/b/build/Release
      Start 1: uefitool-cli-version-extract
  1/3 Test #1: uefitool-cli-version-extract .....   Passed    0.05 sec
      Start 2: uefitool-cli-version-find
  2/3 Test #2: uefitool-cli-version-find ........   Passed    0.03 sec
      Start 3: uefitool-cli-usage-extract
  3/3 Test #3: uefitool-cli-usage-extract .......   Passed    0.03 sec
  
  100% tests passed, 0 tests failed out of 3
  
  Total Test time (real) =   0.12 sec
  uefitool/0.28.0-a73: Package '6b129b068851896169fae42d399fa922d239ce8a' built
  uefitool/0.28.0-a73: Build folder /storage/Users/currentUser/.conan2/p/b/uefit1998ec6d181ba/b/build/Release
  uefitool/0.28.0-a73: Generating the package
  uefitool/0.28.0-a73: Packaging in folder /storage/Users/currentUser/.conan2/p/b/uefit1998ec6d181ba/p
  uefitool/0.28.0-a73: Calling package()
  uefitool/0.28.0-a73: Running CMake.install()
  uefitool/0.28.0-a73: RUN: cmake --install "/storage/Users/currentUser/.conan2/p/b/uefit1998ec6d181ba/b/build/Release" --prefix "/storage/Users/currentUser/.conan2/p/b/uefit1998ec6d181ba/p"
  -- Install configuration: "Release"
  -- Installing: /storage/Users/currentUser/.conan2/p/b/uefit1998ec6d181ba/p/bin/uefiextract
  -- Installing: /storage/Users/currentUser/.conan2/p/b/uefit1998ec6d181ba/p/bin/uefifind
  
  uefitool/0.28.0-a73: package(): Packaged 2 files: uefiextract, uefifind
  uefitool/0.28.0-a73: package(): Packaged 1 '.md' file: LICENSE.md
  uefitool/0.28.0-a73: package(): Packaged 1 '.csv' file: guids.csv
  uefitool/0.28.0-a73: Created package revision eb6bed38adf631a33bb31cff0d31a1e4
  uefitool/0.28.0-a73: Package '6b129b068851896169fae42d399fa922d239ce8a' created
  uefitool/0.28.0-a73: Full package reference: uefitool/0.28.0-a73#a75862c9e282c0883d82f6b28dde08ad:6b129b068851896169fae42d399fa922d239ce8a#eb6bed38adf631a33bb31cff0d31a1e4
  uefitool/0.28.0-a73: Package folder /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p
```

脚本统计：`Building CXX/C object` **149** 行；`error:` / `fatal error:` / `Error N while executing` / `ERROR` 命中 **0**；`warning:` 命中 **0**。

### 7.2 适配侧 ctest 回显 ✅

`ctest` 由适配侧 `cmake/CMakeLists.txt` 注册的 3 条用例驱动（上游本身零测试）：

```
  uefitool/0.28.0-a73: Running tests...
  Test project /storage/Users/currentUser/.conan2/p/b/uefit1998ec6d181ba/b/build/Release
      Start 1: uefitool-cli-version-extract
  1/3 Test #1: uefitool-cli-version-extract .....   Passed    0.05 sec
      Start 2: uefitool-cli-version-find
  2/3 Test #2: uefitool-cli-version-find ........   Passed    0.03 sec
      Start 3: uefitool-cli-usage-extract
  3/3 Test #3: uefitool-cli-usage-extract .......   Passed    0.03 sec
  
  100% tests passed, 0 tests failed out of 3
  
  Total Test time (real) =   0.12 sec
```

### 7.3 消费者用例原文 ✅

`bash test.sh <pkg>/share/uefitool/guids.csv` —— 共 28 条，逐条回显：

```
  --- uefitool 0.28.0-a73 consumer verification ---
  ok 1 - uefiextract -v -> [NE alpha 73 (Oct  4 2026)]
  ok 2 - uefifind -v -> [NE alpha 73 (Oct  4 2026)]
  ok 3 - uefiextract --help rc=0
  ok 4 - uefiextract --help lists [imagefile all]
  ok 5 - uefiextract --help lists [unpack]
  ok 6 - uefiextract --help lists [dump]
  ok 7 - uefiextract --help lists [report]
  ok 8 - uefiextract --help lists [guids]
  ok 9 - uefiextract --help lists [-m MODE_1]
  ok 10 - uefifind --help rc=0
  ok 11 - uefifind --help lists [header | body | all]
  ok 12 - uefifind --help lists [list | count]
  ok 13 - uefifind --help lists [patternsfile]
  ok 14 - uefiextract (no args) rc=1
  ok 15 - uefifind (no args) rc=0 (upstream asymmetry preserved)
  ok 16 - uefiextract <missing file> rc=5 (U_FILE_OPEN)
  ok 17 - uefifind <missing file> rc=5 (U_FILE_OPEN)
  ok 18 - fixture generated (4096 bytes, FFSv2 volume + FREEFORM probe file + Volume Top File)
  ok 19 - uefiextract <fixture> report rc=0
  ok 20 - report written (850 bytes)
  ok 21 - report names the probe file GUID (A1B2C3D4E5F64A5B8C9D0E1F2A3B4C5D)
  ok 22 - uefifind <fixture> body count efbeadde rc=0 -> [1]
  ok 23 - uefifind <fixture> body list efbeadde rc=0 -> names probe file GUID
  ok 24 - uefifind <fixture> body count 5a5a5a5a rc=8 (U_ITEM_NOT_FOUND)
  ok 25 - uefiextract <fixture> dump rc=0, 12 file(s) under probe.fv.dump/
  ok 26 - no guids.csv in CWD -> volume stays raw (8C8CE5788A3D4F1C9935896185C32DD3)
  ok 27 - guids.csv in CWD -> volume named 'EfiFirmwareFileSystem2Guid'
  ok 28 - uefiextract <fixture> guids rc=0 -> probe.fv.guids.csv (53 bytes, names the VTF 1BA0062EC77945828566336AE8F78F09)
  --- uefitool consumer: 28 checks run, 0 failed ---
  ALL CHECKS PASSED (28/28)
```

### 7.4 包产物清单 ✅

```
--- 三个安装项 ---
  /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefiextract
  /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefifind
  /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/share/uefitool/guids.csv
  /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/b/common/guids.csv
  /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/b/build/Release/UEFIExtract/uefiextract
  /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/b/build/Release/UEFIFind/uefifind
  /storage/Users/currentUser/.conan2/p/uefit25b26a75770ab/s/common/guids.csv
--- 包引用 ---
  286:uefitool/0.28.0-a73: package(): Packaged 2 files: uefiextract, uefifind
  287:uefitool/0.28.0-a73: package(): Packaged 1 '.md' file: LICENSE.md
  288:uefitool/0.28.0-a73: package(): Packaged 1 '.csv' file: guids.csv
  291:uefitool/0.28.0-a73: Full package reference: uefitool/0.28.0-a73#a75862c9e282c0883d82f6b28dde08ad:6b129b068851896169fae42d399fa922d239ce8a#eb6bed38adf631a33bb31cff0d31a1e4
--- 二进制自检 ---
  bin = /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefiextract
  -rwxrwx--- 1 20001006 file_manager 1235456 2026-10-04 22:45 /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefiextract
  sha256 = 52dd9dce0dc6dd65f7581e11e8a82527af8ba3f5ff59cd1f7b54696932a39d91
  NE alpha 73 (Oct  4 2026)
  rc(-v) = 0
```

### 7.5 独立复现 `guids` 子模式（消费者用例之外的第二信源）✅

这是第 28 条用例的**对照实验**：F1 有 guids.csv + 有 VTF ⇒ `rc=0`；F2 把 VTF 的
GUID 抹掉使库变空 ⇒ `rc=1` 且不产出文件（同时复现了修复前 Stage 2 的失败形态）；
F3 用 `report`（走 `name` 字段）作对照。

```
========== F. 独立复现 guids 子模式（消费者用例之外的第二信源） ==========
  guids.csv = /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/share/uefitool/guids.csv (662655 bytes)
  fixture = probe.fv (4096 bytes)
--- F1. 有 guids.csv + 有 Volume Top File（期望 rc=0 且生成文件）---
  rc=0  out_bytes=53
  内容：
    1BA0062E-C779-4582-8566-336AE8F78F09,Volume Top File
--- F2. 对照组：把 VTF 的 GUID 抹掉（库变空，期望 rc=1 且不生成文件）---
  rc=1  out_bytes=none
  输出头 3 行（应为用法文本）：
    parseFileHeader: invalid header checksum C9h, should be BEh
    parse: not a single Volume Top File is found, the image may be corrupted
    UEFIExtract NE alpha 73 (Oct  4 2026)
  (F2 会伴随一条 invalid header checksum 警告 —— 抹 GUID 后文件头校验和必然不再匹配，属预期)
--- F3. 同一 fixture 的 report 对照（走 name 字段，期望 rc=0 且含 VTF GUID）---
  rc=0  report_bytes=825
     File                | Freeform              | 00000088 | 00000040 | F905D8C5 | -- SecCore_VolumeTopFile | Volume Top File
```

### 7.6 本地 CI 模拟（W3）✅

命令：`JUNK_PR_DIFF=… CI_PACKAGES=archives/u/uefitool/0.28.0-a73 CI_BRANCH=feat/uefitool-0.28.0-a73 zsh ci/conan/build_and_test.sh`
（脚本是 `#!/usr/bin/zsh`，**必须用 zsh 跑**；用 bash 会在 `${+CI_PACKAGES}` 处 bad substitution）
日志 `$HOME/tmp/ci-sim-uefitool.log`（492 行），`CI_RC=0`。

闸口结果：

```
========== 4. 门禁结果 ==========
G0_RESULT=pass
KC_RESULT=pass
JC_RESULT=pass
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: uefiextract --version OK, uefifind --version OK
L4_RESULT=pass: no patches
L5_RESULT=pass: bin/ has content
[step] CI_PACKAGES received: archives/u/uefitool/0.28.0-a73
  Pass rate: 100.0% (1/1)
10:        [ok] G0e: Root directory whitelist passed
--- 期望出现的两条成功判据 ---
  461:--- uefitool consumer: 28 checks run, 0 failed ---
  462:ALL CHECKS PASSED (28/28)

```

构建汇总：

```
  L0_RESULT=pass: all checks passed
  L1_RESULT=pass: upstream tests + test_package executed
  L2_RESULT=pass: uefiextract --version OK, uefifind --version OK
  L4_RESULT=pass: no patches
  L5_RESULT=pass: bin/ has content
  [step] Generating ci-metadata.json...
  [ok] ci-metadata.json written
  
  ━━━ Build Summary ━━━
    Total:   1
    Success: 1
    Failed:  0
    Pass rate: 100.0% (1/1)
  [step] All packages built and tested successfully ✅
  [step] Pre-download: conandata.yml 已还原为官方 URL

```

⚠️ **本机非阻塞现象（根因已实测定位，2026-10-04 补）**：日志里有 **12 行**
`[fail] [Errno 2] No such file or directory: 'curl'`。
**早先本文件与 `pr-body.md` 把原因写成"本机未安装 `curl`"——这句话是错的**，
按实测更正如下：

```
========== curl 谜题：文件本身 + Python 视角 ==========
--- ls -l /usr/bin/curl ---
  -rwxr-xr-x 1 root root 4173016 2024-06-06 08:00 /usr/bin/curl
--- 前 3 行（ELF，不是脚本）---
  ELF ... /lib/ld-musl-aarch64.so.1 ... OHOS ...
--- sh 视角 ---
  [ -x /usr/bin/curl ] = yes
  command -v curl = /usr/bin/curl
--- python3 视角（逐个能力点） ---
  PermissionError: [Errno 13] Permission denied: '/usr/bin/curl'
    os.path.exists        = False
    os.path.isfile        = False
    os.access X_OK        = False
    os.access R_OK        = False
--- python3 实际调用绝对路径 curl ---
  PermissionError: [Errno 13] Permission denied: '/usr/bin/curl'
--- python3 用 'curl' 裸名调用（复现 CI 的失败） ---
    异常 = FileNotFoundError [Errno 2] No such file or directory: 'curl'
```

★ **真相**：`/usr/bin/curl` **存在且可执行**（`curl 8.8.0-DEV (aarch64-linux-ohos)`，
`libcurl/8.8.0-DEV OpenSSL/3.0.12 zlib/1.3.1`，`755`，ELF）。但 **`python3` 进程读不到它**：
`os.stat()` 直接抛 `PermissionError: [Errno 13]`，于是 `os.path.exists` / `isfile` /
`os.access` 全部为 `False`，`shutil.which('curl')` 返回 `None`；
`subprocess.run(['/usr/bin/curl', …])` 抛 `PermissionError`，用裸名则抛
`FileNotFoundError`（与 CI 日志逐字一致）。

★★ **根因是进程域，不是权限位**：真机的 `python3` 位于
`/storage/Users/currentUser/usr/local/bin/python3` —— **用户可写目录**；
而 OHOS 上**从用户可写目录启动的可执行文件会切入受限进程域**，该域**读不到 `/usr/bin`**。
`sh` 是宿主交互 shell，不在该域，所以 shell 侧一切正常 ——
**本通道自己的取件工具 `~/.ohget` 就是 shell + curl 实现的，一直工作正常，本身就是反证**。
（该机制与本队另一库 qdl 2.7 排查时用 `/proc/<pid>/attr/current` 定位到的结论一致；
本包是它的**第二个复现实例**，且复现路径不同 —— 那里是 shell 命令找不到，
这里是**从 Python 子进程调用**系统命令。）

⇒ CI 脚本的「Pre-download」预热步骤按 `conandata.yml` 的 3 条 URL（第 1 条 `github.com`
被展开成 2 个镜像、后两条各 1 个）逐条 ×3 次重试 ⇒ **恰好 12 次失败**；随后脚本打印
`[step] Pre-download: conandata.yml 已还原为官方 URL`，源码改由 **conan 自身**的下载器
（不走 shell 的 `curl`）取得，`conan create` 与全部闸口仍然 pass。

★★ **该现象与包本身完全无关**（是平台环境特性），但它正好说明两件事：
① `conandata.yml` 必须带"官方源 + 镜像兜底"列表 —— 预热失败时还有 conan 自身的下载兜底；
② **在 OHOS 上写 Python 验证/CI 脚本时，不要用 `subprocess` 直接调 `/usr/bin` 下的系统命令**，
需要时要么走 `sh -c`，要么用绝对路径 + 先做能力探测（`os.stat` 包 try/except）。

### 7.7 产物 ELF 取证（`readelf`）✅

真机 `uname -a`：`HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP … aarch64 Toybox`。

```
uname -a: HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP Wed Apr 29 10:16:03 UTC 2026 aarch64 Toybox
readelf tool = readelf

========== 1. 两个产物 ==========
uefiextract = /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefiextract
uefifind   = /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefifind

========== 2. file / sha256 / 版本 ==========
-- /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefiextract
   -rwxrwx--- 1 20001006 file_manager 1235456 2026-10-04 22:50 /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefiextract
   sha256 = 52dd9dce0dc6dd65f7581e11e8a82527af8ba3f5ff59cd1f7b54696932a39d91
   /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefiextract: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
   size   = 1235456 bytes
-- /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefifind
   -rwxrwx--- 1 20001006 file_manager 1063424 2026-10-04 22:50 /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefifind
   sha256 = ca609260b134074f50ae2ed24147121eadba8c6cd48d3b0b74a8a65141b64653
   /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefifind: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
   size   = 1063424 bytes
-- -v --
   uefiextract: NE alpha 73 (Oct  4 2026)
   uefifind  : NE alpha 73 (Oct  4 2026)

========== 3. ELF 头（期望 64-bit LSB / ARM aarch64 / DYN+INTERP） ==========
-- /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefiextract
     Class:                             ELF64
     Data:                              2's complement, little endian
     OS/ABI:                            UNIX - System V
     Type:                              DYN (Position-Independent Executable file)
     Machine:                           AArch64
-- /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefifind
     Class:                             ELF64
     Data:                              2's complement, little endian
     OS/ABI:                            UNIX - System V
     Type:                              DYN (Position-Independent Executable file)
     Machine:                           AArch64

========== 4. 动态段：NEEDED / RPATH / RUNPATH ==========
-- /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefiextract
    0x0000000000000001 (NEEDED)             Shared library: [libc++_shared.so]
    0x0000000000000001 (NEEDED)             Shared library: [libc.so]
   NEEDED 条数 = 2
   RPATH/RUNPATH 条数 = 0
-- /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefifind
    0x0000000000000001 (NEEDED)             Shared library: [libc++_shared.so]
    0x0000000000000001 (NEEDED)             Shared library: [libc.so]
   NEEDED 条数 = 2
   RPATH/RUNPATH 条数 = 0

========== 5. 段属性：INTERP / GNU_RELRO / GNU_STACK(NX) ==========
-- /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefiextract
     INTERP         0x0002a8 0x00000000000002a8 0x00000000000002a8 0x00001a 0x00001a R   0x1
     GNU_RELRO      0x0f3390 0x00000000000f5390 0x00000000000f5390 0x002c58 0x002c70 R   0x1
     GNU_STACK      0x000000 0x0000000000000000 0x0000000000000000 0x000000 0x000000 RW  0
-- /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefifind
     INTERP         0x0002a8 0x00000000000002a8 0x00000000000002a8 0x00001a 0x00001a R   0x1
     GNU_RELRO      0x0cc4d0 0x00000000000ce4d0 0x00000000000ce4d0 0x002a18 0x002b30 R   0x1
     GNU_STACK      0x000000 0x0000000000000000 0x0000000000000000 0x000000 0x000000 RW  0

========== 6. note 段（E077 关注：ELF 签名段是否仍在） ==========
-- /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefiextract
     [ 2] .note.ohos.ident  NOTE             00000000000002c8  000002c8
     [39] .codesign         PROGBITS         0000000000000000  0012c000
   note 段条数 = 1
-- /storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefifind
     [ 2] .note.ohos.ident  NOTE             00000000000002c8  000002c8
     [39] .codesign         PROGBITS         0000000000000000  00102000
   note 段条数 = 1
```

（该探针第 7 节的 `find` 深度写浅了、未命中包目录，故显示 `package folder = <not found>`；
包内布局已在 §7.4 用另一种方式取到，结论不受影响。）

★ 两个此前**没有实测据**的细节在这里定案：
1. `NEEDED` **不是** 1 条 —— 除 `libc.so` 外还有 `libc++_shared.so`（均为平台自带）。
   因此 `conanfile.py` / `manifest.yaml` / 本文件原先"无任何运行时 `.so` 依赖 /
   纯静态链接"的措辞已按此行实测改写为"**不产出第三方 `.so`，`NEEDED` 只剩平台自带的
   两个**"。真缺陷在于措辞，不在于配方行为。
2. E077 的两件事**同时成立**：`RPATH`/`RUNPATH` 条目数为 0（没有触发安装期 relink），
   而 `.note.ohos.ident` 与 `.codesign` 段**都还在**（签名没被写坏）。
   再叠加二进制能直接跑起来（`-v` → `NE alpha 73 (Oct  4 2026)`、rc=0），
   构成"签名完好 + 可加载"的闭环，而不是只靠"没有 RPATH"这一条间接推断。

### 7.8 最终配方复跑（Stage 5a，提交版）✅

**为什么又跑一次**：`readelf` 取证（§7.7）证明配方注释里"纯静态链接、无任何运行时
`.so` 依赖"的措辞不准确，需改 `conanfile.py`；而**改 `conanfile.py` 会换 recipe hash**
⇒ 必须在提交前把改动后的配方重跑一遍，否则会出现"文档写的 hash ≠ 仓库里的配方"。

载荷：`uefitool-archive.tar.gz` sha256
`2f1d1ca208df7b8b09605483b1796c52a688882b995d1db311dd7d941e984143`（77408 B），
`sha256sum -c` 全 OK；载荷内 `knowledge/drafts/` 计 **8** 个文件（4 条草稿 × 2）。

```
========== A. 刷新载荷 + 校验 ==========
tar sha256 = 2f1d1ca208df7b8b09605483b1796c52a688882b995d1db311dd7d941e984143
tar bytes  = 77408
  uefitool-archive.tar.gz: OK
--- 载荷里 conanfile.py 的那句注释（确认是新版）---
  49:  * `CMAKE_SKIP_RPATH=ON` + `CMAKE_SKIP_INSTALL_RPATH=ON`：本包**不产出任何
--- 载荷里的草稿数（应 8）---
8

========== B. conan create（最终） ==========
conan create rc = 0
log lines = 356
--- 关键行 ---
  262:[100%] Built target UEFIFind
  275:100% tests passed, 0 tests failed out of 3
  289:uefitool/0.28.0-a73: package(): Packaged 2 files: uefiextract, uefifind
  290:uefitool/0.28.0-a73: package(): Packaged 1 '.md' file: LICENSE.md
  291:uefitool/0.28.0-a73: package(): Packaged 1 '.csv' file: guids.csv
  292:uefitool/0.28.0-a73: Created package revision eb6bed38adf631a33bb31cff0d31a1e4
  294:uefitool/0.28.0-a73: Full package reference: uefitool/0.28.0-a73#bb0813fe038ff0ccc7b1525eb894a2e4:6b129b068851896169fae42d399fa922d239ce8a#eb6bed38adf631a33bb31cff0d31a1e4
  295:uefitool/0.28.0-a73: Package folder /storage/Users/currentUser/.conan2/p/b/uefita91bb7e91a5aa/p
  354:--- uefitool consumer: 28 checks run, 0 failed ---
  355:ALL CHECKS PASSED (28/28)
--- 计数 ---
  Building CXX/C object = 149
  warning:              = 0
  error:/fatal:         = 0
  ok N 条               = 28
  not ok N 条           = 0
--- 二进制 hash（新配方）---
  uefiextract: size=1235456 sha256=52dd9dce0dc6dd65f7581e11e8a82527af8ba3f5ff59cd1f7b54696932a39d91
      path=/storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefiextract
  uefifind: size=1063424 sha256=ca609260b134074f50ae2ed24147121eadba8c6cd48d3b0b74a8a65141b64653
      path=/storage/Users/currentUser/.conan2/p/b/uefit6c67fa809ad98/p/bin/uefifind
```

**与 §7.1 的对照**（本节最有价值的一条结论）：

| 项 | Stage 2R（`#a75862c9…`） | Stage 5a（`#bb0813fe…`） | 结论 |
|---|---|---|---|
| recipe revision | `a75862c9e282c0883d82f6b28dde08ad` | `bb0813fe038ff0ccc7b1525eb894a2e4` | 变了（改过 `conanfile.py`） |
| `package_id` | `6b129b068851896169fae42d399fa922d239ce8a` | 同上 | 不变 |
| package revision | `eb6bed38adf631a33bb31cff0d31a1e4` | 同上 | 不变 |
| `uefiextract` sha256 | `52dd9dce…39d91` | 同上 | **逐字节一致** |
| `uefifind` sha256 | `ca609260…64653` | 同上 | **逐字节一致** |
| `ctest` | 3/3 | 3/3 | 不变 |
| 消费者用例 | 28/28 | 28/28 | 不变 |

⇒ 注释修订**只影响 recipe hash**，产物零变化。这同时反证了"改了注释也必须重跑"
这条纪律是必要的：否则仓库里的配方与文档里引用的 hash 会对不上。

**本地 CI 模拟（Stage 5a）**：`CI_RC=0`，日志 492 行，全部闸口 pass：

```
  G0_RESULT=pass
  KC_RESULT=pass
  JC_RESULT=pass
  L0_RESULT=pass: all checks passed
  L1_RESULT=pass: upstream tests + test_package executed
  L2_RESULT=pass: uefiextract --version OK, uefifind --version OK
  L4_RESULT=pass: no patches
  L5_RESULT=pass: bin/ has content
    Total:   1
    Success: 1
    Failed:  0
    Pass rate: 100.0% (1/1)
--- L0j 单独回显 ---
  16:[step] L0j: Checking version collision with registry (R37)...
  17:        [ok] version not in registry yet (first publish)
```

`L0j`（R37：版本号是否与 registry 撞车）实测回显
`[ok] version not in registry yet (first publish)` ⇒ 本库该版本号**首次发布**，
不存在与已发布版本冲突的风险。

同样出现 **12 行** curl 缺失的 `[fail]`（与 §7.6 同一非阻塞现象，成因已在 §7.6 说明）；
除此之外**失败面为空**（"失败面（非 curl）"段无输出）。

**收尾状态**：真机工作树里只剩两行**与本包无关**的改动 ——
`M archives/l/libxext/README.md`、`M archives/l/libxext/manifest.yaml`（**他人遗留**，
本 PR 不触碰，故提交时 `git add` 只限本包路径 + 8 个草稿文件，**绝不 `-A`**）；
`ci-metadata.json` / `conanfile.py.confbak` 一类中间产物**无残留**。

### 7.9 提交文件清单核对（提交前最后一道扫查）✅

CI 模拟打印 `prdiff = 189418 bytes / 20 files`，而交付目录 `find` 到 **21** 个文件。
"少文件"是 PR 级事故，不能靠推断，于是单独查了一遍（**结论：不是漏文件，而是
`.gitignore` 把 1 个文件挡在了外面**）。

**第一步：查明差在哪**

```
========== .gitignore 相关实测 ==========
  .gitignore 总行数 = 308
  # 质量报告（每次重新生成）
  reports/
  reports/quality-report.md
  reports/test-report.md
  reports/calibration-report.md
--- 被忽略判定 (git check-ignore -v) ---
  .gitignore:96:reports/                          archives/u/uefitool/0.28.0-a73/reports/pr-body.md
  .gitignore:240:ci-metadata.json                 archives/u/uefitool/0.28.0-a73/ci-metadata.json
  .gitignore:211:**/test_package/conanbuild*.sh   archives/u/uefitool/0.28.0-a73/test_package/conanbuild.sh
```

真机 `conan create` 还会在包目录留下 8 个 conan 运行产物
（`ci-metadata.json` + `test_package/{conanbuild,conanbuildenv-release-armv8,conanrun,
conanrunenv-release-armv8,deactivate_conanbuild,deactivate_conanrun,deactivate_conanrunenv-release-armv8}.sh`），
它们全部被忽略且**不在交付目录里**，所以不参与计数。

**第二步：`reports/` 到底该不该入库？拿全仓实践取证**

```
========== 仓库里 */reports/ 的文件名分布 ==========
      628 test-report.md
      428 audit-result.json
      277 conan-verify-report.md
      220 pr-body.md          ← 本文件同名者，全仓 220 个
      108 quality-report.md
       49 w3-local-ci.log
       43 W0-report.md
  reports 文件总数 = 2697
--- 实例 ---
  archives/a/ace/8.0.5/reports/pr-body.md
  archives/a/appconfig/1.71.1/reports/pr-body.md
  archives/l/libgenome/1.3.11-svn20110227.4616/reports/pr-body.md   ← 2026-10-03 入库
```

⇒ **`*/reports/` 下的文件（尤其 `pr-body.md`）是这套工作流的常规交付物，全仓已有 2697 个**。
`.gitignore` 第 96 行的 `reports/` 一行（注释写明"质量报告（**每次重新生成**）"）
本意是忽略**仓库根目录**下由 CI 每次重跑生成的那几份报告，但**写成了无前导斜杠的
`reports/`**，于是变成对**任意层级**生效 —— 这是仓库配置层面的既有现象。

**处置**：本 PR 用 **`git add -f`** 显式加入 `reports/pr-body.md`，
与仓库内已有的 220 个同类文件保持一致（**不修改 `.gitignore`** —— 全仓配置不属本包职责，
且"为改 `ci/` 等公共配置单独提 PR"是已知会被关单的做法）。

**第三步：确认本包是全新引入、且不踩 G0**

```
========== main 上的现状 ==========
  archives/u/uefitool 在 origin/main 上的文件数 = 0
  origin/main = d66f94cc12  !13628 merge feat/libadwaita-1.7.12 into main
  G0 根目录白名单（24 项）：.gitattributes .gitcode .gitignore CONTRIBUTING.md KNOW_YOUR_WHY.md
    LICENSE README.md SKILL.md SUMMARY.md archives ci code config docs feedback knowledge
    probes references scripts skills temp templates tests
```

⇒ `archives/u/uefitool` 在 `main` 上**完全不存在**，本包是**全新引入**（`git cat-file -e`
对 13 个路径**全部返回 NEW**），不存在与已合入版本冲突的问题；本 PR 只往既有的
`archives/` 与 `knowledge/` 下加内容，G0 白名单不受影响。

**第四步：最终提交的 21 个文件**

| 组 | 个数 | 内容 |
|---|---|---|
| `archives/u/uefitool/0.28.0-a73/` | 9 | `conanfile.py`、`conandata.yml`、`manifest.yaml`、`notes.md`、`cmake/CMakeLists.txt`、`test_package/{conanfile.py, test.sh, make_fixture.py, MANIFEST.yml}` |
| `archives/u/uefitool/0.28.0-a73/reports/` | 1 | `pr-body.md`（`git add -f`） |
| `archives/u/uefitool/`（跨版本层） | 3 | `README.md`、`manifest.yaml`、`commands.json` |
| `knowledge/drafts/` | 8 | 4 条草稿 ×（`.kv` + `.md`） |
| **合计** | **21** | 21 条全部落在 `archives/` 与 `knowledge/` 内 |

### 7.10 ★ 索引里的 intent-to-add 残留（提交前必须清掉，否则会提交空文件）

本地 CI 模拟会用 `git add -N` 把变更文件标进索引以便生成 diff。**`git add -N`
（intent-to-add）在索引里留下的是"指向空 blob 的条目"**，此时：

```
========== git ls-files -s（本包 20 条全为空 blob） ==========
  100644 e69de29bb2d1d6434b8b29ae775ad8c2e48c5391 0	archives/u/uefitool/0.28.0-a73/cmake/CMakeLists.txt
  100755 e69de29bb2d1d6434b8b29ae775ad8c2e48c5391 0	archives/u/uefitool/0.28.0-a73/conanfile.py
  ...（共 20 条）
  小计 = 20
--- 全仓空 blob 计数 = 159 ---
```

`e69de29b…` 就是 git 的**空 blob** 哈希。⇒ **若此时直接 `git commit`，这 20 个文件会以
0 字节入库**。全仓共有 **159** 条这类残留（`archives/p/parallel` 16 条、其它包若干），
说明这是本地验证流程的普遍现象，不是本包特有。

**处置**：提交前用**明确路径**重新 `git add`（覆盖 intent-to-add 条目），
并在 add 之后**回读 `git ls-files -s` 自校验** —— 判据是这 21 条的 blob 哈希
**不再等于 `e69de29b…`**。这一步写进了提交脚本的闸口。

★ 另一条同处的实测结论：真机的 `cat` 是 toybox 实现，**不支持 `-n`**
（`cat: Unknown option 'n'`），下发脚本里一律改用 `sed -n` / `awk`。

---

## 8. 路径B（知识库扩展）候选素材

本 PR 附带的知识库草稿见 `knowledge/drafts/`（提交到仓库的草稿目录）。
本节登记选题与**全量池查重**结论（查重工具：`kb-scan.py`，扫
`knowledge/doc/` 541 条 + `knowledge/drafts/` 3853 文件，共 4394 文件）。

| # | 候选主题 | 查重锚点 | 命中 | 判定 |
|---|---|---|---|---|
| 1 | Qt6 GUI 子目录被无条件耦合进根工程，零 Qt 依赖的 CLI 也被连带阻断 | `ADD_SUBDIRECTORY+Qt6` / `FIND_PACKAGE+Qt6` | 3 / 38 | 🟡 低命中，但需与 `DRAFT-kf6-top-level-component-negotiation`（顶层组件可选化协商）显式区分 ⇒ 写 `similar_to` |
| 2 | `guids.csv` 只进 GUI Qt 资源 + 按 CWD 查找 + 三重静默降级 | `guids.csv` / `initGuidDatabase` / `guiddatabase` / `qrc+alias` | **0 / 0 / 0 / 0** | ✅ 全零命中 |
| 3 | `uefiextract <img> guids` 在 GUID 库为空时打印用法并 `rc=1` —— 收集函数按 `text` 字段筛选（普通文件该字段恒空）+ 该分支缺终结 `return` | `print_usage` / `guidDatabaseFromTreeRecursive` / `fall-through` / `U_INVALID_PARAMETER` | **0 / 0 / 0 / 0** | ✅ 全零命中；**由真机 `conan create` 的第 28 条消费者用例实测触发**，非推演 |
| 4 | 同一包内多个 CLI 的退出码契约不对称 ⇒ 消费者测试不能套同一模板 | `UEFIExtract` / `UEFIFind` | **0 / 0** | ✅ 全零命中 |

**已否决的候选**（记录在此以免重复尝试）：

- **"`.manifest` 塞进 `ADD_EXECUTABLE` 在非 MSVC 平台会失败"** —— 实测**不成立**。
  用 cmake 4.3.4 做最小复现（`add_executable(mfapp main.c app.manifest)` +
  zig clang + Ninja），**configure 成功**，且 `app.manifest` 被 CMake 识别为
  **`MANIFESTS` 目标属性**写进了 `build.ninja`（`MANIFESTS = …\app.manifest`），
  不是简单忽略也不是报错。真机 Linux 语义下该属性的行为**无法在主机上验证**，
  因此不写条目（宁缺勿假）。
- **"`PROJECT_SOURCES` 混编 C 与 C++ 会让 `-std=c++11` 报错"** —— 实测是
  **本地手写编译命令**的问题，CMake 自身按扩展名分派语言，构建路径下不存在该问题。
- **"clang + libc++ 下 `-Wnullability-completeness` 刷屏"** —— 主机侧用 clang +
  libc++ 编译上游 38 个 C++ 翻译单元时，曾每单元稳定产出 119 条该警告，一度列为
  候选。但真机 `conan create` 的完整日志中 **`warning` 行数为 0** ⇒ 该前提在
  **OHOS 的 clang 15 + libc++** 上**不成立**。据此**撤下**该草稿（对应的
  `.kv` / `.md` 已从 `knowledge/drafts/` 删除），转而把这条实测事实写进
  `manifest.yaml` 的 `knowledge_gained`，作为"本包不需要任何 `-Werror` 豁免"
  的**正面证据**。宁缺勿假。

---

## 9. 参考坐标（供复审快速定位）

| 事实 | 位置 |
|---|---|
| 根工程无条件拉 GUI | `CMakeLists.txt:5`（`ADD_SUBDIRECTORY(UEFITool)`） |
| Qt6 硬依赖 | `UEFITool/CMakeLists.txt:9` |
| `uefiextract` 装载点 | `UEFIExtract/CMakeLists.txt:95`（`ADD_EXECUTABLE`） |
| `uefifind` 装载点 | `UEFIFind/CMakeLists.txt:85` |
| GUID 库初始化（CWD 相对路径） | `UEFIExtract/uefiextract_main.cpp:51` |
| GUID 库空实现分支 | `common/guiddatabase.cpp:92-105`（`#else`） |
| GUID 名查表与裸格式回退 | `common/ffs.cpp:233`；声明默认值 `common/ffs.h:25` |
| 卷名取可读名 | `common/ffsparser.cpp:1520` |
| 文件名取可读名 | `common/ffsparser.cpp:2222` |
| GUI 侧用 Qt 资源路径 | `UEFITool/uefitool.cpp:141,1476`（`":/guids.csv"`） |
| `guids.csv` 进 Qt 资源 | `UEFITool/uefitool.qrc:3` |
| 版本串 | `version.h`（`"NE alpha 73"`） |
| 上游零测试的 fuzzer 入口 | `fuzzing/ffsparser_fuzzer.cpp` |
| GUID 库收集函数的字段筛选（取 `text` 而非 `name`） | `common/guiddatabase.cpp:124` |
| `guids` 分支缺终结 `return`（落穿到函数尾部兜底） | `UEFIExtract/uefiextract_main.cpp:102-107` → `:216-218` |
| 对照：`report` 分支有显式 `return 1` | `UEFIExtract/uefiextract_main.cpp:109-120` |
| 可读名写入 `name` 字段 | `common/ffsparser.cpp:2222`（`name = guidToUString(...)`）、`:2262`（`addItem()` 第 4 个实参） |
| 报告侧读 `name`（故 report 能看到 GUID 名） | `common/ffsreport.cpp:66` |
| Volume Top File 判定 | `common/ffsparser.cpp:2243-2249`；GUID 字面量 `common/ffs.cpp:74`；常量定义 `common/ffs.h`（`EFI_FFS_VOLUME_TOP_FILE_GUID`） |
| 缺 VTF ⇒ 整遍跳过第二道解析 | `common/ffsparser.cpp:103-109`；`performSecondPass()` 做的是 reset vector / FIT / protected range / TE image base 的**地址侧分析**（`:3806-3835`），**不是**段解析 |
| FFS 文件头校验和的真实算法 | `common/ffsparser.cpp:2187-2191`（8 位补码，且**排除 `State`**） |
| FFSv2 固定数据校验和 `0xAA` | `common/ffs.h:301`（`FFS_FIXED_CHECKSUM2`） |
