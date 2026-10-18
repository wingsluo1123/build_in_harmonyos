# qt5-qttranslations 5.15.2 适配笔记

## 基本信息

- 归档版本：5.15.2
- 实际上游版本：Qt 5.15.2（qttranslations 子模块）
- 类型：依赖项（积分赛-依赖池）
- 平台卡号：15281
- taskBranch：feat/qt5-qttranslations-5.15.2
- 本件定位：**纯翻译资源包**（Qt5 翻译 .qm），无可执行文件、无链接库、无编译
- 当前状态：built（conan create 本地全绿）

## 编译环境

- 系统：HarmonyOS PC
- 架构：AArch64（os=OHOS / arch=armv8 / compiler.libcxx=libc++ / cppstd=gnu17）
- 构建系统：资源转换（无 C/C++ 编译；上游为 qmake TEMPLATE=aux 工程）
- 编译器：clang/clang++ 15（本件不编译代码）
- 构建日期：2026-10-16
- conan：2.29.1（OHOS 适配版）

## 源码信息

- 源码包：qttranslations-everywhere-src-5.15.2.tar.xz
- 官方地址：https://download.qt.io/archive/qt/5.15/5.15.2/submodules/qttranslations-everywhere-src-5.15.2.tar.xz
- SHA-256：d5788e86257b21d5323f1efd94376a213e091d1e5e03b45a95dd052b5f570db8（官方源 + 清华/中科大镜像三源一致）
- 上游源码布局：`qttranslations.pro`（TEMPLATE=subdirs）→ `translations/translations.pro`（TEMPLATE=aux）
  - translations/ 含 266 个 `*_??.ts` / `*_??_??.ts` 翻译源

## 为什么"无需编译"

上游 `translations/translations.pro` 是 TEMPLATE=aux，只做两件事：
1. `updateqm` 编译器：`lrelease <in.ts> -qm <out.qm>`（Qt Linguist 资源转换，非编译）；
2. `INSTALLS += translations`：把 `<base>.qm` 安装到 `$$[QT_INSTALL_TRANSLATIONS]`。
另有 `write_file($$OUT_PWD/<module>_en.ts, "<TS></TS>")` 生成 17 个空 source 语言占位
（16 个 TS_MODULES + `qt_en.ts`），它们同样进入 TRANSLATIONS 并被编译为空的 .qm。

因此本配方不做 qmake 复刻，直接按 updateqm 语义逐 .ts 调 lrelease，产物落位
`${prefix}/translations/`（Qt5 QT_INSTALL_TRANSLATIONS 约定）——与上游安装布局一致。

## lrelease 工具链约束（核心）

- 制品仓**没有任何 Qt5 的 qttools 包**：`qt5-qttools/5.15.2`、`qttools/5.15.2` 均 404；
  `qt5-qtbase/5.15.2.2` 只含 Qt5 基础模块（Core/Gui/Network/Widgets/PrintSupport/Xml/DBus），
  **不含 Qt Linguist**（其包内 bin/ 只有 qmake/moc/rcc/uic 等，无 lrelease/lupdate/lconvert）。
- 处置（与 mlite 0.5.5 先例一致，见 `knowledge/drafts/mlite-0.5.5-qt5-qttools-missing-lrelease.kv`）：
  使用已发布的 **Qt6 `qttools/6.11.1.1`** 的 `lrelease` 作为构建工具。
  - Qt6 lrelease 读 Qt5 的 .ts、写标准 .qm；
  - **实测**：Qt6 lrelease 产出的 .qm 可被 **Qt5.15 的 QTranslator 正常加载**
    （本地实测 `qt_zh_CN.qm`：`QTranslator::load()==true` 且 `!isEmpty()`）；
    test_package 用 qt5-qtbase 的 QTranslator 在 CI 内实测复现该结论（非纸面断言）。
- Qt6 lrelease 的运行期依赖：`libQt6Core`/`libQt6Network`（qtbase 6.11.1）+
  `libQt6Qml`（qtdeclarative 6.11.1）+ `libc++_shared`，且该工具 **无 RUNPATH**
  → 配方在调用前显式拼 `LD_LIBRARY_PATH`（Qt6 各包 lib/ + 从 clang++ 路径推导的
  OHOS SDK libc++ 目录）。

## 为什么不复用 qmake 构建上游

尝试用 qt5-qtbase 包内的 qmake 直接驱动 `translations.pro` 失败（实测）：
1. qtbase 包内 `mkspecs/modules-inst/*.pri` 内嵌构建机绝对路径
   （`.../.conan2/p/b/qt5-qXXXX/b/...`），包上传后该目录不存在 → qmake 报
   `Cannot read .../qt_lib_*.pri`（与 mlite/libngf-qt 记录同类）；
2. 上游 `translations.pro` 依赖 Qt 超级模块顶层的 `.qmake.conf`，而独立子模块
   tarball 内没有该文件 → `Project ERROR: Project has no top-level .qmake.conf file.`
故改走"直接 lrelease 转换"路径——更简单、无 qmake 现场依赖、结果与上游 updateqm 等价。

## 产物

- 包内 `translations/` 下共 **283** 个 `.qm`：
  - 266 个来自上游源 `.ts`（含 qt/qtbase/qtdeclarative/qtquickcontrols(2)/qtmultimedia/
    qtscript/qtxmlpatterns/qtconnectivity/qtlocation/qtwebsockets/qtserialport/qtwebengine/
    assistant/designer/linguist/qt_help 各语言）；
  - 17 个空 `_en.qm`（上游 write_file 占位：16 模块 + qt）。
- 落位：`${prefix}/translations/*.qm`（`QT_TRANSLATIONS_PATH` 通过 runenv_info 暴露）。

## 测试

- 上游没有 QTest 测试套件；其"资源生成"挂在上游构建图（updateqm）内，
  本配方在 build() 内逐 .ts 执行并断言每个 .qm 产出（266+17 全绿）。
- test_package（消费者视角，链接 Qt5Core）：
  - 校验 `QT_TRANSLATIONS_PATH` 与 translations/ 目录存在、`.qm` 数量 ≥ 250；
  - 用 **Qt5 运行时 QTranslator** 逐个加载 5 个关键中文翻译
    （qt_zh_CN/assistant_zh_CN/designer_zh_CN/linguist_zh_CN/qt_help_zh_CN），
    断言 `load()==true && !isEmpty()`（证明 Qt5 运行时确实能消费本包产物）。
- 共 13 条断言。

## 与 Qt6 qttranslations 6.11.1 先例的对照

| 维度 | qttranslations 6.11.1（Qt6） | qt5-qttranslations 5.15.2（本件） |
|---|---|---|
| 上游构建系统 | CMake（Qt6） | qmake TEMPLATE=aux（Qt5，无 CMake） |
| lrelease 来源 | qttools/6.11.1（同代） | qttools/6.11.1.1（Qt6，Qt5 qttools 缺件） |
| 转换入口 | `cmake --build --target updateqm` | 逐 .ts 直接调 lrelease |
| 产物落位 | translations/*.qm | translations/*.qm |
