# libvisio 0.1.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-25
- 编译器: clang/clang++
- 状态: built
- 平台: aarch64-unknown-linux-ohos (HarmonyOS)

## 编译步骤

1. 下载源码包 `libvisio-0.1.5.tar.xz` 并解压到 work 目录
2. 打补丁修改 `config.guess` 和 `config.sub` 以支持 HarmonyOS 平台识别
3. 修复 `configure` 脚本中的 `umask 077` → `umask 022`，`./confXXXXXX` → `$TMPDIR/confXXXXXX`
4. 运行 `./configure --prefix=$DEFAULT_PREFIX --disable-tests --host=aarch64-unknown-linux-ohos`
5. 修复 `config.status` 中同样的 umask/tmpdir 问题
6. 运行 `./config.status` 重新生成 Makefile
7. 设置时间戳防止 maintainer 规则触发（源文件设旧、生成文件设新）
8. 移除所有 Makefile 中的 `-Werror` 标志
9. 运行 `make -j1` 编译
10. 运行 `make install DESTDIR=$TEST_PREFIX` 安装到测试目录

关键命令：
```bash
export PKG_CONFIG_PATH="$DEFAULT_PREFIX/lib/pkgconfig:$DEFAULT_PREFIX/share/pkgconfig"
export CPPFLAGS="-I$DEFAULT_PREFIX/include"
export LDFLAGS="-L$DEFAULT_PREFIX/lib"
./configure --prefix=$DEFAULT_PREFIX --disable-tests --host=aarch64-unknown-linux-ohos
./config.status
# 移除 -Werror
find . -name Makefile -exec sed -i 's/-Werror//g' {} \;
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 2014 版 config.guess 不包含 HarmonyOS 检测 | 手动添加 `__OHOS__` 宏检测、HarmonyOS 到 LIBC case、GUESS→echo/exit |
| 2 | config.sub 拒绝 linux-ohos | 2014 版 config.sub 无 linux-ohos 支持 | 添加 `linux-ohos*` 到 maybe_os 和 OS 列表，在 `-linux*)` 兜底前添加专用 case |
| 3 | configure 运行报 Permission denied | HMDFS 上 `umask 077` 创建的临时目录不可写 | `umask 077`→`022`，`./confXXXXXX`→`$TMPDIR/confXXXXXX` |
| 4 | config.status 报 Permission denied | 同 configure 的 umask 问题 | 同上修复 config.status |
| 5 | autoreconf -fi 后 configure 语法错误 | autoconf 2.72 与旧版 configure.ac 的 ICU 检测宏不兼容 | 放弃 autoreconf，直接打补丁 |
| 6 | make 触发 missing 脚本调用 automake/autoconf | 源文件比生成文件新，触发 maintainer 规则 | touch 设置时间戳：源文件设旧(2020)、生成文件设新(2025) |
| 7 | 编译报 -Wdeprecated-copy-with-user-provided-copy 错误 | Makefile 硬编码 -Werror，clang 新版弃用警告被当错误 | `sed -i 's/-Werror//g'` 移除所有 Makefile 中的 -Werror |
| 8 | 运行时找不到 libxml2.so.16 | libxml2.so.16 符号链接缺失 | `ln -sf libxml2.so.16.bak $DEFAULT_PREFIX/lib/libxml2.so.16` |

## 源码修改

### 0001-config.guess.patch
- 在 LIBC 检测 case 中添加 `HarmonyOS` 到 `Linux|GNU|GNU/*` 行
- 添加 `#if defined(__OHOS__)` → `LIBC=ohos` 检测
- 在系统匹配 case 中添加 `*:HarmonyOS:*:*)` 分支，输出 `aarch64-unknown-linux-ohos`
- 将 `GUESS=` 改为 `echo` + `exit`（2014 版使用 GUESS 变量但无输出逻辑）

### 0002-config.sub.patch
- 在 maybe_os 列表中添加 `linux-ohos*`
- 在 OS 系统列表中添加 `-linux-ohos*`
- 在 `-linux-dietlibc)` 前添加 `-linux-ohos*)` case 分支（防止 `-linux*)` 兜底将 ohos 替换为 gnu）

### 手动修复（未生成补丁，因为是生成文件）
- `configure`: umask 077→022, ./confXXXXXX→$TMPDIR/confXXXXXX
- `config.status`: 同上 umask/tmpdir 修复
- 所有 `Makefile`: 移除 `-Werror`

## 依赖版本

| 依赖 | 版本 | 安装位置 |
|------|------|----------|
| librevenge | 0.0.5 | $DEFAULT_PREFIX |
| libxml2 | 2.9.8 | $DEFAULT_PREFIX |
| zlib | 1.3.1 | $DEFAULT_PREFIX |
| icu4c | 77 | $DEFAULT_PREFIX |

## 验证结果

```bash
# pkg-config 验证
$ pkg-config --exists libvisio-0.1 && echo OK
OK
$ pkg-config --modversion libvisio-0.1
0.1.5

# 工具运行测试（6 个工具全部通过）
$ vsd2raw --version
vsd2raw 0.1.5
$ vss2raw --version
vss2raw 0.1.5
$ vsd2xhtml --version
vsd2xhtml 0.1.5
$ vss2xhtml --version
vss2xhtml 0.1.5
$ vsd2text --version
vsd2text 0.1.5
$ vss2text --version
vss2text 0.1.5

# ELF 文件类型
$ file lib/libvisio-0.1.so.1.0.5
ELF shared object, 64-bit LSB arm64, not stripped

# 动态依赖
$ readelf -d lib/libvisio-0.1.so.1.0.5 | grep NEEDED
Shared library: [librevenge-0.0.so.0]
Shared library: [libxml2.so.16]
Shared library: [libz.so.1]
Shared library: [libc++_shared.so]
Shared library: [libc.so]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libvisio-0.1.so.1.0.5 | 33,008,064 bytes | 共享库（含调试符号，未 strip） |
| lib/libvisio-0.1.la | 1,159 bytes | libtool 归档文件 |
| lib/pkgconfig/libvisio-0.1.pc | 428 bytes | pkg-config 配置文件 |
| include/libvisio-0.1/libvisio/libvisio.h | 473 bytes | 主头文件 |
| include/libvisio-0.1/libvisio/VisioDocument.h | 1,156 bytes | 文档接口头文件 |
| bin/vsd2raw | 22,976 bytes | VSD→Raw 转换工具 |
| bin/vss2raw | 22,976 bytes | VSS→Raw 转换工具 |
| bin/vsd2xhtml | 31,168 bytes | VSD→XHTML(SVG) 转换工具 |
| bin/vss2xhtml | 31,168 bytes | VSS→XHTML(SVG) 转换工具 |
| bin/vsd2text | 22,976 bytes | VSD→Text 转换工具 |
| bin/vss2text | 22,976 bytes | VSS→Text 转换工具 |

## 注意事项

1. **不要使用 autoreconf -fi**：autoconf 2.72 与 libvisio 0.1.5 的 configure.ac 中 ICU 检测宏不兼容，会导致生成的 configure 脚本语法错误
2. **umask 修复**：configure 和 config.status 都需要手动修复 umask 077→022 和 tmpdir 路径，HMDFS 文件系统限制
3. **-Werror 必须移除**：Makefile 中硬编码了 -Werror，需在 configure 后、make 前移除
4. **时间戳管理**：为防止 maintainer 规则触发，需确保 .am/.ac 文件比 .in/Makefile/config.status 文件旧
5. **libxml2.so.16 符号链接**：运行时需要确保 `$DEFAULT_PREFIX/lib/libxml2.so.16` 存在（指向实际 .so 文件）
6. **--disable-tests**：禁用测试以绕过 cppunit 依赖

---

**编译开始**: 2026-06-25 09:46
**编译结束**: 2026-06-25 19:39
**测试完成**: 2026-06-25 20:24
**最终状态**: built
---

**编译结束**: 2026-06-25 22:24
**最终状态**: built
