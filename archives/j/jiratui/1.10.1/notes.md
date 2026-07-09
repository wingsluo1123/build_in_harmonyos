# jiratui 1.10.1 鸿蒙适配笔记

## 软件信息
- **名称**: jiratui
- **版本**: 1.10.1
- **语言**: Python
- **上游仓库**: https://github.com/whyisdifficult/jiratui
- **PyPI**: https://pypi.org/project/jiratui/
- **License**: MIT
- **构建系统**: Python pip
- **构建产物**: CLI 工具 jiratui
- **版本验证**: jiratui version 输出 1.10.1

## 依赖分析

### Python 包依赖（通过 pip 安装）
13 个直接依赖均可在鸿蒙 PyPI 源获取：click, gitpython, httpx, marklas, puremagic, pydantic-settings, python-dateutil, python-json-logger, textual-autocomplete, textual-image, textual, urllib3, xdg-base-dirs

### 关键传递依赖问题
1. **mistune>=3.2**（marklas 依赖）：鸿蒙 PyPI 源仅有 0.8.4，需从源码安装
2. **pydantic_core**（Rust 编译扩展）：CI 环境通过 ELF 签名可正常加载

### C 库依赖
- libmagic/5.48 — 未发布到制品仓，需单独适配
- libyaml/0.2.5 — 未发布到制品仓，需单独适配

## 构建过程
1. 源码获取：从 PyPI 下载 sdist (tar.gz)，SHA256 验证通过
2. 构建：pip install --no-deps jiratui==1.10.1
3. 验证：jiratui version 输出 1.10.1（CI 环境验证）

## 已知限制
- pydantic_core .so 受 HarmonyOS SELinux 限制无法在本地加载，CI 环境可签名
- mistune 3.x 不在鸿蒙 PyPI 源
- libmagic/libyaml 需后续单独适配

---

**编译开始**: 2026-07-09
**最终状态**: built
