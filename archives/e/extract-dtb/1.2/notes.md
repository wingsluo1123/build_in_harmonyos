# extract-dtb 1.2 适配笔记

## 编译环境
- 构建系统: setuptools (Python package)
- 编译日期: 2026-08-06
- 编译器: N/A (Python package)
- 状态: built (conan adaptation)

## 源码信息
- 仓库: https://github.com/PabloCastellano/extract-dtb
- 版本: 1.2 (tag: 1.2)
- SHA256: 2fa2683e8c6db61d6edf8ed08a740959f6d447c188f4781e5e24af60b9decf43
- 许可证: GPL-3.0-or-later

## 编译步骤

Pure Python 包，通过 setuptools 安装：

```bash
pip install . --target=<install_dir> --no-deps --no-build-isolation
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `extract-dtb --version` 崩溃 | 源码 `extract_dtb.py` 中 `main()` 使用 `__version__` 变量但未定义 | 添加 `__version__ = "1.2"` (patch: 0001-extract_dtb-extract_dtb.py.patch) |
| 2 | `file` 命令失败 | 缺少 magic 数据库 (Gotcha E002) | 不影响功能，已知平台限制 |

## 修复说明

### 0001-extract_dtb-extract_dtb.py.patch
extract-dtb 1.2 源码的 `extract_dtb.py` 文件中，`main()` 函数使用了 `__version__` 变量：
```python
parser.add_argument("-V", "--version", action="version", version=__version__)
```
但 `__version__` 在模块中从未定义。这导致 `--version` 和 `--help` 均会抛出 `NameError`。

修复：在 `extract_dtb.py` 中添加 `__version__ = "1.2"` 定义（DTB_HEADER 之后）。

## 验证结果

### extract-dtb --version
```
$ extract-dtb --version
1.2
```
✅ PASS

### extract-dtb --help
```
$ extract-dtb --help
usage: extract-dtb [-h] [-o OUTPUT_DIR] [-n] [-V] filename
Extract dtbs from kernel images.
```
✅ PASS

### Conan 验证
- conan create: PASS
- test_package: PASS

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (Python/setuptools) |
| conandata.yml | 源码 URL + SHA256 + 补丁声明 |
| test_package/ | Conan L1 测试 |
| patches/0001-extract_dtb-extract_dtb.py.patch | __version__ 修复补丁 |

---
**Conan 适配完成**: 2026-08-06
**最终状态**: built
---

**编译结束**: 2026-08-06 09:45
**最终状态**: built
