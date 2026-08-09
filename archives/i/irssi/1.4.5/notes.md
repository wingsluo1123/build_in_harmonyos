# irssi 1.4.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-10
- 编译器: clang/clang++
- 状态: published (Conan适配)

## 编译步骤

1. `conan install` 安装依赖 (glib/2.84.0, openssl/3.5.6, ncurses/6.5)
2. 应用4个补丁 (config.guess, config.sub, irssi-config.h, configure mktemp fix)
3. `./configure --with-perl=no` (使用PkgConfigDeps + AutotoolsToolchain)
4. `make -j2`
5. `make install`
6. `make check` (test-796因平台限制失败，已知问题)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess不识别HarmonyOS | E007 | 0001补丁添加HarmonyOS检测 |
| 2 | config.sub拒绝linux-ohos | E007/E072 | 0002补丁添加linux-ohos到验证列表 |
| 3 | Perl模块编译失败 | HarmonyOS Perl不完整 | --with-perl=no |
| 4 | config.status Permission denied | mktemp -d创建目录带SGID位 | 0004补丁跳过mktemp用mkdir |
| 5 | glib版本检测失败(48.0.xxx) | glib/2.84.0.1四段版本号致sed解析错误 | 改用glib/2.84.0(三段版本) |
| 6 | 链接失败 -l:ld-musl-aarch64.so.1 | glib-2.0.pc含-L/lib但linker不跟随符号链接 | 添加-L/system/lib到LDFLAGS |
| 7 | libtool: cannot find //lib/libpcre2-8.la | pcre2/libffi .la文件libdir='//lib' | 修正.la文件libdir为实际路径 |
| 8 | ncurses setupterm未找到 | AC_CHECK_LIB不用pkg-config | conanfile.py添加ncurses flags到tc.extra_ldflags |
| 9 | test-796 getpwuid_r失败 | E051平台限制 | 已知限制，非irssi bug |

## 源码修改

| 补丁 | 文件 | 说明 |
|------|------|------|
| 0001 | build-aux/config.guess | 添加HarmonyOS平台检测 |
| 0002 | build-aux/config.sub | 添加linux-ohos到OS验证列表 |
| 0003 | irssi-config.h | 禁用utf8proc, static perl, term.h |
| 0004 | configure | 跳过mktemp用mkdir(HarmonyOS SGID限制) |

## 依赖版本

- glib 2.84.0 (Conan制品仓, shared)
- openssl 3.5.6 (Conan制品仓, static)
- ncurses 6.5 (Conan制品仓, static)

## 验证结果

```bash
$ irssi --version
irssi 1.4.5 (20231003 1405)
```

## 注意事项

- glib/2.84.0.1(四段版本号)会导致irssi configure sed解析失败，必须使用glib/2.84.0
- HarmonyOS mktemp -d创建的目录带SGID位，阻止后续写入，需patch configure
- conan pcre2/libffi的.la文件libdir可能为'//lib'，需修正后才能链接
---

**编译结束**: 2026-08-10 05:47
**最终状态**: built
