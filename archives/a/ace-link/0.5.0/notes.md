# ace-link 0.5.0 — 适配笔记

## 软件信息

- **名称**: ace-link
- **版本**: 0.5.0
- **描述**: GNU Emacs package for selecting a link to jump to
- **许可证**: GPL-3.0-or-later
- **源码**: https://github.com/abo-abo/ace-link/archive/refs/heads/master.tar.gz
- **SHA256**: dd73fa543cea0187d7544d3eaf767504f618d53864e36ddd8fe7208cb10418f6
- **构建系统**: Makefile (Emacs Lisp byte-compilation)

## 构建特征

ace-link 是一个纯 Emacs Lisp 包，类似 cask。它不需要 C/C++ 编译：
- `ace-link.el` — 主源文件，约 1100 行 Emacs Lisp 代码
- `Makefile` — 仅用于 Emacs byte-compilation (`emacs -batch -l test/make-compile.el`)
- `test/` — 测试目录
- 依赖: `emacs`, `avy` (Emacs Lisp 包, 版本 >= 0.4.0)

安装方式：将 `.el` 文件复制到 Emacs site-lisp 目录即可。

## 适配过程

### 下载
- 从 GitHub 下载 master.tar.gz
- SHA256 校验: dd73fa543cea0187d7544d3eaf767504f618d53864e36ddd8fe7208cb10418f6

### 安装
- 纯 Emacs Lisp 包，无需 C/C++ 编译
- `build()`: 无操作（无需编译）
- `package()`: 复制 `*.el` 文件到 `lib/site-lisp/` 目录
- 使用 DESTDIR 隔离安装，不污染系统目录

### 依赖
- 运行时依赖: `emacs` (Emacs 编辑器), `avy` (Emacs Lisp 包)
- `requirements()` 中暂未声明（emacs/avy 为运行时依赖，非 Conan 构建依赖）
- emacs 本身尚未完成 OHOS 适配，现仅通过 manifest.yaml 文档记录依赖关系
- 待 emacs 完成 OHOS 适配后，可在 `requirements()` 中补充: `emacs/29.4`, `avy/0.5.0`

### 测试
- test_package: 验证 ace-link.el 文件存在于安装目录
- 纯 Elisp 包，无法在无 Emacs 环境的 CI 中运行自动化测试
- test_results: skipped

## 无补丁

ace-link 是纯 Emacs Lisp 项目，无需源码修改。

## 关键决策

1. **conanfile.py 基于 makefile 模板**：虽然构建系统是 Makefile，但实际只需复制 .el 文件，无编译步骤
2. **R32 兼容**：`settings.os` 用 `in ("Linux", "OHOS")` 判断
3. **test_package 简化**：不使用 CMake，直接用 Python 检查文件存在性
4. **cpp_info**：设置 `includedirs = ["lib/site-lisp"]` 以便其他 Elisp 包引用

---

**适配日期**: 2026-07-14
**最终状态**: built
