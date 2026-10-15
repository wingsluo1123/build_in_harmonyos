# tqdm 4.69.0 — 适配笔记

## 概述
- 上游: https://github.com/tqdm/tqdm（PyPI sdist 4.69.0，官方 tag v4.69.0 →
  commit 6ab24dc）
- 类型: 纯 Python 包，非 Windows 平台零运行时依赖（colorama 仅 Windows）
- License: MPL-2.0 AND MIT
- SHA-256 (PyPI sdist): 700c5e85dcd5f009dd6222588a29180a193a748247a5d855b4d67db93d79a53b

## 适配要点
1. copytree staging → lib/python3.12/site-packages/tqdm（WR-008 模式），无源码补丁。
2. version.py 经 importlib.metadata.version("tqdm") 解析 __version__——copytree
   移植必须补 tqdm-4.69.0.dist-info（METADATA+WHEEL，cachecontrol recipe 先例）；
   补齐后 __version__ 精确为 4.69.0（4.70.1 的上游 bump 遗漏问题在本版不存在）。
3. 上游 console_scripts 入口 tqdm（tqdm.cli:main）未承载：lastversion 只消费
   tqdm.tqdm/trange 库 API；不伪造工具面，无 commands.json。
4. recipe 以同仓 feat/tqdm-4.70.1 分支 commit a67abdb6 的 4.70.1 recipe 为蓝本，
   仅版本/URL/SHA256/dist-info 目录名与文档差异。

## 上游测试（设备实测 2026-09-27）
- 入口: `python3 -m pytest tests/ -q -o addopts= --basetemp=<可写目录>`
  （-o addopts= 清空 pyproject 的 --asyncio-mode=strict；basetemp 规避设备
  文件系统上 pytest tmpdir 所有权检查误报）。
- 实测: 144 passed / 1 failed / 7 skipped（152 collected，约 40 秒）。
  前置: pip 安装 pytest-asyncio 1.4.0 后 8 例 asyncio 用例全部转绿。
- 归因: 唯一失败 tests_main.py::test_pipes 以裸命令名 'ls' 调 subprocess，
  本设备 Python 3.12 的 posix_spawn 路径不做 PATH 解析（shutil.which 可定位
  /system/bin/ls、绝对路径执行正常）——设备环境/测试依赖归因，非实现缺陷。
- 日志见 run 证据 reports/upstream-pytest.log、reports/upstream-test-summary.md。
- 等效验证: test_package 消费者测试（非 TTY 流降级、format_meter、update，
  __version__ 精确断言 4.69.0），CI L1 真实执行通过。

## 环境
- Python 3.12.9, Conan 2.x, profile ohos-aarch64
