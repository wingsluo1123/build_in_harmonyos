# asciidoc 10.2.1 适配笔记

## 编译环境
- 构建系统: Python (setup.py)
- 编译日期: 2026-08-05
- 编译器: N/A (纯 Python 包)
- 状态: built

## 编译步骤

```bash
# 1. 下载源码 (GitHub releases)
# 2. 解压
# 3. 安装 Python 包
python3 setup.py install --prefix=$DEFAULT_PREFIX
# 4. 验证
asciidoc --version
a2x --version
asciidoc -o test.html test.adoc
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | asciidoc 命令报 PackageNotFoundError | 入口点脚本使用 importlib.metadata 查找包元数据，但安装位置不在系统 Python 搜索路径中 | 创建 wrapper 脚本，自动设置 PYTHONPATH 为相对于脚本的位置 |
| 2 | GitHub 直连下载超时 | 鸿蒙环境无法直接访问 GitHub | conandata.yml 使用 GitHub URL，CI 自动添加镜像 fallback |

## 源码修改

- 替换 bin/asciidoc 和 bin/a2x 入口点脚本为自包含 wrapper（自动设置 PYTHONPATH）
- 无源码补丁

## 依赖版本

- 无外部依赖（纯 Python 包）
- Python >= 3.5

## 验证结果

```bash
$ asciidoc --version
asciidoc 10.2.1

$ a2x --version
a2x 10.2.1

$ echo '= Test\n\nHello.' | asciidoc -o /tmp/test.html -
# 生成有效 HTML 输出
```

## 注意事项

- asciidoc 是 Python 应用程序，不是 C/C++ 库
- 构建产物为 Python 脚本（bin/asciidoc, bin/a2x）和 Python 包（lib/python3.x/site-packages/asciidoc/）
- conanfile.py 中 package_type = "application"，settings = "os", "arch"（无需 compiler）
---

**编译结束**: 2026-08-05 03:09
**最终状态**: built
