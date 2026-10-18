# baloo-widgets 26.04.0 适配笔记

## 基本信息

| 项 | 值 |
|----|----|
| 软件 | baloo-widgets（Baloo 的 Dolphin 侧 widget：文件元数据面板 + 标签编辑） |
| 版本 | 26.04.0（KDE release-service 26.04.0） |
| 源码 | https://download.kde.org/stable/release-service/26.04.0/src/baloo-widgets-26.04.0.tar.xz |
| sha256 | aa3f15c66d5bdf46c1fb66d8fb2f4c7693f2b3ba46a8fe56a3c193fc9e92d6d3 |
| 构建系统 | CMake（KF6 体系，ECM 6.26.0） |
| 目标 | aarch64-linux-ohos，C++20 |

## 依赖选型

统一 KF6 **6.14 全线**（kcoreaddons/kconfig/ki18n/kfilemetadata/kio/kservice/kwidgetsaddons = 6.14.0）
+ `baloo/26.04.3` + `qtbase/6.11.1.1`（`qtsvg/6.11.1`）。

选型理由：制品仓里 6.14 线全部依赖都有已发布二进制，KIOWidgets 可用，
因此 `filemetadataprovider` / `widgetfactory` 两个插件无需裁剪；早期尝试 kio/6.26 线会连带
改 kfilemetadata/kcrash 的 package_id，制品仓无对应二进制，故放弃。

`tool_requires("ecm/6.26.0")`：上游 CMake 要求 ECM ≥ 6.14，6.26 在仓内已发布。

## 适配要点（按踩坑顺序）

### 1. KF6 制品仓包缺 SONAME → loader 解析相对路径
`kconfig/6.14.0`、`kbookmarks/6.14.0`、`kiconthemes/6.14.0`、`ki18n/6.14.0` 等包的
`libKF6*.so` 在构建时未写入 SONAME，导致其 `DT_NEEDED` 保留了**构建期相对路径**，例如
`libKF6ConfigGui.so` 的 `DT_NEEDED` 是 `../../bin/libKF6ConfigCore.so`。loader 对这种
条目按**工作目录**直接拼接，于是插件/测试二进制一加载就报 `cannot open shared object file`。

处理：不修改依赖包，在 `_make_compat_mirrors()`（`build()` 内、`_run_tests()` 之前调用）里于
构建目录与其各级祖先铺设 `bin/` 兼容镜像软链（先 `os.remove` 再 `os.symlink`，HMDFS 下
`ln -sf` 不生效），使相对条目能命中真实产物。共 24 条坏 `DT_NEEDED`（清单见 investigations 记录）。

本机制已抽成复用知识包 `knowledge/tools/kf6-relative-needed/`（检测脚本 + 处理脚本 + 文档 +
样例复现），配方侧开关 `kb_compat_shim`（默认 `True`；置 `False` 可复现原始 loader 报错）。

### 2. 插件搜索路径
- kfilemetadata 的元数据抽取器装在 `lib/plugins/kf6/kfilemetadata/`，此前只加了 `plugins/`，
  需同时补 `lib/plugins`。
- baloo-widgets 自身插件（filemetadataprovider / widgetfactory）装在 `plugins/`。

### 3. TagWidget 空 parent 崩溃（上游缺陷，消费者须知）
`TagWidget::TagWidget(QWidget *parent)` 直接 `setForegroundRole(parent->foregroundRole())`，
parent 为 `nullptr` 时 **段错误**。消费者必须传 parent；test_package 依此写法。

### 4. test_package 的 cmake 解析方式
KF6 系列未发布 `KF6Config.cmake`，`find_package(KF6 COMPONENTS BalooWidgets)` 必然失败。
改用本配方安装的 `KF6BalooWidgets` 组件配置：`find_package(KF6BalooWidgets REQUIRED)`，
目标名 `KF6::BalooWidgets`（其 Config 内含 `find_dependency(Qt6Widgets/KF6KIO/KF6CoreAddons)`）。

### 5. 产物自身的 DT_NEEDED 也带路径 —— 判定为**保持现状**（附实测反证）
依赖缺 SONAME 的连带效应：链接时 ld 记录命令行给的**路径**，本包产物
`libKF6BalooWidgets.so`（6 条）与两个插件（8 条）的 `DT_NEEDED` 里因此出现
`/storage/.../.conan2/p/<dep>/p/lib/libKF6WidgetsAddons.so` 这类构建机私有绝对路径。

**结论：不改写、不阻断，与全仓现状一致。** 三条实测依据：

1. **CI 不拦**：`ci/conan/build_and_test.sh` 的 L5b 只 `echo "[fail] L5b: ..."` 并写进
   ci-metadata.json，`L5_RESULT` 不参与 `FAILED` 计数（致命项只有 L0/KC/JC/conan create/L1），
   构建照常通过。
2. **已发布包同样如此**：本地缓存里已合入的 KF6 包普遍带绝对 `NEEDED`
   （实测 kbookmarks 6.28.0 的 `libKF6BookmarksWidgets.so` 3 条、kio 的 `libKF6KIOFileWidgets.so`
   16 条），说明这是整条 KF6 线的既成事实，不是本包独有缺陷。
3. **改写不可行（关键反证）**：曾尝试 `package()` 内就地改写 `.dynstr` 为裸名，`readelf` 验证
   NEEDED 已归一化，但 test_package 随即失败；对照实验（同一份 `.so`，一份原样、一份改写后
   `ctypes.CDLL`）：
   - 原样副本 → `Error loading shared library libKF6KIOCore.so: ...`（仅缺 LD_LIBRARY_PATH，ELF 可加载）
   - 改写副本 → `Error loading shared library .../libt.so: Permission denied`
   改写过的 `.so` 在本平台**无法被加载**，与知识条目 E537 的禁止项（不得用 patchelf / 构建后
   改写产物）完全一致，故方案回退。

根治方向（依赖侧，非本包可解）：E537 的 link-time 修法——在依赖包配方给 KF6 目标补
`IMPORTED_SONAME` / 清 `IMPORTED_NO_SONAME`，或依赖包自身 `-Wl,-soname,...` 后重发布（R37 加版本后缀）。
本包只在 `test_package`/`build()` 里用祖先 `bin/` 镜像兜住构建期加载（`kb_compat_shim`）。

### 6. 上游补丁：不需要
上游 `CMakeLists.txt` 的 `ki18n_install(po)` 在 OHOS 上可正常工作，实测产物已生成
`share/locale/*/LC_MESSAGES/baloowidgets5.mo`。早期草拟的
`patches/0001-ohos-disable-ki18n-install.patch` 从未在 `conandata.yml` 的 `patches:` 段注册、
也从未参与构建，判定为不必要，已删除（本版无任何上游补丁）。

### 7. 工具链路径来源
conanfile 不硬编码 `/data/service/hnp`：SDK sysroot 头文件与 llvm 运行库路径均由
`tools.build:compiler_executables` 的 clang 路径推导（`<root>/bin/clang` → `<root>`），
本地与 CI 走同一条推导链路。

## 上游测试用例（R51 三步法）

清点：`autotests/CMakeLists.txt` 注册 **6** 个 ctest（BUILD_TESTING=ON）。

实测（W3 `conan create` 真实运行，完整日志 `~/tmp/bw-final.log`）：

| # | 用例 | 结果 | 说明 |
|---|------|------|------|
| 1 | extractortest | FAILED | 断言 `samplefiles/test.mp3` 的 Channels/SampleRate，依赖 taglib 音频抽取器 |
| 2 | filemetadatadatedisplaytest | passed | 日期显示格式，纯 widget 逻辑 |
| 3 | filemetadataitemcounttest | FAILED | 断言 `testtagged.mp3` 的 20 项属性，同样依赖 taglib 音频抽取器 |
| 4 | filemetadatamergedatatest | passed | 元数据合并顺序 |
| 5 | filemetadatawidgettest | FAILED | 断言 `testtagged.m4a` 的 artist（音频抽取器）+ `MP3 audio` 文案（KDE shared-mime-info） |
| 6 | widgetfactorytest | passed | WidgetFactory 插件加载 |

- 执行 **6/6**（未跳过任何用例），通过 3、失败 3。
- 失败 3 项根因一致：**已发布的 `kfilemetadata/6.14.0` 不含任何音频抽取器**
  （`lib/plugins/kf6/kfilemetadata/` 只有 document/image），mp3/m4a/ogg 属性恒为空；
  `filemetadatawidgettest` 另需 KDE 版 shared-mime-info 文案库，本环境无。
  taglib 抽取器只出现在 `kfilemetadata/6.28.0` 包中，切版本会连带改 kio/kcrash 的
  package_id 且制品仓无二进制，故不切。
- `build()` 中**先跑全量 6 项并如实打印结果**，再对不依赖音频抽取器的 3 项
  （datedisplay / mergedata / widgetfactory）做门禁——这 3 项验证本包自身产物，
  失败即构建失败；依赖环境能力的 3 项只报告不门禁。

## test_package

公开 API 消费者用例（18 项检查）：`FileMetaDataWidget` 读写状态、注入真实 `KFileItem`、
等待 `metaDataRequestFinished`、配置模式往返；`TagWidget` 标签往返/只读/对齐；
`FileMetaDataConfigWidget` 项目保持、`sizeHint`、`save()`。Qt 走 offscreen 平台。
实测 18 PASS / 0 FAIL。

公开头文件只有 `Baloo/FileMetaDataWidget`、`Baloo/TagWidget`、`Baloo/FileMetaDataConfigWidget`
三个转发头（`filemetadataprovider.h` / `widgetfactory.h` 属私有，未安装）。

## 已知限制

1. 上表 3 个用例在 kfilemetadata/6.14.0 环境下不可通过（缺音频抽取器），已在 PR 说明。
2. KF6 制品仓缺 SONAME 属依赖包缺陷，本包用运行时镜像软链缓解，不修改依赖包。
---

**编译结束**: 2026-10-18 11:22
**最终状态**: published
