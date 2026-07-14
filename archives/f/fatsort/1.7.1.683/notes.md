# fatsort 1.7.1.683 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-14
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

```bash
# 1. 初始化源码和归档
python3 $SKILL_ROOT/scripts/ohc-run.py init-build fatsort 1.7.1.683 \
  --url=https://downloads.sourceforge.net/sourceforge/fatsort/fatsort-1.7.1.683.tar.xz \
  --tar=tar.xz

# 2. 探索性编译
source .build-context-fatsort-1.7.1.683
cd $BUILD_SRC_DIR
make -C src -j1 CC=clang LD=clang CFLAGS="$CFLAGS -D__LINUX__" LDFLAGS="$LDFLAGS"

# 3. Staging 验证
mkdir -p "$TEST_PREFIX$DEFAULT_PREFIX/bin" "$TEST_PREFIX$DEFAULT_PREFIX/share/man/man1"
cp src/fatsort "$TEST_PREFIX$DEFAULT_PREFIX/bin/fatsort"
cp "$BUILD_SRC_ORIG_DIR/man/fatsort.1" "$TEST_PREFIX$DEFAULT_PREFIX/share/man/man1/fatsort.1"
"$TEST_PREFIX$DEFAULT_PREFIX/bin/fatsort" -v
"$TEST_PREFIX$DEFAULT_PREFIX/bin/fatsort" -h

# 4. 上游测试尝试（记录为平台/环境限制）
make -j1 tests SHELL=/data/service/hnp/bin/bash CC=clang LD=clang CFLAGS="$CFLAGS -D__LINUX__" LDFLAGS="$LDFLAGS"

# 5. Conan 配方验证
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify fatsort 1.7.1.683
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make install` 调用 `install` 失败 | HarmonyOS 当前 PATH 没有 GNU install；且上游顶层 install 依赖已存在的 `man/fatsort.1` | Conan package() 直接复制 `src/fatsort` 和上游 manpage，避免依赖系统 install 工具 |
| 2 | Conan G2 初次构建失败: `make: *** src: No such file or directory` | basic_layout 下 Conan build() 当前目录是 build-release，不是 source root | build() 中使用 `os.path.join(self.source_folder, "src")` 作为 make 工作目录 |
| 3 | SourceForge 下载超时 | `downloads.sourceforge.net` 被重定向到慢镜像，conan source() 下载超时 | conandata.yml 增加 Gentoo distfiles 权威镜像作为首选 URL，保留 SourceForge fallback |
| 4 | 上游 tests 大量失败 | 测试套件依赖 `/bin/bash`、bbe、valgrind、可写 `/tmp`、镜像解压/挂载等能力，当前 HarmonyOS 环境不完整 | 记录 `reports/upstream-tests.log`，阻塞质量验证改用 conan test_package 运行 `fatsort -v` 和 `fatsort -h` |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| 0001-Makefile.patch | 顶层 install 目标改用 mkdir/cp/chmod，避免依赖当前环境缺失的 GNU install |
| 0002-configure.patch | 为 Makefile-only 项目增加最小 configure shim，满足 clean-verify 的 configure 阶段 |
| 0003-src-Makefile.patch | 允许 CC/LD 被环境覆盖，默认安装到 bin，并避免 src install 目标依赖 GNU install |

## 依赖版本

无外部编译依赖；仅使用系统 clang/make/xz。

## 验证结果

```bash
# 探索编译
make -C src -j1 CC=clang LD=clang CFLAGS="$CFLAGS -D__LINUX__"
# 结果: PASS，生成 src/fatsort

# Staging smoke
fatsort -v
# 结果: fatsort 1.7.1

fatsort -h
# 结果: 帮助文本正常输出

# 上游测试尝试
make -j1 tests SHELL=/data/service/hnp/bin/bash ...
# 结果: FAIL（平台/环境限制，详见 reports/upstream-tests.log）

# conan-verify
G0: PASS  G1: PASS  G2: PASS  G3: PASS  G4: PASS
L2: PASS  L4: PASS  L5: PASS
Verdict: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/fatsort | 84,352 bytes | FAT/exFAT 目录排序命令行工具，ELF arm64 |
| share/man/man1/fatsort.1 | 2,935 bytes | manpage |

## 注意事项

1. 上游版本宏输出 `fatsort 1.7.1`，源码包文件名版本为 `1.7.1.683`。
2. 上游 tests 适合完整 Linux 用户态环境；当前 HarmonyOS 环境缺少部分工具和 `/tmp` 行为，未作为阻塞门禁。
3. 本包为纯命令行工具，已按 R38 在软件级目录新增 `commands.json`。
---

**编译结束**: 2026-07-14 23:32
**最终状态**: published
