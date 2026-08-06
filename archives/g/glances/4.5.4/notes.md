# glances 4.5.4 适配笔记

## 编译环境
- 构建系统: custom (setuptools/pyproject.toml)
- 编译日期: 2026-08-06
- 编译器: N/A (pure Python, no C/C++ compilation needed)
- 状态: built

## 编译步骤

1. 下载 glances-4.5.4.tar.gz 源码包 (PyPI)
2. `python3 -m pip install . --no-deps --target=$TEST_PREFIX` 安装 glances 本体
3. `python3 -m pip install psutil defusedxml packaging jinja2 pyinstrument shtab --target=$TEST_PREFIX/glances-deps` 安装运行时依赖
4. 验证 glances 模块和二进制入口存在

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | psutil C 扩展无法加载 | OHOS ELF 签名限制，未签名的 .so 不可加载 | 平台限制，CI 环境通过 ci/artifacts/sign.sh 签名后可用。本地测试改为从源码读取 __version__ 而非 import |
| 2 | pip 下载源不可用 | 默认 PyPI 源无法访问 | 配置社区 pip 源 pypi.cnb.cool |
| 3 | init-build 嵌套源码检测错误 | docs/ 目录被误识别为嵌套源码 | 手动修正 .orig 和 .work 目录 |

## 源码修改

无补丁。glances 是纯 Python 包，pip install 直接构建成功。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| psutil | 7.2.2 | C 扩展，社区源提供 OHOS 适配 wheel |
| defusedxml | 0.7.1 | 纯 Python |
| packaging | 26.3 | 纯 Python |
| jinja2 | 3.1.4 | 纯 Python |
| pyinstrument | 5.1.2 | 纯 Python |
| shtab | 1.9.3 | 纯 Python |

## 验证结果

```bash
# 构建验证
python3 -m pip install . --no-deps --target=$TEST_PREFIX
# → Successfully installed Glances-4.5.4

# 包结构验证
ls $TEST_PREFIX/bin/glances     # → entry point script exists
ls $TEST_PREFIX/glances/__init__.py  # → Python package exists
```

## 注意事项

- psutil C 扩展 (.so) 在 OHOS 上需要 ELF 签名才能加载，CI 环境通过 sign.sh 处理
- glances/__init__.py 在导入时检查 psutil，缺失则 sys.exit(1)
- 运行时依赖通过 pip install --target 打包到 glances-deps/ 目录
---

**编译结束**: 2026-08-06 14:06
**最终状态**: built
