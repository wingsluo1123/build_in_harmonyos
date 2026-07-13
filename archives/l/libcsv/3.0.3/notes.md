# libcsv 3.0.3 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-06-26
- 编译器: clang 15.0.4 (HarmonyOS SDK)
- 平台: aarch64-unknown-linux-ohos
- 状态: published

## 编译步骤

```bash
# 1. 下载源码
#    源码来自 https://github.com/rgamble/libcsv master 分支
#    (无 tag/release，使用 master 分支 tarball)

# 2. 平台兼容性修复
#    a) 替换 config.guess/config.sub 为 automake 1.17 (2023) 版本
#       原始版本 (2013) 无法识别 HarmonyOS
#    b) 修改 configure 脚本 umask 077 → umask 022
#       HMDFS 文件系统下 0700 权限目录无法写入

# 3. configure
./configure --prefix=$DEFAULT_PREFIX --disable-shared --enable-static

# 4. make
make -j1

# 5. make check (测试通过)
make check

# 6. make install
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报错无法识别平台 | config.guess (2013版) 不含 HarmonyOS 检测分支 | 替换为 automake 1.17 的 2023 版 config.guess/config.sub |
| 2 | mktemp -d 创建的临时目录无写入权限 | HMDFS 文件系统下 umask 077 创建 0700 目录无法写入 | configure 脚本中 umask 077 改为 umask 022 |
| 3 | Conan build() 方法找不到 configure 文件 | Conan 2.x basic_layout 下 build() 工作目录非源码目录 | 使用 os.path.join(self.source_folder, "configure") 代替相对路径 |
| 4 | GitHub 下载 URL 错误 | 任务指定 laamaa/libcsv，实际正确仓库为 rgamble/libcsv | 修正为 https://github.com/rgamble/libcsv/archive/refs/heads/master.tar.gz |

## 源码修改

共生成 16 个补丁文件，均为 autotools 自动生成文件的平台适配更新：

| 补丁 | 文件 | 说明 |
|------|------|------|
| 0001 | Makefile.in | autoreconf 重新生成 |
| 0002 | aclocal.m4 | autoreconf 重新生成 |
| 0003 | compile | automake 1.17 版本更新 |
| 0004 | config.guess | 2013→2023 版本，支持 HarmonyOS |
| 0005 | config.sub | 2013→2023 版本，支持 HarmonyOS |
| 0006 | configure | autoreconf 重新生成 + umask 077→022 |
| 0007 | depcomp | automake 1.17 版本更新 |
| 0008 | install-sh | automake 1.17 版本更新 |
| 0009 | ltmain.sh | libtool 版本更新 |
| 0010-0014 | m4/*.m4 | libtool 宏文件更新 |
| 0015 | missing | automake 1.17 版本更新 |
| 0016 | test-driver | automake 1.17 版本更新 |

**注意**: 这些补丁均为自动生成文件的平台适配更新，不修改任何源码逻辑 (R6)。

## 依赖版本

- 无外部依赖 (libcsv 是纯 ANSI C 库)
- 构建工具: automake 1.17, libtool 2.4.x
- Conan 引用: libcsv/3.0.3@ohpcd/stable

## 验证结果

### make check
```
PASS: check_csv
============================================================================
Testsuite summary for libcsv 3.0.3
============================================================================
# TOTAL: 1
# PASS:  1
# SKIP:  0
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0
============================================================================
```

### Conan test_package
```
1/1 Test #1: test_libcsv ......................   Passed    0.02 sec
100% tests passed, 0 tests failed out of 1
```

### conan-verify
8 道门禁全部通过 (G0/G1/G2/G3/G4/L2/L4/L5)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libcsv.a | 7648 字节 | 静态库 (手动构建) |
| libcsv.a | 7000 字节 | 静态库 (Conan 构建) |
| csv.h | 4411 字节 | 公共头文件 |
| csv.3 | 24253 字节 | man 手册页 |

## 注意事项

- libcsv 无 tag/release，使用 master 分支，版本号在 configure.ac 中确认为 3.0.3
- 许可证为 LGPL-2.1 (非 MIT)
- 静态链接模式 (R26: --disable-shared --enable-static)
- 补丁分类: 全部为 platform_only=True (仅平台适配，不影响功能)

---

**编译结束**: 2026-06-26 04:48
**最终状态**: published
