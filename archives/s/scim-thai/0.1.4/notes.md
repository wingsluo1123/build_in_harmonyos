# scim-thai 0.1.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-10-16
- 编译器: clang/clang++（aarch64-unknown-linux-ohos）
- 状态: built（编译时状态；最终状态为 published）

## 编译步骤

1. **版本核实**: 上游 tlwg/scim-thai v0.1.4（peeled commit 2d719751b89d0c53da9613a690b9342b10e16a69）存在，按指定版本适配，无版本替换。
2. **依赖检查（W0）**: scim/1.4.18-git20211204 ✅、libthai/0.1.29 ✅、libdatrie/0.2.13（libthai 传递）✅ 均已发布。
3. **autogen**: git 快照无 configure，执行 autogen.sh（libtoolize + autopoint + aclocal + autoheader + automake + autoconf）；需补 m4/pkg.m4（PKG_CHECK_MODULES）；gettext 宏链与 config.rpath 由重定位后的 autopoint 自动生成。
4. **configure**: 注入 scim/libthai/datrie 的 PKG_CONFIG_PATH；--enable-shared --disable-static（IMEngine 必须 dlopen）；--build/--host=aarch64-linux；AS_TMPDIR umask 002 覆盖解决 HMDFS config.status 权限。
5. **make -j1**: 产出 src/thai.so（2.3MB），2 个非致命警告（-Wmismatched-new-delete 等）。
6. **make check**: 上游无 TESTS 注册（src/data/po 均 Nothing to be done for 'check'）。
7. **conan-verify**: G1/G0/G2/G3/G4 + L2/L4/L5 全部 PASS。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PKG_CHECK_MODULES 未展开，configure 语法错误 | 上游 git 快照缺 m4/pkg.m4 | 配方 export_sources 提供 m4/pkg.m4（E089 复用） |
| 2 | CI: `autopoint: can't open //share/gettext/archive.dir.tar.xz` → `po/Makefile.in.in` 缺失 → configure 失败 | conan gettext 包的 autopoint 脚本 `prefix="/"` 写死（重定位缺失），gettext_datadir 误解析为 `//share/gettext` | 生成 `prefix=<gettext包目录>` 的 autopoint 副本并置于 PATH 前；gettext 宏链与 config.rpath 由其自动生成 |
| 3 | config.status: can't create ./confXXX/subs1.awk Permission denied | HMDFS AS_TMPDIR umask 077 临时目录不可写 | configure.ac m4_define 覆盖 AS_TMPDIR 为 umask 002（E052/E060 复用） |
| 4 | aclocal @am_AUTOM4TE@ 不可用 | 本地 automake 1.17 脚本占位符未替换 | 配方 tool_requires automake/1.18 + PERL/PERL5LIB 修正（E155 复用） |
| 5 | configure 找不到 libthai 的 datrie-0.2 | libthai.pc Requires.private datrie-0.2 | 注入 libdatrie pkgconfig 路径 |
| 6 | libtool: '//lib/libltdl.la' is not a valid libtool archive | scim 依赖包 libscim-1.0.la 内嵌无效绝对依赖 | build() 前修正依赖包 .la（移除 //lib/libltdl.la） |
| 7 | test_package 找不到 thai.so（仅 thai.a） | 模板默认 shared=False 强制 --disable-shared，dlopen 模块不可用 | 强制 --enable-shared --disable-static |
| 8 | ginstall 截断 thai.so（2.3MB→1.4MB，ELF 损坏） | HMDFS 复制大文件 Permission denied | package() 用 conan copy 重复制完整产物 |
| 9 | dlopen thai.so Permission denied | 安装产物被 ginstall 截断损坏 | 同 #8，复制完整产物后解决 |

## 源码修改

- `patches/0001-configure.ac.patch`: AS_TMPDIR umask 002 覆盖（HMDFS config.status 权限）。

## 依赖版本

- scim/1.4.18-git20211204（SCIM 框架，提供 scim.pc）
- libthai/0.1.29（泰语支持库）
- libdatrie/0.2.13（libthai 传递依赖，datrie-0.2.pc）
- 工具链: autoconf/2.72、automake/1.18、libtool/2.5.4、gettext/0.22.5.1

## 验证结果

```bash
# 手动编译（Step 2）
sh autogen.sh && ./configure --enable-shared --disable-static && make -j1 && make check
# → configure ✅ make ✅（thai.so 2.3MB）make check ✅（无上游 TESTS）

# Conan 验证
ohc-run.py conan-verify scim-thai 0.1.4
# → G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS

# test_package 消费者测试
./test_probe <thai.so>
# → scim-thai module OK: thai_LTX_scim_imengine_module_create_factory -> 0x...
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/s/scim-thai/0.1.4/conanfile.py | 完整配方（bootstrap + shared 模块 + .la 修正 + package copy） |
| archives/s/scim-thai/0.1.4/conandata.yml | 源码 sha256 + 补丁声明 |
| archives/s/scim-thai/0.1.4/m4/pkg.m4 | PKG_CHECK_MODULES 宏（export_sources，供 aclocal 展开） |
| archives/s/scim-thai/0.1.4/patches/0001-configure.ac.patch | AS_TMPDIR umask 002 |
| archives/s/scim-thai/0.1.4/test_package/ | dlopen 消费者测试（test.cpp + conanfile.py + MANIFEST.yml） |

## 注意事项

- scim-thai 是 SCIM 的 IMEngine 模块（thai.so），非普通链接库；消费者（SCIM 框架）运行时 dlopen 加载，因此必须构建为 shared 模块。
- scim 依赖包 libscim-1.0.la 存在内嵌无效绝对依赖（//lib/libltdl.la）的遗留缺陷，下游链接需规避；此缺陷应在 scim 依赖项后续版本修复。
- test_package 采用 dlopen 方式验证模块可加载（绕开 conan 子进程 HNP cmake 缺 libc++_shared.so 问题，同 scim/libthai 先例）。
---

**编译结束**: 2026-10-17 14:28
**最终状态**: published
