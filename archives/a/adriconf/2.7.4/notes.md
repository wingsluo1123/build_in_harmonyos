# adriconf 2.7.4 适配笔记

## 编译环境
- 构建系统: cmake（GTK4 GUI 应用，C++17，clang 15 / libc++）
- 编译日期: 2026-10-10
- 编译器: clang/clang++ 15.0.4（OHOS aarch64，conan profile ohos-aarch64）
- 状态: built（本地 conan create + W3 门禁通过）

## 编译步骤

1. `ohc-run.py init-build adriconf 2.7.4`：初始化归档 + 源码（官方 gitlab.freedesktop.org/mesa/adriconf tag v.2.7.4）
2. `ohc-run.py conan-init` 后重写为 CMake 配方（conan-init 默认 autotools 模板，实际是 CMake）
3. `ohc-run.py conan-verify`：G0/G1/G2(conan create)/G3/G4 全 PASS
4. `ohc-run.py finish published`：W3 本地 CI 模拟通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码在 GitHub jlHertel/adriconf 最高 v1.6.1，无 2.7.4 | 2.7.4 已迁移到 gitlab.freedesktop.org/mesa/adriconf | conandata 指向 gitlab 官方归档（R39），sha256 实测校验 |
| 2 | expat 版本冲突（2.8.2.1 vs 2.8.2.1.1） | fontconfig 链与 mesa 链解析不同 expat | 配方 override 统一到 expat/2.8.2.1.1 |
| 3 | CMake find_package(OpenGL REQUIRED) 失败 | OHOS 无桌面 GL/GLX | 显式把 OpenGL 库/头指向 mesa 包 libOSMesa.so + include（coin3d 先例） |
| 4 | msgmerge/msgfmt 运行报 libintl 符号缺失 | CMake 命中 /usr/local 系统 gettext（旧共享库缺符号） | 生成 shim 脚本：LD_LIBRARY_PATH 前置 conan gettext lib 再 exec |
| 5 | glib-compile-resources 报 Operation not permitted (126) | glib 包 bin 工具 .codesign 过期（OHOS XPM 拒绝） | 按 gtk4 R85/R86 就地重签名 + PATH/LD_LIBRARY_PATH 前置 glib |
| 6 | 链接期 pkg_check_modules 库找不到 | LIBRARY_DIRS 未进链接路径（conan 缓存不在默认路径） | 补丁：link_directories 汇总各模块 LIBRARY_DIRS |
| 7 | FlowBox::append() 不存在 | gtkmm 4.0.0.1 是旧 API | 补丁：改 insert(widget, -1)（语义等价） |
| 8 | gdkmm-4.0.pc 幽灵依赖导致 -lgdkmm-4.0 找不到 | ohpcd gtkmm 包把 gdkmm 符号合并进 libgtkmm-4.0.so，但 .pc 仍声明独立 gdkmm 组件 | generate() 修补 gtkmm-4.0.pc 移除 Requires 中的 gdkmm-4.0 |
| 9 | g_libintl_* 符号未定义 | libglib-2.0.so 以 UND 引用 proxy-libintl 符号，glib-2.0.pc 未引用 libintl | 传 ADRICONF_GLIB_INTL 全路径，补丁 target_link_libraries 链接 glib 包 libintl.so |
| 10 | libgtk-4.so 引用 pango 符号，--no-allow-shlib-undefined 报错 | 依赖链共享库运行时解析 | CMAKE_EXE_LINKER_FLAGS 加 -Wl,--allow-shlib-undefined（aghermann 先例） |

## 源码修改（patches/ 3 个，均为 portability，无平台宏）

1. `0001-CMakeLists.txt.patch` — link_directories 汇总 pkg_check_modules LIBRARY_DIRS（OHOS conan 缓存库不在默认搜索路径）
2. `0002-adriconf-CMakeLists.txt.patch` — 链接 glib 包内 libintl.so 解析 g_libintl_* 符号（ADRICONF_GLIB_INTL）
3. `0003-adriconf-GUI.cpp.patch` — FlowBox::append → insert(widget, -1)（gtkmm 4.0.0.1 API 差异）

## 依赖版本（全部 ohpcd 制品仓预编译）

gtkmm/4.0.0.1（gtk4/4.22.4、glibmm/2.68.2、cairomm/1.18.0、pangomm/2.50.1、gdk-pixbuf/2.44.6）、libdrm/2.4.133、mesa/24.3.4.1.1（gbm/egl）、pciutils/3.13.0、pugixml/1.16、gettext/0.22.5.1、gtest/1.17.0.2、glib/2.84.0.1.1（override 统一图）

## 验证结果（R51 上游测试三步法）

- 上游测试清点：tests/ 10 个 gtest 源文件，15 个 test suite，64 个用例，断言 202 个（EXPECT_ 183 + ASSERT_ 19）
- 上游测试命令：`cmake --build <build> --target runUnitTests && ./runUnitTests`
- 实测运行（OHOS aarch64 设备环境）：**64/64 PASSED（100%）**，2 ms 完成，无失败用例
- test_package（R34 实质验证）：bin/adriconf ELF 校验 + --help 输出可读

```bash
$ ./runUnitTests --gtest_brief=1
[==========] 64 tests from 15 test suites ran. (2 ms total)
[  PASSED  ] 64 tests.
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/a/adriconf/2.7.4/conanfile.py | CMake 配方（application） |
| archives/a/adriconf/2.7.4/conandata.yml | 官方 gitlab 源 + sha256 |
| archives/a/adriconf/2.7.4/patches/0001-0003 | 3 个 portability 补丁 |
| archives/a/adriconf/2.7.4/test_package/ | R34 实质测试（ELF + --help） |
| archives/a/adriconf/commands.json | R38 CLI 工具声明 |

## 注意事项

- 上游 GUI 依赖显示环境（Wayland/X11 + Mesa drirc），OHOS 上仅验证编译、链接与二进制可执行性；GUI 运行需鸿蒙图形栈就绪后实测（R40 说明）
- gtkmm/4.0.0.1 制品包把 gdkmm 符号合并进 libgtkmm-4.0.so，任何消费者都需在配方里处理 gdkmm-4.0.pc 幽灵依赖（本配方已处理，见问题 #8）
---

**编译结束**: 2026-10-11 10:17
**最终状态**: built
