# zeGrapher 3.1.1 适配笔记（OHOS aarch64）

## 上游测试清点（R51 三步法 · 第 1 步）

- 上游源码 v3.1.1 tarball：55 个 .cpp，**无 tests/ 目录**，ZeGrapher.pro
  **无 test target**（CONFIG 只含 c++11，无 test 相关配置）。
- 构建系统为 qmake（非 CMake/CTest），上游无任何自动化测试注册。
- 结论：上游测试用例数 = 0，无可运行的上游测试环境。test_package 提供
  R51 补全的冒烟测试（见下）。

## 构建方式

qmake 驱动（上游 ZeGrapher.pro，`QT += widgets printsupport network`），
直接调用 qt5-qtbase/5.15.2.2 包内 `bin/qmake`：

```
qmake -spec linux-clang-libc++ ZeGrapher.pro INCLUDEPATH+=<boost>/include CONFIG+=c++17
make -j2 && make install INSTALL_ROOT=<pkg>
```

- 依赖：qt5-qtbase/5.15.2.2（Core/Gui/Widgets/PrintSupport/Network，
  含 moc/uic/rcc/offscreen 插件）+ boost/1.90.0.4.1（头文件级使用：
  boost/math/special_functions/binomial.hpp、boost/multiprecision/cpp_dec_float.hpp）。
- CMakeDeps 不参与（qmake 走包内 mkspecs + qt.conf 自解析 Qt 库）。

## 踩坑记录

1. **QMAKESPEC 未定义**：qt5-qtbase 包内 `qmake -query QMAKESPEC` =
   `**Unknown**`，不显式传 `-spec` 报 "Could not read qmake configuration
   file .../mkspecs/qmake.conf"。OHOS 本机工具链为 clang+libc++，用
   包内自带的 `linux-clang-libc++` spec。
2. **CONFIG += c++11 → boost 1.90 头文件不兼容**：boost/math/tools/
   type_traits.hpp 使用 std::decay_t/enable_if_t（C++14+），c++11 下
   20+ 个编译错误。qmake 命令行 `CONFIG+=c++17` 覆盖（.pro 后写优先）。
3. **OHOS ELF 签名（§7 陷阱）**：未签名二进制运行 rc=126
   "Operation not permitted"。package() 内对 bin/* 自签名
   （binary-sign-tool sign -selfSign 1，SHA256withECDSA）。
4. **strip 残留 .codesign 段**：.pro 的 `QMAKE_LFLAGS_RELEASE=-s` +
   qmake install 步骤的 `strip -s` 在二进制里留下陈旧 .codesign 段，
   签名工具报 ".codesign section already exists / sign elf failed"。
   签名前先 `llvm-objcopy --remove-section .codesign`（同 boost 配方
   _sign_shared_libraries 的做法）。
5. **/tmp 只读（E002）**：探索性构建放 $HOME/tmp。

## test_package（鸿蒙特有测试，R51 第 3 步补全）

- T1: QT_QPA_PLATFORM=offscreen 启动 ZeGrapher（QApplication 主循环），
  timeout 5s 存活性断言（GUI 无 CLI 参数，崩溃/缺库/平台插件缺失 1s 内
  非 0 退出；存活到超时 rc=124 = 启动成功）。
- T2: 二进制为 aarch64 有效 ELF。
- 实测：conan create 全绿，T1/T2 ALL PASS（rc=124 符合预期）。

## 其他

- updatecheck.cpp 启动时会向 zegrapher.com 检查更新（纯客户端 HTTP，
  不影响构建，保持上游行为）。
- 安装产物：bin/ZeGrapher + share/applications/desktop + icons +
  share/ZeGrapher/locale（.qm 翻译）。
---

**编译结束**: 2026-10-06 12:01
**最终状态**: published
