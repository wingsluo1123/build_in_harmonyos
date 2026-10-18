# PreviSat 7.2.1.3 适配笔记（HarmonyOS PC / OHOS aarch64）

## 软件简介

PreviSat 是开源卫星跟踪软件（Astropedia）：轨道传播（SGP4/SDP4）、过境/掩星/闪光与
Starlink 过境预报、星空图与雷达图、卫星数据库（SQLite）、AOS/LOS 声音提示等。
上游 7.2.1.3 为 **Qt6 + CMake** 桌面应用（C++20，`qt_add_executable`），产物为单一可执行
程序（无库），运行时同时依赖 Qt6 **Core/Gui/Widgets/Network/Xml/Concurrent/Sql/Multimedia**。

- 官方站点：http://previsat.free.fr/ 、http://astropedia.free.fr
- 源码（官方下载入口，SourceForge previsat 项目）：
  `previsat-7.2.1.3-src.tar.gz`，SHA256 `0cbe9a3c66f03612a4b2e86f2b955bc09d2c52be7b116cb4514db77c780845ed`

## 编译环境

- 构建系统：cmake（上游 `CMakeLists.txt`，要求 ≥3.24；本机 cmake 4.1.2）
- 编译器：clang 15.0.4 / clang++ 15.0.4（OHOS SDK），libc++，C++20（上游 `CMAKE_CXX_STANDARD 20`）
- 目标平台：HarmonyOS PC aarch64（os=OHOS，arch=armv8），Release
- 状态：built（conan create + test_package 运行时验证通过）

## 依赖（W0 预检）

PreviSat 一次性要求 8 个 Qt6 模块，制品仓中不存在单一基础包覆盖全部（模块与变体矩阵）：

| Qt6 模块 | 需求证据 | 提供者（制品仓实况） |
|---|---|---|
| Core / Gui / Widgets / Network / Xml / Concurrent | `find_package(Qt6 REQUIRED COMPONENTS ...)` | `qtbase-sql-dbus/6.11.1`（已发布二进制，实测无 PrintSupport/Multimedia） |
| Sql（卫星数据库：`QSqlDatabase::addDatabase("QSQLITE")`） | `src/configuration/configuration.cpp:1136`、`donnees.cpp`、`tle.cpp` 等 | 仅 `qtbase-sql-dbus/6.11.1`（sql ON）或 `qtbase/6.11.1.3`（sql+print ON） |
| Multimedia（`QSoundEffect` 声音提示） | `src/interface/previsat.cpp`、`onglets/general/general.cpp` | `qtmultimedia/6.11.1`（精确 requires `qtbase/6.11.1`） |
| PrintSupport | `CMakeLists.txt` REQUIRED 列表（源码内**仅 2 处未使用的 include**，无任何 `QPrinter`/`QPrintDialog` 调用） | 无与 `qtmultimedia` 兼容的提供者（详见下） |

关键约束与取舍：

1. `qtmultimedia/6.11.1` 精确 requires `qtbase/6.11.1`，而 `qtbase/6.11.1` 的
   `FEATURE_sql=OFF`、`FEATURE_printsupport=OFF`（实测包内无 `libQt6Sql.so`/`libQt6PrintSupport.so`
   及对应 CMake 配置）；
2. 含 Sql 的 `qtbase/6.11.1.3`（sql+print+dbus ON，已发布二进制）与 `qtmultimedia` 的
   `qtbase/6.11.1` 精确 pin **冲突**（`Version conflict: Conflict between qtbase/6.11.1 and
   qtbase/6.11.1.3 in the graph. Conflict originates from qtmultimedia/6.11.1`）；强行
   `override=True` 会让 `qtmultimedia`/`qtshadertools` 失去预编译二进制（实测
   `Missing prebuilt package for 'qtmultimedia/6.11.1', 'qtshadertools/6.11.1'`），属 R36 禁止的
   源码重建依赖；
3. 因此采用仓库既有组合（同 actiona 3.11.1 的做法）：**`qtbase-sql-dbus/6.11.1`（Sql 变体）
   + `qtmultimedia/6.11.1`**，两侧均为已发布预编译二进制；
4. `PrintSupport` 在本版本源码中**已无实际用途**（全树仅剩 `previsat.cpp` 的两行未使用
   include），故从 `find_package` 与链接列表移除（补丁 0001+0002），**不损失任何功能**；
   `Multimedia`（声音提示）、`Sql`（卫星库）均保留。

> W0 预检命令（依赖均已在制品仓发布）：
> `conan download qtbase-sql-dbus/6.11.1 -r=ohpcd` / `conan download qtmultimedia/6.11.1 -r=ohpcd`
> → 均取到二进制包（本机 `~/.conan2` 实测 `--build=never` 安装成功）。

## 编译步骤

1. `init-build previsat 7.2.1.3 --url=<SourceForge 官方直链>`（基线 286 个文件）
2. `lang-preflight`：task=cpp / detected=cpp（70 个 cpp，主体占比 100%）→ 通过
3. 源码适配（编辑 `$BUILD_SRC_DIR` → 生成 7 个补丁，见下）
4. 编写 `conanfile.py`（CMake + 多 Qt6 前缀装配 + 可重定位打包 + ELF 签名）
5. `conan create`（真实构建 + 安装后运行 test_package）

## 遇到的问题与解决方案（首错 → 根因 → 修复 → 重新验证）

| # | 首个错误 | 根因 | 修复 | 重新验证 |
|---|---|---|---|---|
| 1 | `BadZipFile: File is not a zip file`（`source()`） | URL 以 `/download` 结尾，conan `get()` 无法从扩展名判定格式，按 zip 解压 | 改用官方直链 `https://downloads.sourceforge.net/project/previsat/.../previsat-7.2.1.3-src.tar.gz`（同 sha256，实测 5,475,164 字节一致） | `conan create` 进入 configure |
| 2 | `luneconst.h:80:25: error: constexpr variable 'GA' must be initialized by a constant expression`（note: non-constexpr function 'sqrt'） | 上游在 `constexpr` 初始化中调用 C 库 `sqrt()`；GCC 允许常量折叠，clang/libc++ 不允许（实测该 clang 连 `__builtin_sqrt` 也不接受，`-std=c++23` 亦不支持） | 补丁 0003/0004：将 `sqrt(...)` 表达式替换为其 **IEEE-754 double 字面值**（位级等价，实测 GA=0.8888194417315589 → `3fec71357849271a`、KE=0.07436691613317341 → `3fb309b5d0b2444b`，与运行期 `sqrt` 结果逐位一致） | 编译推进到下一个错误 |
| 3 | `carte.cpp:1168:37: error: alias template 'QVectorIterator' requires template arguments` | Qt6 中 `QVectorIterator<T>` 是 `QListIterator<T>` 的**别名模板**，`QVectorIterator it(x)` 依赖 C++20 别名模板 CTAD；clang 15 未实现该特性（GCC 11+/MSVC 支持） | 补丁 0005：3 处补显式模板参数 `<QPolygonF>` | 编译推进 |
| 4 | `configuration.cpp:1265:27: error: redefinition of 'listeFics'` | 上游 `VerificationArborescences()` 在 `#if defined(Q_OS_LINUX)` 分支与主干各定义同名局部变量（同一作用域）；OHOS 的 Qt6 定义 `Q_OS_LINUX`，因此暴露该上游缺陷 | 补丁 0006：把前者重命名为 `listeFicsRacine`（含其 `foreach`），语义不变 | 编译推进 |
| 5 | `date.cpp:704:25: error: alias template 'QVectorIterator' requires template arguments` | 同 #3（第 4 处） | 补丁 0007：补 `<QPointF>` | **编译链接成功，包产出** |
| 6 | 运行期：`Le répertoire /usr/share/Astropedia/PreviSat/data n'existe pas, veuillez réinstaller PreviSat`（应用回退到系统数据目录） | `PORTABLE_BUILD` 未生效：① 上游在 `project()` 之前用 `if(NOT DEFINED PORTABLE_BUILD)` 取默认值，而 CMakeToolchain 的缓存变量在该处尚不可见；② 上游用 `#if (PORTABLE_BUILD)` 判宏，必须传入**数值**（`1`），传 `ON` 会被当作未定义标识符判为假 | 改为 `cmake.configure(variables={"PORTABLE_BUILD": "1", "BUILD_TEST": "OFF"})`（命令行 `-D`，先于 CMakeLists 生效） | 配置输出变为 `Build portable software configuration`、`PORTABLE_BUILD = 1`；运行后应用在可执行文件旁生成 `log/`、`cache/`、`data/config`、`Astropedia/`，且不再有 `/usr/share` 报错 |
| 7 | `license.txt` 未打包（`copy(COPYING)` 无命中） | 上游 release 包内无 `COPYING`，许可证文本位于 `infos/license.txt` | `package()` 改从 `infos/license.txt` 复制 | 打包日志出现 `Packaged 1 '.txt' file: license.txt` |

（另有 2 处**预判性**适配，未造成实际失败：PrintSupport 模块与链接项移除；GCC 专属 release
选项剔除——后者若保留，clang 会报 `error: unknown argument: '-fbranch-target-load-optimize'` 等 8 条硬错误。）

## 源码修改（补丁）

| 补丁 | 修改内容 |
|------|----------|
| `patches/0001-CMakeLists-qt6-modules-and-clang-flags.patch` | `CMakeLists.txt`：`find_package`/`target_link_libraries` 去掉 Qt6 PrintSupport；RELEASE_FLAGS 去掉 8 个 GCC 专属选项（`-fbranch-target-load-optimize`、`-fcprop-registers`、`-fcrossjumping`、`-floop-optimize`、`-foptimize-register-move`、`-fpeephole`、`-fpeephole2`、`-frerun-cse-after-loop`） |
| `patches/0002-src-interface-previsat-unused-print-includes.patch` | `src/interface/previsat.cpp`：删除未使用的 `<QPrintDialog>`/`<QPrinter>` include |
| `patches/0003-src-librairies-corps-systemesolaire-luneconst-constexpr-sqrt.patch` | `luneconst.h`：`GA` 由 `sqrt(1. - W0)` 改为等值 double 字面值 |
| `patches/0004-src-librairies-corps-terreconst-constexpr-sqrt.patch` | `terreconst.h`：`KE` 由 `NB_SEC_PAR_MIN * sqrt(GE / RAYON^3)` 改为等值 double 字面值 |
| `patches/0005-src-interface-carte-carte-qvectoriterator-ctad.patch` | `carte.cpp`：3 处 `QVectorIterator` 补 `<QPolygonF>` |
| `patches/0006-src-configuration-configuration-listeFics-redefinition.patch` | `configuration.cpp`：`Q_OS_LINUX` 分支内 `listeFics` 重命名为 `listeFicsRacine` |
| `patches/0007-src-librairies-dates-date-qvectoriterator-ctad.patch` | `date.cpp`：`QVectorIterator` 补 `<QPointF>` |

> 补丁中无任何平台宏（无 `__OHOS__`）；未删除任何上游功能代码；未改动任何测试用例。
> 说明：上述补丁为 **CRLF 保真**的统一 diff——上游多数源文件为 CRLF，仓库 `refresh-patch --auto`
> 以文本模式读取会丢失 `\r`（生成物 `patch --dry-run` 失败），故本次以等价格式手工生成并逐个
> `patch -p1 --dry-run` 验证（详见 `reports/skill-feedback.md`）。

## 上游测试（R51 三步法）

### 1. 清点（真实入口 + 证据）

- 上游 `CMakeLists.txt` 提供 `BUILD_TEST` 选项（默认 false），为 ON 时：
  `include(CTest)` + `add_test(NAME PreviSatTest COMMAND PreviSatTest)`，测试源码为
  `test/src/*.cpp|*.h`（见 `CMakeLists.txt` 第 151-209 行）。
- **但 7.2.1.3 发布源码包中不存在 `test/` 目录**。实测包内顶层条目仅：
  `CMakeLists.txt`、`data/`、`infos/`、`resources/`、`src/`、`translations/`、
  `resources.qrc`、`icone.rc`（`ls` 输出见日志）。
- 因此上游测试目标**无源码可构建**：`BUILD_TEST=ON` 会因 `TEST_SOURCES` 为空而无法生成
  `PreviSatTest`，`ctest` 无用例可跑。配方按 `BUILD_TEST=OFF` 构建。

结论：**上游本版本无自动化测试入口可用**（不是"未运行"，而是发布包内不包含测试材料）；
未修改任何上游测试用例。

### 2. 实际执行

- `ctest` 在无注册用例的情况下不产生统计（`BUILD_TEST=OFF`）。
- 替代真实运行时验证：`test_package/test.sh`（下述第 3 节）在 `conan create` 内**实际运行
  安装后的应用**，覆盖依赖链、数据布局、SQL 驱动等运行时行为。
- 日志路径：`reports/conan-create.log`（完整 conan create 日志，含 test_package 全部输出）。

## 新增鸿蒙特有测试（`test_package/`，运行时行为，无静态断言）

`test_package/test.sh`（由 `test_package/conanfile.py::test()` 调用，conanrun 环境 +
`QT_PLUGIN_PATH` 指向各 Qt6 依赖包 `plugins/`）：

| # | 项 | 观测方式 | 结果 |
|---|---|---|---|
| 1 | 安装产物完整 | `bin/PreviSat` + `bin/data/satellites.db` + `bin/data/sound/flare.wav` + `bin/translations/qt_fr.qm` | 通过 |
| 2 | 已签名可执行 ELF | `llvm-readelf -S` 检出 `.codesign`（鸿蒙仅执行已签名 ELF），随后实际执行 | 通过 |
| 3 | 无头启动（offscreen QPA） | `PreviSat -platform offscreen` 后台运行 12s，进程存活且无缺库/缺平台插件错误 | 通过（pid 存活） |
| 4 | 可重定位数据根 + 运行期目录 | 运行后在可执行文件旁出现 `log/`、`cache/`、`data/config`、`Astropedia/`；日志含 `PreviSat 7.2.1.3` 与 `Lecture fichier configuration.xml OK`；stderr 无 `n'existe pas, veuillez réinstaller`（即未回退 `/usr/share`） | 通过 |
| 5 | Qt SQLite 驱动可用 | 应用日志/PREVI 输出无 `QSQLITE driver not loaded`，卫星库正常打开 | 通过 |

## 验证结果

```bash
# 1) 依赖预检（W0）：qtbase-sql-dbus/6.11.1 + qtmultimedia/6.11.1 均取到发布二进制
conan install --requires=qtbase-sql-dbus/6.11.1 --requires=qtmultimedia/6.11.1 ...
# 2) 语言预检（R47）：task=cpp / detected=cpp
python3 scripts/ohc-run.py lang-preflight previsat 7.2.1.3 --src $BUILD_SRC_DIR
# 3) conan create（真实构建 + 安装后运行）
conan create . --version=7.2.1.3 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --build=previsat/7.2.1.3
# → EXIT=0；test_package: ALL TESTS PASSED（5/5，日志 reports/conan-create.log）
```

包内产物（`conan create` 实测）：

```
bin/PreviSat                        # 3.4 MB，已签名（.codesign）
bin/data/{satellites.db,config,preferences,sound,stars,boundaries,coordinates,html,resources,map,taiutc.dat}
bin/translations/{PreviSat_en.ts,PreviSat_ja.ts,qt_en.qm,qt_fr.qm,qt_ja.qm}
licenses/license.txt
```

## 注意事项

- **应用依赖窗口系统**：鸿蒙 PC 镜像无 X11/Wayland，正常使用需经 offscreen（或后续平台插件）
  运行；本仓库 `accessibility` 等 Qt6 应用同样以 `QT_QPA_PLATFORM=offscreen` 做无头验证。
- **PORTABLE_BUILD=ON（数值 1）**：应用按可执行文件所在目录解析 `data/`、`translations/`，
  并在同级目录写入 `log/`、`cache/`、`starlink/`、`Astropedia/`（上游"便携版"设计）；
  因此安装前缀须可写，或由使用者按需重定向。
- 非致命告警：无字体目录（Qt6 不再附带字体，`QFontDatabase` 警告，离屏渲染不受影响）；
  启动期 `TelechargementFichier ... ISS.OEM_J2K_EPH.xml` 下载失败（沙箱无外网，属环境），
  应用继续运行；offscreen 插件 `does not support propagateSizeHints()`。
- 链接期仍有 `-s`、`-fbounds-check`、`-fcaller-saves`、`-fstrength-reduce`、`-malign-double`
  等 GCC 风格参数（clang 仅告警不报错），保留上游原样；签名在打包阶段执行（位于 `-s` 之后）。
- 本包未导出任何库/头文件（纯应用），`commands.json` 声明 `binary: true`（可执行 GUI 程序）。
---

**编译结束**: 2026-10-16 20:23
**最终状态**: built
