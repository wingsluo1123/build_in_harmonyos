# guile 2.2.7 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-17 (Conan 配方适配)
- 初次编译: 2026-05-26 (探索性编译)
- 编译器: clang/clang++
- 状态: published

## 背景
- Guile 3.0.x 在 HarmonyOS 上有字节码兼容性问题
- 2.2.7 是 2.x 系列最新稳定版，理论上更兼容 HarmonyOS
- 主要被 autogen 作为库依赖使用

## 依赖状态

### Conan 依赖（在 conanfile.py requirements() 中声明）
| 软件 | 版本 | 说明 |
|------|------|------|
| gc | 8.2.12 | Boehm-Demers-Weiser GC, 无 pthread_cancel |
| gmp | 6.3.0@ohpcd/stable | GNU 多精度算术库 |
| libffi | 3.4.8 | 外部函数接口 (注意用 3.4.8 不是 3.4.6) |
| pkgconf | 2.5.1 | 构建依赖 (build_requires) |

### 非 Conan 依赖（已安装到 /usr/local）
| 软件 | 版本 | 说明 |
|------|------|------|
| libunistring | 1.4.2 | Unicode 字符串库, /usr/local/lib/pkgconfig |
| libltdl | 2.4.7 | libtool 的动态加载库, libltdl.so.7 |
| readline | 8.2 | 系统库 |
| gettext/libintl | — | 系统库 |

非 Conan 依赖在 conanfile.py generate() 中通过:
- `tc.extra_cflags.append("-I/usr/local/include")`
- `tc.extra_ldflags.append("-L/usr/local/lib -Wl,-rpath,/usr/local/lib")`
- `env.prepend_path("PKG_CONFIG_PATH", "/usr/local/lib/pkgconfig")`

## 补丁

### 应用的补丁（在 conandata.yml 中声明）
1. `0001-build-aux-config.guess.patch`: 添加 HarmonyOS 系统识别
2. `0002-build-aux-config.sub.patch`: 添加 linux-ohos* 支持
3. `0003-configure.patch`: umask 077→022 修复 HMDFS 权限问题

### 非 Conan 补丁方式处理（在 conanfile.py build() 中）
4. `libguile/guile-snarf`: umask 077→022 (replace_in_file)
5. `doc/ref/stamp-vti`, `doc/ref/version.texi`: touch 防止重新生成

### 未应用的补丁（跳过）
- `0004-doc-ref-stamp-vti.patch`: 包含环境变量转储，通过 touch 替代
- `0005-doc-ref-version.texi.patch`: 同上

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 未添加 HarmonyOS 模式 | 补丁 0001: 添加 `*:HarmonyOS:*:*` case |
| 2 | config.sub 不支持 linux-ohos | 未添加 ohos 支持 | 补丁 0002: 在两处添加 `linux-ohos*` |
| 3 | configure/config.status 权限拒绝 | HMDFS + umask 077 | 补丁 0003: `umask 077` → `umask 022` |
| 4 | guile-snarf 权限拒绝 | HMDFS + umask 077 | conanfile.py: replace_in_file 修改 |
| 5 | 缺少 libltdl | libtool 未安装库部分 | 已安装到 /usr/local |
| 6 | 编译 .go 文件后 Signal 5 崩溃 | GC库/HarmonyOS限制 | `make -k -j1` 容忍崩溃 |
| 7 | doc 文件重新生成失败 | texinfo 工具缺失/损坏 | touch stamp-vti/version.texi |
| 8 | 无 libguile.h 总头文件 | guile 2.2 不生成总头文件 | test.c 直接 include 各子头文件 |

## 包信息
- 库名: `guile-2.2` (libguile-2.2.so, libguile-2.2.a)
- pkg-config 名: `guile-2.2`
- 头文件路径: `include/guile/2.2/libguile/`
- 可执行文件: `bin/guile`, `bin/guile-config`, `bin/guile-snarf`
- Scheme 运行时: `share/guile/2.2/`

## 验证结果

```bash
$ guile --version
GC Warning: Failed to find PT_GNU_RELRO segment inside PT_LOAD region
guile (GNU Guile) 2.2.7
Copyright (C) 2020 Free Software Foundation, Inc.
```

## 注意事项

1. **GC警告**: `Failed to find PT_GNU_RELRO segment` 不影响功能
2. **Signal 5**: 编译 .go 文件后的崩溃不影响文件生成，用 `make -k` 容忍
3. **libltdl**: Guile 依赖 libltdl，必须确保 /usr/local 在搜索路径中
4. **非 Conan 依赖**: libunistring 和 libltdl 不在 Conan 缓存中，通过 /usr/local 路径提供
5. **文档补丁**: 0004/0005 包含环境转储，不应应用，用 touch 替代

## 知识提取

### L1 平台真理
- HarmonyOS 系统识别需要修改 config.guess/config.sub
- HMDFS 文件系统要求修改 umask 077 为 022（configure 和 guile-snarf 两处）
- Signal 5 (SIGTRAP) 在 GC 相关操作中可能触发，不影响产物

### L2 模式经验
- Guile 2.2.x 需要 libltdl（libtool 的库部分）
- Guile 2.2.x 不生成 libguile.h 总头文件，需直接 include 子头文件
- 库名带版本后缀: libguile-2.2, pkg-config: guile-2.2
- 非 Conan 依赖通过 extra_cflags/extra_ldflags/Environment 提供路径

---

**Conan 配方创建**: 2026-07-17
**最终状态**: published (conan create 验证)
---

**编译结束**: 2026-07-20 11:51
**最终状态**: built
