# apertium 3.9.12 适配笔记

## 编译环境
- 构建系统: autotools (configure.ac + Makefile.am + autogen.sh)
- 编译器: clang/clang++ 15.0.4
- 平台: OpenHarmony (OHOS) aarch64
- 编译日期: 2026-08-12
- 状态: built

## 软件说明
apertium 3.9.12 是 Apertium 机器翻译平台的核心引擎（finite-state transfer），提供 transfer / interchunk / postchunk / tagger / formatters / validators 等二进制工具，构建在 lttoolbox / libxml2 / ICU / utfcpp 之上。

## 构建步骤
1. 下载上游源码 apertium-v3.9.12.tar.gz（GitHub archive API，SHA256: 1a719e7338898f82891d3c4cbc1fb8bb4f575173df7b7313dd3802176ce234fe）
2. 应用 3 份补丁（0001 getopt_long OHOS sysroot compat、0002 tmx_builder inline PACKAGE_VERSION、0003 C++17 standard headers）
3. autoreconf -fi 生成 configure（release tarball 不含预生成 configure）
4. conan create 构建 apertium/3.9.12@ohpcd/stable，autotools configure + make -j1

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lua/5.3.0 依赖不可达 | 制品仓 ohpcd remote 无 apertium 依赖链 lttoolbox/icu4c/utf8cpp，ConanCenter 项目内被禁用 | 子任务为 lttoolbox 3.7.6 补写 Conan 配方并 conan create 发布到本地 cache（传递依赖 icu4c/77 + utf8cpp/4.1.1 也由 --build=missing 自动构建） |
| 2 | conandata.yml sources 用版本子键嵌套格式导致 get() unexpected keyword argument | Conan 2 的 get() 不接受嵌套字典 | 改用扁平 sources 格式（去掉 `"3.9.12"` 子键） |
| 3 | SHA256 不匹配 | git archive 生成的 tarball hash 与 GitHub archive API 官方 tarball hash 不同（元数据差异） | 改用 GitHub archive API 直拉官方 tarball，SHA256: 1a719e7338898f82891d3c4cbc1fb8bb4f575173df7b7313dd3802176ce234fe |
| 4 | apertium/apertium_config.h 文件未生成 | 源码树有 apertium_config.h.cmake_in（CMake 模板）但无 apertium_config.h.in（autotools 模板），configure.ac 用 AC_CONFIG_HEADER �后者 | build() 在 autoreconf 后手动从 cmake_in 模板生成 apertium_config.h.in（cmakedefine→undef、${VAR}→@VAR@） |
| 5 | getopt() 声明冲突 | apertium 的 getopt_long.h 在 HAVE_DECL_GETOPT=0 时声明 `extern int getopt()`（无参），与 OHOS sysroot unistd.h 的 `int getopt(int, char *const[], const char*)` 冲突 | 补丁 0001 在 getopt_long.h 的守卫加 `&& !defined (__OHOS__) && !defined (__ohos__)`，跳过冲突声明 |
| 6 | tmx_builder.cc:419 PACKAGE_VERSION 未声明 | tmx_builder.cc 用 PACKAGE_VERSION 宏但不 include apertium_config.h，手动生成的 config.h 在 build folder 找不到 | 补丁 0002 直接把 PACKAGE_VERSION 替换为字面字符串 "3.9.12" |
| 7 | xsltproc/flex 找不到 deformat.xsl / *.l 数据文件 | Conan basic_layout 把 source 和 build folder 分离，但 Makefile 的 xsltproc/flex 命令期望数据文件就在当前工作目录 | build() 在 configure 后用 glob 复制 *.xsl / *-format*.xml / *.l / *.sh / README-MODES / apertium.m4 从 source folder 到 build folder |
| 8 | experimental/string_view file not found | apertium 的 string_view.h / filesystem.h 用 C++17 之前的过渡头 <experimental/string_view>，但 clang 15 + libc++ 已移除 | 补丁 0003 在 string_view.h / filesystem.h 加 #define HAVE_STRING_VIEW 1 / HAVE_FILESYSTEM 1，走 C++17 标准 <string_view> / <filesystem> 分支 |
| 9 | test_package build 链接报 undefined symbol: u_fprintf_77 | lttoolbox 的 ustring.o 引用 ICU 77 的版本化符号 u_fprintf_77（在 libicuio.a），但 icu4c Conan 包的 cpp_info.libs 漏了 icuio+icutu | test_package CMakeLists.txt 用 find_library 显式链 libicuio.a / libicutu.a / libicui18n.a / libicuuc.a / libicudata.a（conanfile generate() 写 icu4c_lib.txt 传库目录路径） |
| 10 | test_package build 报 utf8.h file not found | lttoolbox 的 ustring.h 用 `#include <utf8.h>`（裸头名），但 utf8cpp 的头在 include/utf8cpp/ 子目录 | test_package conanfile generate() 写 utf8cpp_inc.txt 传 include/utf8cpp/ 路径，CMakeLists.txt 读后显式加 include 目录 |
| 11 | test_package 编译报 use of undeclared identifier 'lttoolbox' | to_ustring() 在 ustring.h 的全局命名空间（非 lttoolbox::） | apertium_probe.cpp 去掉 lttoolbox:: 前缀，用裸 to_ustring() |
| 12 | test_package 运行时 FAIL: a(Analysis) construction | a::a(const Analysis&) 的真实语义是 TheTags = morphemes[0].TheTags、TheMorphemes = morphemes[1..end]（跳过第一个 Morpheme），测试只喂 1 个 Morpheme 导致 TheMorphemes 为空 | apertium_probe.cpp 改为喂 2 个 Morpheme（各带非空 TheTags），验证 a::TheTags 和 a::TheMorphemes 的正确传播 |

## 源码修改
- `apertium/getopt_long.h`：守卫加 `&& !defined (__OHOS__) && !defined (__ohos__)` 跳过冲突 getopt 声明（补丁 0001）
- `apertium/tmx_builder.cc`：PACKAGE_VERSION 替换为字面字符串 "3.9.12"（补丁 0002）
- `apertium/string_view.h` / `apertium/filesystem.h`：加 #define HAVE_STRING_VIEW 1 / HAVE_FILESYSTEM 1 走 C++17 标准头分支（补丁 0003）

## 依赖版本
- lttoolbox/3.7.6（制品仓本地 cache，子任务补写 Conan 配方）
- libxml2/2.15.3.1（制品仓已有）
- icu4c/77（制品仓本地 cache，lttoolbox 子任务传递依赖）
- utf8cpp/4.1.1（制品仓本地 cache，lttoolbox 子任务传递依赖）

## 验证结果
```bash
conan create archives/a/apertium/3.9.12 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# 结果: test package PASS
#   1/1 Test #1: apertium_probe ... Passed 0.17 sec
#   100% tests passed, 0 tests failed out of 1
```

## 上游测试说明
apertium 3.9.12 上游有 Python unittest 套件（tests/run_tests.py 调 transfer/cleanstream/tagger/interchunk/postchunk 等二进制），但 OHOS 设备无 Python 运行时无法跑。test_package 用 C++ 嵌入 libapertium 调用真实 API（Morpheme/Analysis/a/i 类）验证 5 个断言：Analysis morpheme propagation、a(Analysis) TheTags/TheMorphemes propagation、i(Morpheme) tag propagation、a operator==。
---

**编译结束**: 2026-08-12 14:52
**最终状态**: built
