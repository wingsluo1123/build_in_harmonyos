# jiratui

## 软件简介
JiraTUI 是基于 Textual 框架的 Atlassian Jira 终端交互界面（TUI），支持 Jira Cloud Platform REST API v2/v3。

## OHOS 适配要点
- Python 包（非 C/C++ 库），使用 pip install 构建
- 依赖 mistune>=3.2，鸿蒙 PyPI 源仅有 0.8.4，需从源码安装
- pydantic_core Rust 扩展受 SELinux 限制，CI 环境需 ELF 签名
- C 库依赖 libmagic 和 libyaml 需单独适配

## 安装方式
```bash
pip install jiratui==1.10.1
```

## 版本
- 1.10.1 (2026-07-09)
