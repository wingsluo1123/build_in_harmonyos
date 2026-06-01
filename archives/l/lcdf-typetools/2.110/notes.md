# lcdf-typetools 2.110 — 编译笔记

## 编译过程

### 问题1: kpathsea 依赖缺失
- **症状**: configure error: "I can't find the kpathsea library"
- **处理**: kpathsea 是可选的 TeX 库依赖，使用 `--without-kpathsea` 禁用
- **原因**: lcdf-typetools 无强依赖，kpathsea 为可选功能

### 问题2: HMDFS umask 077 导致 config.status 失败
- **症状**: `./config.status[774]: can't create ./confXXXXXX/subs1.awk: Permission denied`
- **根因**: HMDFS 文件系统上，`mktemp -d` 使用 `umask 077` 创建的 0700 权限目录，shell 脚本无法在其中创建文件
- **修复**: 从 configure 脚本中移除 `umask 077` 前缀（补丁 0001-configure.patch）
- **知识层**: L1 平台真理

### 问题3: GNU cat/sort 无法写入 stdout（管道）
- **症状**: `sort: stat failed: -: Permission denied` 和 `cat: standard output: Permission denied`
- **根因**: HMDFS 平台上 GNU coreutils 的 cat 和 sort 无法处理 stdin→stdout 管道操作
- **修复**: 创建 sort wrapper（写临时文件后排序）和 cat symlink（指向 toybox /bin/cat）
- **知识层**: L1 平台真理

## 编译配置

- configure 选项: `--prefix=$DEFAULT_PREFIX --without-kpathsea`
- 编译器: clang/clang++
- CFLAGS: -fPIC -O2
- make check: 无测试（PASS，无 test target）

---

**编译开始**: 2026-06-01
**编译结束**: 2026-06-01
**最终状态**: published
---

**编译结束**: 2026-06-01 12:24
**最终状态**: published
