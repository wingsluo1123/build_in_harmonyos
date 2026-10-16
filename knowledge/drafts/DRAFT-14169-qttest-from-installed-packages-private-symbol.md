# draft-14169-qttest-from-installed-packages-private-symbol

## 背景

同 rule4 场景（见 DRAFT-14168-qttest-static-plugin-real-execution 的"真实执行"立场），
但 qtconnectivity 是 **22 个 tst 目标、205 个测试函数**的套件，且被测模块
（QtBluetooth/QtNfc）以 conan 安装包形态存在——需要一个可批量、可复现的执行法。

## 方法：脚本生成统一 CMake 工程 + 安装包环境批量执行

1. **生成器**（Python）：逐目录解析上游 `tests/auto/<dir>/CMakeLists.txt` 的
   `qt_internal_add_test(...)` 块（括号平衡扫描取参，SOURCES/LIBRARIES/DEFINES
   逐字段提取），生成**一个 CMakeLists 包含全部 22 个 `add_executable`**：
   - `Qt::Foo` / `Qt::FooPrivate` 一律映射到公共目标 `Qt6::Foo`（私有模块在
     安装包里 header-only，符号在公共 .so 里）；
   - include 直取**源码包**路径（conan 缓存 `/p/<pkg>/s`），相对 `../nfccommons/`
     的共享源码按相对路径展开；
   - 私有头根统一注入（模块级 + 版本化父目录两级，见 qtsensors 草稿判据）。
2. **configure 关键差异**（对比 qtsensors 单目标）：依赖里出现 Widgets/Gui →
   qtbase 是开 EGL 构建的，`Qt6GuiConfig` 会 `find_package(EGL/GLESv2)`——手动
   configure 必须喂 SDK sysroot 路径，否则 `Qt6_FOUND=FALSE`：
   ```
   -DEGL_INCLUDE_DIR=<sdk>/sysroot/usr/include
   -DEGL_LIBRARY=<sdk>/sysroot/usr/lib/aarch64-linux-ohos/libEGL.so
   -DGLESv2_INCLUDE_DIR=… -DGLESv2_LIBRARY=…
   ```
3. **批量执行**：逐目标 `timeout 60 ./tst_* -o results/<t>.txt,txt`，环境
   `LD_LIBRARY_PATH=<qtbase>/lib:<qtconn>/lib` + `QT_QPA_PLATFORM=offscreen`；
   汇总从 per-target txt 的 `^Totals:` 行统计（终端回显会被日志截断，别从 log 统计）。

实测（2026-10-14）：22/22 目标全部真实执行，**passed=340 failed=8 skipped=48**。

## NFC 三目标：安装库隐藏私有符号的补链

`tst_qnearfieldmanager`/`tst_qnearfieldtagtype1/2` 链接报
`undefined symbol: QNearField{Manager,Target}Private::qt_metacall/staticMetaObject/…`：

- **取证**：`llvm-nm -C libQt6Nfc.so`——动态符号表无这些符号，但 `.symtab` 里有
  （local `t`/`d`）＝按 ELF 可见性隐藏，不是没编；
- **不可行**：`objcopy --globalize-symbol` 只改 `.symtab`，改不了 `.dynsym`；
  单独 moc 私有头生成 metacode 静态编入 → 与库内隐藏符号冲突形态不定，且虚分派器
  （`uid()/accessMethods()/disconnect()`）的实现体在私有实现 TU 里，单 moc 补不齐；
- **可行**：把模块的**私有实现源文件**编进测试本体：
  ```
  src/nfc/qnearfieldtarget.cpp + qnearfieldtarget_p.cpp   # target 三目标都要
  src/nfc/qnearfieldmanager.cpp                            # 仅 manager
  ```
  两个关键认知：① 实现体在 `*_p.cpp`（不是 `*.cpp`）；② 这些 cpp 尾部自带
  `#include "moc_…_p.cpp"`，**AUTOMOC 会从其包含的私有头自动生成私有 metacode**——
  不要再手挂 moc 文件（手挂必 duplicate symbol，两种形态的重复都踩过）；
- **上游语义对齐**：树内构建时测试就是这么链的（链 build-tree 对象），安装包只是
  隐藏了符号；把同一批源码编进测试本体＝等价静态链接语义。

## 失败的归类（真实执行的产出物）

8 failed = 7 个 NFC 仿真器 `targetDetected` 信号未触发（单用例 30s 超时特征，
nfccommons 仿真器的目标检测线程未按期投递）+ 1 个 `tst_writeByteArray`
（上游注释自述断言 BlueZ 后端的 debug dump 实现，dummy 后端输出为空）。
48 skipped 均为上游自身 QSKIP（无适配器按设计跳过）。**失败≠没测**——逐分类落账
进 MANIFEST，比"0 执行+全量豁免"在评审侧强得多。

## 判据小结

| 现象 | 结论 |
|---|---|
| 多目标上游套件要真实执行 | 生成器解析 qt_internal_add_test 块→统一 CMakeLists，别手写 22 份 |
| configure 报 `Failed to find required Qt component "Gui"` 但 config 文件在 | Qt6GuiConfig 的 find_dependency(EGL/GLESv2) 失败：喂 SDK sysroot 的 `-DEGL_LIBRARY/-DGLESv2_LIBRARY` |
| 链接 `undefined symbol: <Private>::qt_metacall/…` 且 `nm -C` 在 .symtab 可见 | 库按可见性隐藏了私有符号；把私有实现 `*.cpp + *_p.cpp` 编进测试本体 |
| 补链后 `duplicate symbol: <Private>::…` | 实现 cpp 尾部自带 `#include "moc_…"` 且 AUTOMOC 自动生成私有 metacode——删掉手挂的 moc 文件 |
| 私有实现符号仍缺 | 实现体在 `*_p.cpp`，别只挂 `*.cpp` |
| 汇总数字与终端输出对不上 | 从 `-o x.txt,txt` 的 `^Totals:` 统计，终端回显会被截断 |
