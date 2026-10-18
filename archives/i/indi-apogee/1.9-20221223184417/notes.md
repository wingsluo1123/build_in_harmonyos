# indi-apogee 1.9-20221223184417 适配笔记

## 编译环境

- 构建系统: cmake (Conan 2)
- 编译器: clang / clang++ (OHOS SDK)
- 目标平台: HarmonyOS PC / OHOS aarch64（target triple `aarch64-linux-ohos`）
- 上游: indilib/indi-3rdparty 的 `indi-apogee` 驱动（阿普奇 Apogee CCD 相机 / 滤光轮），
  取 Debian 官方重新打包的 orig 源码包作为来源（上游 Apogee 相机 SDK 为闭源，社区版由 Debian 维护）
- 版本: 1.9，上游快照时间戳 `20221223184417`

## 编译步骤

1. 下载源码包 `indi-apogee_1.9+20221223184417.orig.tar.gz`（65133 字节）
2. 校验 SHA256：`50819156e313a90346d01c99c888e339ee0fcff71271ca62397d49e79405ee80`
3. 应用 4 个补丁：`patches/0001`、`patches/0002` 改 `cmake_modules/`（纯可移植性）；
   `patches/0003`、`patches/0004` 把两个源文件里**从 libindi 基类继承的属性**迁移到 2.x 的
   `INDI::Property` API（内容照搬上游 indi-3rdparty 的同名迁移，见「关键结论二」）
4. `conan create`，同时构建两个可执行文件并安装 XML 元数据
5. 打包 `<prefix>/bin/indi_apogee_ccd`、`<prefix>/bin/indi_apogee_wheel`、`<prefix>/share/indi/indi_apogee.xml`
6. 对两个二进制做 ELF 自签名（E077）——不签名则真机拒绝执行，见问题 10

## 产物

| 可执行文件 | 源文件 | 链接库 |
|---|---|---|
| `indi_apogee_ccd` | `apogee_ccd.cpp` | INDI + CFITSIO + libapogee |
| `indi_apogee_wheel` | `apogee_cfw.cpp` | INDI + libapogee |

两个可执行文件共用同一份 `cmake_modules/`；`apogee_ccd.cpp` 里还带一份被 `#if 0` 关闭的
CFW 内部实现（`ApogeeCCD::connectCFW()`，1511–1698 行），上游早已改为由
`ApogeeFilterWheel` 类承担，属历史残留，不需要处理。

两个二进制在 `package()` 里完成 ELF 自签名（E077），否则真机 execve 直接 EPERM，见问题 10。

## 依赖

| 包 | 版本 | 用途 |
|---|---|---|
| `libindi` | 2.2.2.1 | INDI 框架（`INDI::CCD` / `INDI::FilterWheel` / `INDI::FilterInterface` + 驱动入口 `main`） |
| `libapogee3` | 3.2+20221221183454 | Apogee 相机驱动库（`ApogeeCam` / `ApogeeFilterWheel` / `FindDeviceUsb` / `FindDeviceEthernet`） |
| `cfitsio` | 4.6.4 | CCD 图像 FITS 输出 |
| `zlib` | 1.3.1.1 | CFITSIO 传递依赖，CMakeLists 显式 `find_package(ZLIB REQUIRED)` |
| `curl` | 8.15.0.1 | **显式声明**（`force=True`）用于消解版本冲突，见问题 7；实际使用者是 libapogee3 的以太网相机传输与 libindi |

四个依赖在归档中均已存在，无需新增第三方配方。

## 关键结论一：驱动入口 `main()` 来自 libindi，源码里本来就没有

初次读源码时会发现一个"缺文件"式的假象：`apogee_ccd.cpp`、`apogee_cfw.cpp` 全文中
**不存在任何 `main`**（连子串都不出现，`grep -c main` = 0），但 `CMakeLists.txt` 却用它们
`add_executable` 出两个可执行文件。

原因是 INDI 3rdparty 的通用约定：

- 入口定义在 **libindi** 的 `libs/indibase/indidrivermain.c`，编译进 `libindidriver`
  （即 `INDI_LIBRARIES` 的组成部分，见 `libs/indibase/CMakeLists.txt:140`）；
- 该 `main()` 解析 stdin 上的 INDI XML 分发到驱动，把设备属性定义写到 stdout；
  它**只认 `-v`（verbose）**，之后进入 `eventLoop()` 阻塞等待客户端；
  当 stdin 关闭（EOF）时打印 `EOF` 并 `exit(1)`；
- 驱动侧只需提供一个静态实例（本包 `apogee_ccd.cpp:81` / `apogee_cfw.cpp:31` 的
  `static std::unique_ptr<...> ...(new ...)`），设备即自动注册。

**这直接决定了 test_package 该怎么写**：`indi_apogee_ccd -v` 既不是"打印版本"也不返回 0，
拿退出码或 `-v` 当探针是错的。正确探针是喂一条 `<getProperties version="1.7"/>`
再看 stdout 里有没有 `<def...>`（见 `test_package/test.sh`）。

## 关键结论二：要区分「驱动自己声明的属性」与「从 libindi 基类继承的属性」

驱动**自己**声明的属性确实全是纯 C API，libindi 2.2.2 也完整保留着这套 API，这部分不用改；
但**从 libindi 基类继承**的属性在 2.x 已被换成 `INDI::Property` 对象，这部分必须迁移 ——
首轮真机编译的报错全部落在这一类上（`apogee_ccd.cpp` 触发 `-ferror-limit` 前报了 20 个、
`apogee_cfw.cpp` 9 个）。

先看「自己声明的属性」这一半（与同族 `indi-eqmod` 的差异在这里成立）：

| | indi-eqmod | indi-apogee |
|---|---|---|
| 属性声明 | `INDI::PropertyNumber` 等 C++ 对象 | `INumberVectorProperty` / `ISwitchVectorProperty` 裸结构体 |
| define | `defineProperty(Prop)` | `defineProperty(&Prop)` |
| 传参 | `Prop->sp[i]`、`Prop.nsp` | `Prop.sp[i]`、`Prop.nsp` |
| 结论 | 需 2 个源码补丁 | 自己声明的属性**无需源码补丁** |

libindi 2.2.2 完整保留了这套 C API（`defineProperty` 的裸指针重载带
`INDI_DEPRECATED` 标记但仍可用；`IUFill*` / `IUSaveText` / `IUUpdate*` 见
`libs/indicore/indidevapi.c`），且 `INDI::FilterInterface` 的
`initProperties` / `updateProperties` / `processNumber` / `processText` / `saveConfigItems`
签名与 apogee 的调用完全一致；`INDI::CCD` 的 `SetTemperature(int)` /
`StartExposure(float)` / `UpdateCCDBin(int,int)` 等虚函数签名也与 apogee 的 override 一致。

再看「从基类继承的属性」这一半 —— 这里是 libindi 2.x 真正的破坏性变更：

| 属性 | libindi 1.x | libindi 2.2.2 | 报错形态 |
|---|---|---|---|
| `INDI::CCD::TemperatureNP` | 裸 `INumberVectorProperty`（另有别名 `TemperatureN`） | `INDI::PropertyNumber TemperatureNP {1}`，**`TemperatureN` 已删除** | `use of undeclared identifier 'TemperatureN'` |
| `INDI::FilterInterface::FilterSlotNP` | 同上（别名 `FilterSlotN`） | `INDI::PropertyNumber FilterSlotNP {1}` | 同上 |
| `INDI::FilterInterface::FilterNameTP` | 裸 `ITextVectorProperty` | `INDI::PropertyText FilterNameTP {0}` | `->name` 可用但已 deprecated |

对应的访问方式迁移（`INDI::Property` 的 `operator&` 被设为 protected，专门用来拦住旧写法）：

| 旧写法 | 新写法 |
|---|---|
| `TemperatureN[0].value = x` | `TemperatureNP[0].setValue(x)` |
| `TemperatureN[0].value`（读） | `TemperatureNP[0].getValue()` |
| `TemperatureNP.s = IPS_ALERT` | `TemperatureNP.setState(IPS_ALERT)` |
| `switch (TemperatureNP.s)` | `switch (TemperatureNP.getState())` |
| `IDSetNumber(&TemperatureNP, nullptr)` | `TemperatureNP.apply()` |
| `FilterSlotN[0].max = n` | `FilterSlotNP[0].setMax(n)` |
| `!strcmp(name, FilterSlotNP.name)` 加 `processNumber(...)` | 直接用 `INDI::FilterInterface::processNumber(...)` 的 `bool` 返回值 |

`PropertyBasic::operator[]` 返回的 `WidgetView<INumber>` **直接继承 `INumber`**，
所以 `[0].value` / `[0].max` 这类裸成员访问在新 API 下也不报错 —— 但本项目按上游写法统一
用 `setValue` / `getValue` / `setMax`。

补丁来源：**上游 indi-3rdparty master 早就迁移完了**，且 `apogee_ccd.cpp` / `apogee_cfw.cpp`
从 Debian 快照（2022-12-23）到上游 master 的**唯一**差异就是这次迁移（`apogee_ccd.h` /
`apogee_cfw.h` 逐字节相同）。因此 `patches/0003`、`patches/0004` 逐字节照搬上游 diff，
不手写迁移，避免引入行为差异。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 不认识 HarmonyOS 平台（E092） | OHOS 的 CMake 平台文件缺失 | toolchain 显式 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` |
| 2 | `cmake_minimum_required(VERSION 3.0)` 在 CMake ≥ 4 直接报错（真机 configure 死在**第 1 行**） | CMake 4.x 移除了 < 3.5 的兼容策略。关键坑：`CMAKE_POLICY_VERSION_MINIMUM` **只在命令行 `-D`（cache 变量）下对第 1 行有效** —— 工具链文件是 CMake 在 `project()` 时才加载的，晚于 `CMakeLists.txt:1`，所以 `tc.variables` / `tc.cache_variables` 设的同名变量都读不到（实测：只写 toolchain 时原样报错） | `cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})` 走命令行 `-D`；toolchain 里那份仅作兜底。归档内 `archives/a/amqp-cpp/4.3.27` 有同款注释与做法 |
| 3 | 编译报缺 `std::any` | `CMakeCommon.cmake` 强制 `CMAKE_CXX_STANDARD 14`，libindi 2.2.2.1 头文件用了 C++17 的 `std::any` | 补丁 `0001`（14 → 17），recipe 再以 `CMAKE_CXX_STANDARD=17` 兜底 |
| 4 | `find_package(INDI)` 报 `failed to detect INDI version` | `FindINDI.cmake` 的版本正则只认不带引号的 `INDI_VERSION 2.2.2`，libindi 2.2.2 头文件写的是带引号的 `INDI_VERSION "2.2.2"` | 补丁 `0002`（正则加 `\"?`） |
| 5 | `#include <libapogee/Alta.h>` 找不到头文件 | `libapogee3` 的 `cpp_info.includedirs` 是 `include/libapogee`（因其公有头互相用扁平 `#include "CameraInfo.h"`），而 apogee 源码用命名空间式 `<libapogee/Xxx.h>`；在 Debian 上两种写法同时成立只因为 `/usr/include` 在隐式搜索路径中 | recipe 里把 `libapogee3` 的 include 根追加进 `CMAKE_CXX_FLAGS`（`-I<libapogee3>/include`），**不改源码** |
| 6 | `install(FILES indi_apogee.xml DESTINATION ${INDI_DATA_DIR})` 会装进名为 `INDI_DATA_DIR-NOTFOUND` 的目录 | `INDI_DATA_DIR` 来自 `FindINDI.cmake` 的 `find_path(drivers.xml PATH_SUFFIXES share/indi)`，而制品仓的 `libindi` 不安装 `drivers.xml`，`find_path` 失败留下 `<VAR>-NOTFOUND` | recipe 以 `-DINDI_DATA_DIR=<install_prefix>/share/indi` 显式钉住 |
| 7 | `ERROR: Version conflict: Conflict between curl/8.15.0 and curl/8.15.0.1 in the graph. Conflict originates from libapogee3/3.2+20221221183454` | `libindi/2.2.2.1` 钉 `curl/8.15.0.1`，而 `libapogee3` 钉 `curl/8.15.0` —— 本包是归档里第一个同时拉这两条的包，无先例可循 | recipe 声明 `self.requires("curl/8.15.0.1", force=True)`。选 8.15.0.1 是因为二者**同源码**（8.15.0.1 的 notes：`Upstream source: curl 8.15.0 release archive (same source as 8.15.0)`，是 R37 适配修复，修 8.15.0 在 HMDFS 上的日志目录问题），ABI 一致；反向迁就 8.15.0 会把该缺陷带回来。用 `force=True` 而非 `override=True`：`libapogee3` 的 `generate()` 调 `CMakeDeps(self).generate()`，需要 curl 保持**真实节点**（有 `package_folder`），override-only 节点的 `package_folder` 是 `None`（归档内 `archives/n/nymphcast/0.2-alpha0/conanfile.py` 对这点有明确注释） |
| 8 | (预留) 真机构建若报 `undefined reference to main` | 说明所用 libindi 制品未编入 `indidrivermain.c` | 此时才需要补一个 `main()`（照 libindi 上游写法），属最后手段 |
| 9 | 编译期 29 个报错：`use of undeclared identifier 'TemperatureN'/'FilterSlotN'`、`no member named 's'/'name' in 'INDI::PropertyNumber'`、`'operator&' is a protected member of 'INDI::PropertyBasic<_INumber>'` | libindi 2.x 把**基类**属性（`INDI::CCD::TemperatureNP`、`INDI::FilterInterface::FilterSlotNP/FilterNameTP`）从裸 C 结构体换成了 `INDI::PropertyNumber`/`PropertyText` 对象，旧名 `TemperatureN`/`FilterSlotN` 直接删除；`operator&` 被设为 protected 以拦住 `IDSetNumber(&Prop, ...)` 这类旧写法。驱动源码写于 libindi 1.x 时代，故全部失配 | 补丁 `0003`/`0004` 迁移访问方式（见「关键结论二」的对照表）：赋/取值改 `setValue`/`getValue`、`X.s` 改 `setState`/`getState`、`IDSetNumber(&X, nullptr)` 改 `X.apply()`、`[0].max` 改 `[0].setMax()`、`strcmp(X.name)+processX` 改为直接用 `processX` 的 `bool` 返回值。内容逐字节取自上游 indi-3rdparty master（该 diff 即上游对这两个文件的全部改动） |
| 10 | 编译与打包**都成功**后，test_package 执行探针报 `.../p/bin/indi_apogee_ccd: Operation not permitted`（两个二进制都如此） | OHOS 内核只执行带有效 `.codesign` 数据的 ELF（知识条目 E077）。此时 `ls -l` 是 0755、`[ -x ]` 为真、ELF 可加载，缺的是**签名**而不是权限位 —— 所以 `chmod` 解决不了 | 在 `package()` 里自签名（作用于最终 package 内的文件）：`llvm-objcopy --remove-section .codesign`（首次本无该段，非 0 退出属正常）→ `binary-sign-tool sign -inFile ... -outFile ... -selfSign 1` → `os.replace` 回写 + `chmod 0755`。工具定位：`/data/service/hnp/bin/binary-sign-tool`，兜底 `HNP_PUBLIC_HOME` 与 `PATH`；OHOS 上找不到则直接报错，非 OHOS 目标只告警跳过 |
| 11 | 签名修好后（第 2 轮真机），test_package 报 `Error loading shared library libindidriver.so.2` / `libindiAlignmentDriver.so.2: (needed by .../indi_apogee_ccd)`，其后紧跟一片 `Error relocating ...: _ZN4INDI…` / `IUFillSwitch: symbol not found`（`indi_apogee_wheel` 同） | 产物链的是 libindi 的**共享库**（libindi 默认 `shared=False`，但同时产出 `.a` 与 `.so`，`INDI_BUILD_SHARED` 恒 ON，CMake 的 `find_library` 优先选 `.so`，故 `DT_NEEDED` 记的是 `.so.2`）。但**根因不是「路径没拼上」**：HMDFS 上**未签名（或签名失效）的 OHOS 共享库无法 `mmap(PROT_EXEC)`**（E537/R49 的收窄结论 + E077），而依赖 libdir 里那批 `.so` 恰好都没有有效签名。**这条报错不带 errno**，读起来像「搜索路径上找不到」，实际是候选文件被逐个否掉 —— 极易误诊成环境变量问题（本项目先按误诊断改了一轮）。`libindidriver` 没加载上，它的符号自然全缺；那一大片 `symbol not found` 是**同一个**根因的连带后果，不是第二个问题 | 三轮演进，最终方案是**自包含 staging**：(1) 首轮以为「缺 libdir」，用 `Environment().append("LD_LIBRARY_PATH", 全部 host 依赖 libdir)` 再叠加 conanrun —— **这条路走不通**：把未签名的 libdir 挂上路径，loader 只会更早撞上坏候选；且实测追加拼出的值里出现过 `<某 libdir>: /storage/…/stage`（冒号后带空格 ⇒ `" /storage/…"` 是无效目录，staging 根本没上路径）。(2) 改为在 test_package 自己的目录搭 `stage/`：复制两个产物二进制 + 全部 host 依赖 libdir 下的 `.so`（`cp -L` 语义解软链，让 `DT_NEEDED` 里每个 SONAME 都能命中）+ 缺失的 `libc++_shared.so`，逐个 `llvm-objcopy --remove-section .codesign` → `binary-sign-tool -selfSign 1` → `chmod 0755`。(3) 末轮修掉最后一个路径毛病：`LD_LIBRARY_PATH` **改由 `test.sh` 自己用显式冒号把 BINDIR 前置**（不再走 conan 的 `Environment.append`，也就不受追加顺序影响），staging 同时挪出仓库树到 `~/.cache/indi-apogee-test-stage`（原先建在 `test_package/stage/`，约 30MB 未跟踪、污染工作树）。真机对照实验：同一套 `LD_LIBRARY_PATH`，只把三个 `.so` 剥签重签，探针即从失败变为 `def count: 39`。**注意同族 `indi-eqmod` 并没有解决这个问题**：其 `test.sh` 在 `-v` 失败后走 `WARN: … 跳过执行探针`，退化为 `test -x` 存在性检查，因此从不曾证明 `.so` 可加载 |

## 源码修改

补丁文件（均在 `cmake_modules/`，均为 `patch_type: portability`）：

| 补丁 | 内容 |
|---|---|
| `patches/0001-cmake_modules-CMakeCommon.cmake.patch` | `set(CMAKE_CXX_STANDARD 14)` → `17` |
| `patches/0002-cmake_modules-FindINDI.cmake.patch` | 版本检测正则兼容带引号的 `INDI_VERSION` |
| `patches/0003-apogee_ccd.cpp.patch` | libindi 2.x 属性 API 迁移（13 处 hunk，+30/−34 行） |
| `patches/0004-apogee_cfw.cpp.patch` | libindi 2.x 属性 API 迁移（5 处 hunk，+9/−9 行） |

`0001`/`0002` 与同族 `indi-eqmod` 系列逐字节相同（同族包在
`archives/i/indi-eqmod/1.0-20230126190232`，是独立提交的另一个包）；`0003`/`0004` 逐字节取自上游
indi-3rdparty master 的 `indi-apogee/apogee_ccd.cpp`、`apogee_cfw.cpp`（该 diff 即上游对这两个
文件的全部改动，diff 里除属性访问方式外无任何其它变化）。四个补丁均已
`patch -p1 --dry-run --forward` 验证在 indi-apogee 源码上干净应用（exit 0）。
`apogee_ccd.h` / `apogee_cfw.h` 与上游逐字节一致，未改；**驱动的业务逻辑零改动**，
改的只是属性访问写法。

## 验证结果

```bash
conan create archives/i/indi-apogee/1.9-20221223184417 \
  --profile:host=ci/conan/profiles/ohos-aarch64 \
  --profile:build=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

真机（HarmonyOS PC，OHOS aarch64）2026-10-03 实测通过。`test()` 的 staging 行：

```
OHOS staging: 2 个产物二进制 + 30 个依赖 .so，其中 32 个 ELF 已重签；
staging 目录=/storage/Users/currentUser/.cache/indi-apogee-test-stage（LD_LIBRARY_PATH 由 test.sh 前置 BINDIR，不叠加 conanrun）
```

`test_package/test.sh` 的断言输出：

```
OK: indi_apogee_ccd 存在且可执行 -> /storage/Users/currentUser/.cache/indi-apogee-test-stage/indi_apogee_ccd
OK: indi_apogee_ccd 响应 getProperties，返回 39 条属性定义
OK: indi_apogee_wheel 存在且可执行 -> /storage/Users/currentUser/.cache/indi-apogee-test-stage/indi_apogee_wheel
OK: indi_apogee_wheel 响应 getProperties，返回 33 条属性定义
[test] indi-apogee 冒烟测试通过（2 个二进制 × 存在性 + INDI getProperties 往返）
```

三点说明：

- 两个二进制的属性定义条数（39 / 33）与先前那次「只把三个 `.so` 剥签重签」的对照实验
  （`def count: 39`）一致，两处独立证据互为印证。
- `WARN: staging 与依赖包目录里都没有 libc++_shared.so，改由默认搜索路径解析` 是**已知良性**
  告警：实测该版本下并未影响加载（探针全绿），故只告警、不作致命处理。
- 冒烟测试覆盖的是两个 `bin/` 下的可执行文件；`share/indi/indi_apogee.xml` 由 `package()`
  安装，但不在探针的断言范围内。

## 上游测试说明

本版本源码包内**不含任何测试**：没有 `test/` 目录，没有 ctest 用例
（与同族 `indi-eqmod` 自带 `test/test_eqmod.cpp` 的 GTest 用例不同）。
因此 test_package 采取"消费者视角"的冒烟测试，见 `test_package/MANIFEST.yml` 与
`test_package/test.sh`：

1. 两个二进制是否在 PATH 中且可执行；
2. 对每个二进制喂一条 INDI `<getProperties version="1.7"/>`，stdout 必须回出 `<def...>`
   属性定义 —— 这一步同时覆盖了 ELF 可加载、依赖 so 可解析、libindi 链接正确、
   驱动已注册到事件循环四件事。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/indi_apogee_ccd` | Apogee CCD 相机驱动 |
| `bin/indi_apogee_wheel` | Apogee 滤光轮驱动 |
| `share/indi/indi_apogee.xml` | INDI 驱动元数据（由 `indi_apogee.xml.cmake` 生成） |

## 注意事项

- 本包为 `package_type = "application"`（纯 CLI 工具包），`cpp_info.libs = []`。
- 许可：源码文件头声明 LGPL-2.1-or-later；随包附带的 `COPYING.LIB` 是 1991 年 6 月的
  "GNU Library General Public License Version 2"（LGPL-2.0 文本），两者措辞略有出入，
  Debian 侧按 LGPL-2.1+ 处理，本配方采用 `LGPL-2.1-or-later`。
- 驱动运行需真实 Apogee 硬件或 INDI 客户端，test_package 不连接硬件，只做协议层往返。
- 本包是**工具类型**（`package_type = "application"` + `bin/` 下有可执行文件），除版本级四个文件
  外还需要软件级元数据：`archives/i/indi-apogee/commands.json`（R38/L0k 门禁：工具类型必须有）、
  `manifest.yaml`、`README.md`。
- 两个二进制必须**已签名**（E077）才能在任何 OHOS 环境执行；若将来对它们做 `patchelf`/`strip`，
  签名会失效，必须重新签名后再打包。
- 两个二进制是**动态链接** libindi（真机实测缺的正是 `libindidriver.so.2`、
  `libindiAlignmentDriver.so.2`）的。运行进程需要这些库，**但光把依赖包的 `libdir` 挂上
  `LD_LIBRARY_PATH` 并不管用**：那些目录里的 `.so` 在 HMDFS 上未签名、加载不了，loader
  只会更早撞上坏候选（见问题 11）。可行做法是**自包含 staging** —— 把产物二进制与全部依赖
  `.so` 的**已重签副本**放进同一个目录，再把这个目录**前置**到 `LD_LIBRARY_PATH`。
  `test_package` 就是这么做的（`~/.cache/indi-apogee-test-stage`，由 `test.sh` 自己前置）。
  真实消费方同样需要 —— 这不是本包的缺陷，而是"Conan 里分发动态链接的 CLI 工具"在 OHOS /
  HMDFS 上的固有要求。
- 上游 master 已把 `CMakeLists.txt:1` 的 `cmake_minimum_required` 从 3.0 提到 3.16；本配方
  **不**采用这个改动，而是走 configure 命令行 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（纯配方侧，
  见问题 2），让源码补丁只保留必需的那几处。
