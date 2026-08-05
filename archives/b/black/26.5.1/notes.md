# black 26.5.1 适配笔记

## 编译环境
- 构建系统: pip (Python项目, hatchling backend)
- 编译日期: 2026-08-05
- 编译器: N/A (纯Python项目，无C/C++编译)
- 状态: built

## 编译步骤

1. `ohc-run.py init-build black 26.5.1 --url=https://files.pythonhosted.org/.../black-26.5.1.tar.gz`
2. 在 build() 中创建 `src/_black_version.py`（GitHub tarball 缺少此文件）
3. `pip install hatchling hatch-vcs hatch-fancy-pypi-readme`（构建依赖）
4. `SETUPTOOLS_SCM_PRETEND_VERSION=26.5.1 pip wheel . --no-deps --no-build-isolation`
5. 解压 wheel 到 `lib/python3.X/site-packages/`
6. 创建 `bin/black` wrapper 脚本

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | src/_black_version.py 缺失 | GitHub tarball 无 git 元数据，hatch-vcs 无法生成此文件 | 在 build() 中直接创建 `src/_black_version.py: version = "26.5.1"` |
| 2 | 版本检测失败 | setuptools-scm 无法检测版本 | 设置 SETUPTOOLS_SCM_PRETEND_VERSION=26.5.1 |
| 3 | 构建隔离超时 | pip build isolation 下载 hatchling 等依赖超时 | 使用 --no-build-isolation 并预装构建依赖 |

## 源码修改

- 无补丁。在 conanfile.py 的 build() 方法中直接创建 `src/_black_version.py`

## 依赖版本

- python3: 3.12.9
- pip: 26.1.2

## 验证结果

```bash
black --version
black, 26.5.1 (compiled: no)
Python (CPython) 3.12.9
```

## 交付物

| 文件 | 说明 |
|------|------|
| black-26.5.1-ohos-aarch64.tar.gz | Release包 (wheel + bin wrapper) |

## 注意事项

- 纯 Python 项目，使用 pip wheel 构建方式
- GitHub tarball 缺少 src/_black_version.py，在 build() 中创建
- 需设置 SETUPTOOLS_SCM_PRETEND_VERSION
- 构建依赖需预装 (hatchling, hatch-vcs, hatch-fancy-pypi-readme)
---
**编译结束**: 2026-08-05 10:25
**最终状态**: built
