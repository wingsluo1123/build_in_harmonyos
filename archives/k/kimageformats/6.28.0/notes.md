# kimageformats 6.28.0 适配笔记

> 上游 KDE Frameworks 6 图像格式插件集合：为 Qt 补齐发行版自带的 QImageIOHandler
> 插件（本构建面 21 个格式：ANI/DDS/EXR/FF/HDR/IFF/PCX/PFM/PIC/PSD/PXR/QOI/RAS/
> RAW/RGB/SCT/TGA/TIM/XCF/AVIF/JP2），语言 C++。
> 归档名/分支名 `kimageformats`，上游仓 invent.kde.org/frameworks/kimageformats。

## 编译环境
- 构建系统: CMake（Conan 2.29.1，CMakeToolchain 生成器；cpack 关闭）
- 编译日期: 2026-10-17
- 编译器: clang 15（profile `ohos-aarch64-full`：os=OHOS、arch=armv8、
  build_type=Release、compiler.cppstd=17、compiler.libcxx=libc++）
- 依赖版本: qtbase/6.11.1、openexr/3.3.4、libraw/0.22.1、openjpeg/2.5.4、
  libavif/1.4.2.2；build: ecm/6.28.0；transitive: imath/3.2.2、libdav1d/1.5.4、
  libdeflate/1.22、libjpeg/10、zlib/1.3.1.1
- 状态: 真机 create 收官（见「真机验证」）

## 适配决策

### 1. 平台门与插件范围门
- `KF_IGNORE_PLATFORM_CHECK=TRUE`：上游 ECM 平台检测的允许清单里没有 OHOS。
- 范围门（见「插件面与范围决策」）：DDS/EXR/LibRaw/JP2/AVIF 由配方 option 打开，
  HEIF/JXL 关闭；JXR 经 `KIMAGEFORMATS_WITH_KNOWN_CRASHES_JXR=OFF` 关闭（上游
  目录名即标注 known crashes）；KRA/ORA 经 `CMAKE_DISABLE_FIND_PACKAGE_KF6Archive`
  关闭；EPS 自然关闭——`CMAKE_SYSTEM_NAME=HarmonyOS` 使上游的 UNIX 判定为假，
  且制品仓 qtbase 不含 Qt6::PrintSupport。
- 插件安装位置钉死：`KDE_INSTALL_USE_QT_SYS_PATHS=OFF`、
  `KDE_INSTALL_QTPLUGINDIR=plugins`、`KDE_INSTALL_PLUGINDIR=lib/plugins`，
  产物落在 `<package>/plugins/imageformats`，消费者加一条
  `QCoreApplication::addLibraryPath` 即可看到全部格式。

### 2. CMakeDeps 必须显式实例化 + conan_cmakedeps_paths 机制
本包依赖链（OpenEXR→Imath、libavif→dav1d、libdeflate 等）消费的是 CMakeDeps
生成的 config；而 qtbase 是 `cmake_find_mode=none`，CMakeDeps 不会把它的
`lib/cmake` 加进 `CMAKE_PREFIX_PATH`。配方自己写
`generators/conan_cmakedeps_paths.cmake`（CMakeToolchain 会自动 include），
按搜索优先级prepend：qtbase 的 cmake/lib/include 目录、ecm 的
share/ECM/cmake、OpenEXR 及其传递依赖包目录、kif-shims、openjpeg/imath 包
目录。`build()` 前 `CMakeDeps(self).generate()` 显式生成依赖 config。
（对照：kif5 5.116 没踩这个坑是因其依赖包自带 config + 手动 prefix 注入。）

### 3. OpenJPEG 大写变量契约
上游 `src/imageformats/CMakeLists.txt` 消费大写
`OPENJPEG_INCLUDE_DIRS`/`OPENJPEG_LIBRARIES`，写测试门还读
`OPENJPEG_MAJOR_MINOR_BUILD_VERSION` 大写三元组（值 2.5.4 > 2000-write 门的
2.5.3）。CMakeDeps 生成的 config 只定义 mixed-case。做法：把 openjpeg 包目录
前置 `CMAKE_PREFIX_PATH`，让其自带的 `OpenJPEGConfig.cmake` 在 CONFIG 查找中
先胜（该 config 会设大写变量）；toolchain 里大写三元组 + include/libs 值兜底。

### 4. Imath 平头 include
`src/imageformats/exr.cpp` 直接 `#include <ImathBox.h>`（平文件路径）；
制品仓 imath/3.2.2 盘上只有 `include/Imath/*`。CMakeDeps 的 `Imath::Imath`
只挂 include 根目录。做法：imath 包目录前置 `CMAKE_PREFIX_PATH`，用其自带
`ImathConfig.cmake`（`INTERFACE_INCLUDE_DIRECTORIES` 同时含 `include/` 与
`include/Imath`）先胜。

### 5. libavif 字面 target shim
上游把 AVIF 插件链到字面 target `avif`（无命名空间），CMakeDeps 只提供
`libavif::libavif`。做法：`generators/kif-shims/libavif-config.cmake` 转发
生成的 libavif-config，再补 `avif` INTERFACE 别名；配套 version 文件同时
接受上游两次版本请求（0.8.2 与当前 1.4.2.2）。shim 目录在搜索序最前。

### 6. LibRaw find 模块
上游 `cmake/find-modules/FindLibRaw.cmake` 是裸 find_path/find_library 模块，
读复数名 `LibRaw_LIBRARIES`/`LibRaw_r_LIBRARIES` 并建 `LibRaw::LibRaw` 目标；
conan 版 libraw config 定义的是 `libraw::libraw`，对不上。做法：
`CMAKE_FIND_PACKAGE_PREFER_CONFIG` 刻意**不设**（让模块模式生效），并在
toolchain 预置 `LibRaw_INCLUDE_DIR`/`LibRaw_LIBRARIES`/`LibRaw_r_LIBRARIES`
指向包内实际路径，find 结果确定。

### 7. SONAME-only 共享库规则（kitemviews 6.28.0 先例）
OHOS CMake 没有 Platform/HarmonyOS 模块，`CMAKE_SHARED_LIBRARY_SONAME_*`
保持为空，lld 不会写 DT_SONAME，消费者 DT_NEEDED 会漏构建机路径。配方经
`CMAKE_USER_MAKE_RULES_OVERRIDE_C/CXX` 注入 `-Wl,-soname,`；同时
`CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`（HMDFS 拒 symlink，版本号全名链
落不了盘）。`CMAKE_SHARED_LIBRARY_RUNTIME_*`（rpath）标志**刻意不定义**：
一旦定义，cmake install() 会重写 ELF 剥 RUNPATH，设备 dlopen 重写后的库会
EACCES（kitemviews 6.28.0 实踩）。本包为纯插件包（无链接库、无可执行文件），
`package()` 就是 `cmake.install()` 的字节级拷贝。

### 8. 测试接法（BUILD_TESTING=ON，ctest 挂在 build() 里）
- `_run_upstream_tests()` 在 `build()` 的 `can_run(self)` 下执行：
  `ctest --test-dir <build> --output-on-failure --no-tests=error -E
  "kimageformats-write-avif"`。
- 测试环境：`QT_QPA_PLATFORM=offscreen`、`CTEST_OUTPUT_ON_FAILURE=1`、
  `CTEST_PARALLEL_LEVEL=1`（设备并行串行化）、HOME/XDG_RUNTIME_DIR(0700)/
  XDG_CACHE/CONFIG/DATA 全部重导向到 build 目录（防设备家目录污染）；
  `LD_LIBRARY_PATH` 前置各依赖 lib 与 `/system/lib64`、SDK llvm lib
  （ECM 的 KDEInstallDirs6 在 configure 期要跑 qtbase 的 qtpaths 宿主工具，
  lld 的 libxml2 与之都要先解析到兼容 libc++_shared.so，kconfig/kitemviews
  先例）；`QT_PLUGIN_PATH` 指向 build 的 bin 与各依赖 plugins 目录。

### 9. 依赖制品缺陷：openexr 绝对路径 DT_NEEDED 与本地修复
制品仓 openexr/3.3.4 的 `libOpenEXR-3_3.so.32` 的 DT_NEEDED 里，
`libImath.so` 条目烘焙了**构建机缓存绝对路径**
`/storage/Users/currentUser/.cache/conan2/p/imath97b7356a3fe4a/p/lib/libImath.so`。
musl 装载器对含 `/` 的条目直接按路径 open，LD_LIBRARY_PATH 救不了——EXR
插件 dlopen 即断（kif5 5.116 / kio-fuse 5.1.1 同款缺陷与先例）。
**设备本地修复**：把同名包（imath/3.2.2 的包短名恰好就是
`imath97b7356a3fe4a`，跨机器确定）的真实 `libImath.so` 复制到该 .cache 路径，
链即自洽；修复后 read-exr、write-exr 与 test_package 的 EXR 往返全过。
**CI 侧无需任何操作**：CI 自身的 conan home 就是
`/storage/Users/currentUser/.cache/conan2`（kio-fuse build 108343 日志：
`Exported to cache folder: /storage/Users/currentUser/.cache/conan2/...`），
依赖包天然装在该路径，链天然成立——配方内不做任何依赖改写、补丁不碰上游。

## 插件面与范围决策

| 格式面 | 决策 | 依据 |
|--------|------|------|
| ENABLED (21) | 无外部依赖的 16 个（ani ff hdr iff pcx pic pfm psd pxr qoi ras rgb sct tim tga xcf）+ dds + exr(openexr/3.3.4) + raw(libraw/0.22.1) + jp2(openjpeg/2.5.4) + avif(libavif/1.4.2.2) | 依赖全部在制品仓可解析 |
| heif | OFF | libheif 未上架制品仓 |
| jxl | OFF | libjxl 未上架制品仓 |
| jxr | OFF | 上游目录名即标注 known crashes；依赖（jxrlib）亦未上架 |
| kra/ora | OFF | 需 KF6Archive 恰好 6.28.0（KF_DEP_VERSION 精确匹配），制品仓仅有 karchive/6.26.0 |
| eps | OFF | 上游在非 UNIX 下不注册；qtbase 无 Qt6::PrintSupport |
| avif 解码 | ON（read-avif 通过） | libavif/1.4.2.2 为纯解码构建 |
| avif 编码 | 测不了 | 同上无 AV1 编码器（write-avif 环境性排除，见「真机验证」） |

## 真机验证（2026-10-17，HarmonyOS PC aarch64 真机）

单次 `conan create` 干净全链（CREATE_RC=0）：

1. **构建**：configure（qtpaths 前置修复后一次通过）→ build（21 个插件全量编译）。
2. **上游 ctest**：`ctest -E "kimageformats-write-avif"` →
   **`100% tests passed, 0 tests failed out of 29`**，逐项：
   read-{ff,hdr,iff,pcx,pfm,psd,pxr,qoi,ras,rgb,sct,tim,tga,dds,avif,jp2,xcf,exr,raw}
   19 项 + write-{dds,jp2,pcx,pic,qoi,rgb,tga,exr} 8 项 + pic + ani。
3. **排除项（1 项，环境性）**：write-avif。制品仓 libavif/1.4.2.2 是纯解码
   构建（无 AV1 编码器），真实失败原文：
   `FAIL : libraries configuration is missing necessary encoder(s) for avif!`
   上游 write 测试对无编码器配置本就按 fail 退出，属"制品能力面"而非本包缺陷。
4. **read-psd / read-exr 不排除的理由**（上游 6.28 行为差异，与 kif5 时代的
   排除口径不同）：缺 TIF 对照图的用例被降级为
   `SKIP : birthday.pdd: comparison image birthday.tif cannot be loaded due to
   the lack of TIF plugin!`——read-psd Totals **`90 passed, 40 skipped, 0 failed`**；
   seek 型 handler 的顺序设备读取轮次降级为
   `SKIP : ... (don't worry, it's ok)`——read-exr Totals **`7 passed, 3 skipped,
   0 failed`**；write-exr 四组 BASIC 4/0、FORMAT 34 passed/0 failed/2 skipped、
   SIZE 315 passed/0 failed/1 skipped、NULL 1/0。
5. **打包**：`Created package revision cd021a1bee7bee4db655a6ee821c70b0`，
   `Package kimageformats/6.28.0:46b1c24b34791981c426a70872cd32235e91d0fc`，
   产物 `plugins/imageformats/` 下 21 个 `kimg_*.so`
   （ani avif dds exr ff hdr iff jp2 pcx pfm pic psd pxr qoi ras raw rgb sct
   tim tga xcf）。
6. **test_package**：8 案例全过——**`TEST SUMMARY: 8 passed, 0 failed`**
   （插件广告/HDR/TGA/QOI/DDS/EXR 往返/JP2 往返/包布局，39 项校验点，
   任一无过即非零退出）。EXR 往返是 §9 修复后的端到端复核。
7. **源获取**：conandata 为「官方源 download.kde.org 优先 + NJU 官方镜像
   兜底」URL 列表（sha256 双源同值钉死）；Conan 的 get() 按序尝试。

配方修订（本节数据出自源=镜像单 URL 版配方
`kimageformats/6.28.0#75d59830d9a22290488bf6baadeb49b9`；最终交付 conandata
改为源列表后，`conan-verify-report.md` 的复跑记录对应最终文件集，sha256 不变）。

10-17 W5 独立审计整改复核（`package_type` 元数据 `shared-library`→`library`、
包布局校验点收紧为恰 21 个 `kimg_*.so`、manifest 计数分解措辞与 package_id
出处注释）：再次干净复跑 `conan create`——configure 10.4s → 21 插件全量重编
→ ctest `100% tests passed, 0 tests failed out of 29` → 消费者
`TEST SUMMARY: 8 passed, 0 failed`（含包布局 `TEST PASS`）；本次
`conan-verify-report.md` 即为最终文件集的复跑记录，package_id
（`46b1c24b…`）与 package revision（`cd021a1b…`）同首轮一致。

## 已知限制
- write-avif 依赖 libavif 编码器（见上），read-avif 与插件本体不受影响。
- heif/jxl/jxr/kra/ora/eps 六个插件面未启用（依赖未上架/上游标注/平台面，
  见决策表）；插件广告与包布局用例对缺席做了显式核验。
- RAW 解码行为面由 libraw/0.22.1 决定（read-raw 通过）。

## 交付文件
- `conandata.yml`（源列表 + sha256）、`conanfile.py`（配方，无补丁）
- `test_package/`：conanfile.py、CMakeLists.txt、test_kimageformats.cpp（8 案例
  执行器）、MANIFEST.yml（41 潜在/30 注册/39 校验点口径）
- `manifest.yaml`（本文件）、`notes.md`、`reports/conan-verify-report.md`
  （设备侧 verify 工具产物）。
