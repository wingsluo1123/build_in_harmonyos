# 编译笔记 — aiven-client 4.16.0

**软件名称**: aiven-client (Aiven.io client library / command-line client)
**版本**: 4.16.0
**上游仓库**: https://github.com/aiven/aiven-client
**许可证**: Apache-2.0
**构建系统**: hatchling（纯 Python src layout: aiven/）

## 软件简介

aiven-client (`avn`) 是 Aiven 官方命令行客户端，提供云服务管理、Kafka topic 操作、
VPC peering、认证令牌等功能。纯 Python 包，无 C 扩展。构建后端 hatchling + hatch-vcs，
sdist 已含生成文件 `aiven/client/version.py`（固定 `__version__='4.16.0'`）。

## 依赖

- 运行时依赖: requests (>=2.2.1 on linux), requests-toolbelt (>=0.9.0), certifi (>=2015.11.20.1)
- 测试依赖: pytest, click (dev)
- 构建依赖: hatchling, hatch-vcs（由 pip build isolation 自动从 pypi.cnb.cool 下载）

## 构建方式

```bash
conan create archives/a/aiven-client/4.16.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing -nr
```

- `pip install . --prefix=... --no-deps`（构建后端 hatchling + hatch-vcs）
- 不带 `--no-build-isolation`：让 pip 自动创建隔离环境并从 pypi.cnb.cool 源下载构建依赖
  （同 pluggy/pyparsing/cfgv 方案）

## 适配说明

1. **纯 Python 无 C 扩展**：构建用 sys.executable（Conan 运行的 Python），不使用 clang。
   conanfile 的 settings 含 os/arch 仅用于 R32 OHOS 平台兼容验证。
2. **PYTHONPATH 导出**：package_info 通过 runenv_info.append_path 导出
   site-packages 路径，供下游消费者和 test_package import aiven。
3. **R32 平台兼容**：conanfile validate() 拒绝非 Linux/OHOS 的 OS。
4. **R33 不依赖 shell 环境变量**：build() 使用 sys.executable（Conan 运行时 Python）。
5. **R34 test_package 实质性测试**：7 项 smoke test 覆盖模块导入/版本/AivenClient 类/
   argx.CommandLineTool/pretty.format_item/speller.suggest/session.get_requests_session。

## 上游测试验证

```bash
cd .tmp-aiven-client/aiven_client-4.16.0
pip install -e ".[dev]" pytest requests requests-toolbelt certifi
python3 -m pytest tests/ -v --tb=short
```

结果: **223 passed in 40.48s** — 100% 通过率，无需子任务定位崩溃点。

## 文件结构

```
archives/a/aiven-client/4.16.0/
├── conanfile.py           # Conan 配方（hatchling 纯 Python）
├── conandata.yml          # 源码 URL + SHA256
├── manifest.yaml          # 软件级元数据 + 版本索引
├── notes.md               # 适配笔记
└── test_package/
    ├── conanfile.py       # test_package 配方
    └── test.sh            # 7 项 smoke test
```
---

**编译结束**: 2026-08-10 23:05
**最终状态**: built
