# cachecontrol 0.14.4 — 适配笔记

## 概述
- 上游: https://github.com/psf/cachecontrol（PyPI sdist 0.14.4）
- 类型: 纯 Python 包；运行依赖 requests、msgpack、[filecache]→filelock
- License: Apache-2.0
- SHA-256 (PyPI sdist): e6220afafa4c22a47dd0badb319f84475d79108100d04e26e8542ef7d3ab05a1

## 适配要点
1. copytree staging → site-packages/cachecontrol（WR-008 模式），无源码补丁。
2. package() 生成最小 dist-info（cachecontrol-0.14.4.dist-info：METADATA/WHEEL）：
   上游 __init__.py 经 importlib.metadata 无守卫解析 __version__，无 dist-info
   则 import 抛 PackageNotFoundError。
3. 依赖映射：msgpack → python-msgpack/1.1.1（ohpcd msgpack/7.0.1 是 msgpack-c）；
   [filecache] → filelock/3.32.7（lastversion 启动路径 FileCache）。
4. R38: 纯库无 commands.json。

## 上游测试（NOT_RUN — REASONABLY_EXHAUSTED，2026-09-26 核验）
- sdist 的 tests/ 为空目录（已核验）；上游测试仅存 GitHub 仓。
- 已取回官方 tag v0.14.4 tarball（sha256 d862b0f3…），pytest 收集阶段即失败：
  tests/conftest.py import cherrypy——测试专用依赖设备未装；按写入边界不改动
  设备 Python 环境，不补装。
- 结论: 上游套件在 OHOS 设备当前约束下无法运行（NOT_RUN），非省略；
  等效验证: test_package 消费者测试（FileCache 落盘 + msgpack 序列化 + filelock
  联动的全栈离线往返，CI L1 真实执行）。

## 环境
- Python 3.12.9, Conan 2.x, profile ohos-aarch64
