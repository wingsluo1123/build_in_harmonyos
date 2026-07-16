# git-cola

Git Cola is a powerful Git GUI with a slick and intuitive user interface.

## 信息
- 版本: 4.19.0
- 许可证: GPL-2.0
- 主页: https://github.com/git-cola/git-cola
- 构建系统: Makefile + pip (Python setuptools)
- 类型: Python 应用 (GUI)

## 描述
git-cola 是一个基于 Python + Qt (PyQt5/PyQt6/PySide2) 的 Git 图形界面客户端。
通过 qtpy 抽象层支持多种 Qt 绑定，提供直观的 Git 操作界面。

## 鸿蒙适配说明
- 纯 Python 应用，无需 C/C++ 编译
- 适配修改: 移除 setuptools_scm 依赖，硬编码版本号
- 运行时依赖: polib, qtpy, PyQt5/PyQt6/PySide2 (需单独安装)
