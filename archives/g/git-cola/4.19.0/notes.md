# git-cola 4.19.0 适配笔记

## 编译环境
- 构建系统: makefile + pip (Python setuptools)
- 编译日期: 2026-07-16
- 编译器: N/A (纯 Python 应用，无需 C/C++ 编译)
- 状态: built

## 软件简介
git-cola 是一个基于 Python + Qt (PyQt5/PyQt6/PySide2) 的 Git GUI 客户端。
通过 qtpy 抽象层支持多种 Qt 绑定。

## 编译步骤

1. 下载源码 tarball: https://github.com/git-cola/git-cola/archive/refs/tags/v4.19.0.tar.gz
2. 安装构建依赖: pip3 install setuptools_scm polib qtpy
3. 修改 pyproject.toml 绕过 setuptools_scm (见源码修改)
4. 安装 desktop 文件、图标、文档:
   make PIP=pip3 DESTDIR=$TEST_PREFIX prefix=$DEFAULT_PREFIX install-desktop-files install-icons install-htmldocs install-metainfo
5. pip install Python 包:
   pip3 install --no-deps --no-build-isolation --target=$TEST_PREFIX/$DEFAULT_PREFIX/lib/python3.12/site-packages .
6. 创建 entry point 脚本:
   cola, git-cola, git-dag, git-cola-sequence-editor

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `install` 命令不存在 | 鸿蒙系统缺少 GNU coreutils 的 install 命令 | 创建 install wrapper 脚本到 /usr/local/bin/install |
| 2 | pip 构建隔离环境找不到 setuptools | 社区源在隔离环境中无法安装 setuptools | 使用 --no-build-isolation 选项 |
| 3 | setuptools_scm 3.5.0 依赖 pkg_resources | setuptools 83.0.0 移除了 pkg_resources 模块 | 卸载 setuptools_scm，硬编码版本号 |
| 4 | pip 不支持 --root 和 --prefix 同时使用 | pip 版本限制 | 改用 --target 安装 Python 模块，手动创建 bin 脚本 |
| 5 | Qt 绑定缺失 (PyQt5/PyQt6) | 鸿蒙平台无预编译 Qt 绑定 wheel | 运行时依赖，不影响安装本身 |

## 源码修改

### pyproject.toml
1. 移除 setuptools_scm 构建依赖: `requires = ["setuptools>=61.2"]`
2. 硬编码版本号: `version = "4.19.0"` (替代 `dynamic = ["version"]`)
3. 移除 `[tool.setuptools_scm]` 配置节

## 依赖版本

- Python: 3.12.9
- setuptools: 83.0.0
- pip: 24.3.1
- polib: 1.2.0
- qtpy: 1.11.3
- make: GNU Make 4.4.1

## 验证结果

```bash
# 模块导入验证
PYTHONPATH=$TEST_PREFIX/usr/local/lib/python3.12/site-packages python3 -c "from cola._version import VERSION; print(VERSION)"
# 输出: 4.19.0

# 安装结构验证
# bin/: cola, git-cola, git-dag, git-cola-sequence-editor
# lib/python3.12/site-packages/cola/: 完整 Python 模块
# share/applications/: git-cola.desktop, git-cola-folder-handler.desktop, git-dag.desktop
# share/icons/hicolor/scalable/apps/: git-cola.svg
# share/doc/git-cola/: hotkeys*.html
# share/metainfo/: git-cola.appdata.xml, git-dag.appdata.xml
```

## 注意事项

- git-cola 是纯 Python 应用，不需要 C/C++ 编译器
- 运行时需要 PyQt5 或 PyQt6 Qt 绑定（鸿蒙平台目前缺失，需单独适配）
- install 命令的 wrapper 脚本是平台适配必需品
- pyproject.toml 修改绕过 setuptools_scm 是因为鸿蒙 Python 环境的 setuptools/pkg_resources 兼容性问题
---

**编译结束**: 2026-07-16 16:48
**最终状态**: built
