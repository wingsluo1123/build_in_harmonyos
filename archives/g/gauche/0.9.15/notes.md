# Gauche 0.9.15 编译笔记

## 编译状态
built (Conan 配方验证全门禁通过 G0-G4+L2/L4/L5)

## 编译日期
2026-05-27（探索编译）/ 2026-08-09（Conan 配方适配完成）

## 平台
aarch64-unknown-linux-ohos

## 遇到的问题

### 1. E007: config.guess 无法识别 HarmonyOS
- **症状**: `configure: error: cannot guess build type`
- **根因**: GNU config.guess 不包含 HarmonyOS/__OHOS__ 检测分支
- **解决方案**: 修改 config.guess 和 config.sub，添加 OHOS 支持
- **补丁**: 0013-config.guess.patch, 0014-config.sub.patch, 0030-gc-config.guess.patch, 0031-gc-config.sub.patch

### 2. config.status 临时目录创建失败
- **症状**: `can't create ./confXXXXXX/subs1.awk: Permission denied`
- **根因**: HMDFS 文件系统对临时目录创建有特殊限制，umask 077 导致权限问题
- **解决方案**: 修改 configure 中 umask 077→002（补丁 0042/0043）

### 3. pthread_cancel 和 pthread_setcancelstate 缺失
- **症状**: `undefined reference to pthread_cancel, pthread_setcancelstate`
- **根因**: HarmonyOS musl libc 不实现 pthread 线程取消功能
- **解决方案**: GC 补丁 0033/0034 禁用 pthread_cancel 相关宏（GC_NO_PTHREAD_CANCEL）

### 4. GC Warning: PT_GNU_RELRO segment
- **症状**: Boehm GC 警告 `Failed to find PT_GNU_RELRO segment inside PT_LOAD region`
- **根因**: HarmonyOS ELF 文件结构与传统 Linux 不同
- **解决方案**: 可忽略，不影响功能

## Conan 配方关键决策

### 动态构建（非 --disable-shared）
Gauche 的内嵌 Boehm GC 需要生成 `libgc_pic.a`（PIC 归档）供 libgauche 链接。
`--disable-shared` 会使 `libgc_pic.a` 为空，导致 GC_* 符号未定义。
因此 `generate()` 中不加 `--disable-shared`，保持默认动态构建。

### ext/doc/static 跳过（补丁 0002/0044/0046）
- **ext 跳过**: ext 目录扩展模块依赖动态链接，OHOS 上编译失败。
  补丁 0002 修改 Makefile.in 的 SUBDIRS 跳过 ext。
- **doc 跳过**: doc 目录需要构建 gosh 后生成 man page，跳过以简化构建。
  补丁 0002 中和 install-doc 目标。
- **static 跳过**: 静态库构建依赖 ext（需要 gauche.uvector 等），跳过。
  补丁 0046 从 src/Makefile.in 的 INSTALL_LIBS 中移除 libgauche-static-0.98.a。
- **pre-package check 跳过**: 补丁 0044 跳过 make install 前的版本检查
  （BUILD_GOSH 在干净构建中不可用）。

### copy-port 替换（补丁 0045）
ext 目录跳过后，`util.scm` 的 `do-copy` 依赖 `gauche.uvector`（来自跳过的 ext）。
补丁 0045 将 `do-copy` 改为字符级拷贝，绕过 `make-u8vector` 依赖。

### package_info 头文件路径
Gauche 的头文件安装在 `lib/gauche-0.98/0.9.15/include/`（autotools
GAUCHE_HEADER_INSTALL_DIR），而非顶层 `include/`。
`package_info()` 中 `cpp_info.includedirs` 指向该嵌套路径。

### test_package require traits（关键修复）
Conan 2.29 的 test_package 阶段，`requires` 默认 `headers=False, libs=False`
（假设 test_package 只运行测试二进制文件，不编译新的二进制文件）。
这导致 CMakeDeps 清空 `INCLUDE_DIRS` 和 `LIBS`，test_package 编译失败
（`'gauche.h' file not found`）。
**修复**: test_package 的 `requirements()` 中显式声明
`self.requires(self.tested_reference_str, headers=True, libs=True)`。

## 验证结果
- conan create 成功 ✓
- test_package (test_gauche) 通过 ✓
- `gosh -e "(display (gauche-version))(newline)"` → `0.9.15` ✓
- `gosh -e "(display (+ 1 2 3))(newline)"` → `6` ✓
- gosh 需 `LD_LIBRARY_PATH` 运行（RPATH 指向 `//lib/...`，prefix=/ 导致）

## 知识提取
1. HarmonyOS 不支持 pthread_cancel 等线程取消功能
2. HMDFS 文件系统对临时目录创建有特殊限制（umask 077→002）
3. Gauche 的扩展模块依赖动态链接，OHOS 上需跳过 ext 目录
4. **R6 铁律遵守**: 删除生成文件补丁（2026-05-28）
5. Conan 2.29 test_package require traits 默认 headers=False/libs=False，
   编译型 test_package 需显式 headers=True, libs=True

---

## 补丁清理记录 (R6 铁律遵守)

**删除的生成文件补丁（16 个）**：
- 0001: .patch-ai-review.txt（AI 判断文件）
- 0015-0019: doc/*.1（man page，编译生成）
- 0023-0029: ext/gauche/*.sci（Scheme 编译产物）
- 0036: src/features.flags（configure 生成）
- 0042-0043: src/gauche-config_threads.h, gauche-priv-configP.h（configure 生成）

**保留的源文件补丁（27 个）**：
- 核心源文件修改（config.guess, config.sub, gc_priv.h 等）
- Makefile.in（跳过 ext 目录）
- C 源文件（.c, .h）
- Scheme 源文件（.scm）
- 脚本文件（gauche-cesconv, gauche-install, gauche-package, genconfig, makeverslink）

---

**Conan 配方验证完成**: 2026-08-09
**最终状态**: built (全门禁通过 G0-G4+L2/L4/L5)
---

**编译结束**: 2026-08-11 14:25
**最终状态**: published
