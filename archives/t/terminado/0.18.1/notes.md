# terminado 0.18.1 适配笔记

## 软件概况

- **上游**：https://github.com/jupyter/terminado （PyPI: terminado）
- **用途**：Tornado websocket 后端，为浏览器中的 Xterm.js 终端提供 pty 服务（Jupyter 等项目的终端基础组件）
- **技术形态**：**纯 Python wheel 包**，无 C 扩展模块；PEP 517 构建后端为 `hatchling.build`
- **上游依赖**：`ptyprocess`（POSIX）、`tornado>=6.1.0`（均已发布于 ohpcd）

## 构建策略

复用仓库内 Python 包既有模式（`archives/t/tornado/6.5.2`、`archives/p/ptyprocess/0.7.0`、`archives/s/snakeviz/2.2.2`）：

```bash
pip wheel . --no-deps -w dist .     # 构 wheel（--no-deps：依赖走 Conan）
# 解包 wheel 到 lib/python3.12/site-packages
# package_info() 将 site-packages 注入 runenv_info 的 PYTHONPATH
```

`package_type = "python-require"`（Conan 2 无 python 类型，library 会要求 shared option，wheel 无法满足——同 ptyprocess 配方理由）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pip wheel --no-build-isolation` 报 `BackendUnavailable: No module named 'hatchling'` | terminado 用 hatchling 构建后端；`--no-build-isolation` 时 pip 从构建解释器 site-packages 导入 backend，而本机解释器未装 hatchling | **去掉 `--no-build-isolation`**，保留 pip build isolation，由 pip 从社区索引自动拉取 hatchling（与 tornado 配方一致） |
| 2 | test_package `import tornado` 失败（ModuleNotFoundError） | tornado 仅通过 terminado 传递依赖进入图；其 runenv（PYTHONPATH）未进入 test 环境 | test_package 显式 `self.requires("tornado/6.5.2")` 与 `ptyprocess/0.7.0`（同 snakeviz/2.2.2 先例） |
| 3 | test_package 中 `tornado.web` 无 `WebSocketHandler` 属性 | TermSocket 的真实基类是 `tornado.websocket.WebSocketHandler`（terminado/websocket.py:27 实证），`tornado.web` 不导出该类 | 断言改为 `issubclass(TermSocket, tornado.websocket.WebSocketHandler)`，并以源码行号注释留证 |
| 4 | `hasattr(PtyWithClients, "ptyproc")` 为 False | `ptyproc` 是 `PtyWithClients.__init__` 里的**实例属性**（`PtyProcessUnicode.spawn()` 赋值），类上不存在 | 改为对真实实例断言：`mgr.new_terminal()` 后检查 `.ptyproc.fd` |
| 5 | 消费者测试解释器选到 hnp python3，其 `import select/pty` 失败 | **G2（hnp python3 stdlib 残缺）**：该解释器的 `lib-dynload` 里是非本机架构编译的 `.so`（`select.cpython-312.so`，无 `-aarch64-linux-ohos` 后缀），import 即失败；而 `~/usr/local/bin/python3` 的 lib-dynload 是本机架构且完整 | test_package `_pick_python()` 用**功能探针**（实际 `pty.openpty()` + `select.select()` 往返）筛选解释器，而非仅 `import select`——import 成功不代表 .so 可加载 |

## 运行期能力核验（W0b 语义可迁移性）

真机（鸿蒙 PC aarch64）实测：**PTY 完全可用**——`/dev/ptmx` 可打开、`pty.openpty()` 成功返回 master/slave fd、写入 `echo xxx` 能经伪终端回显。

此结论是 terminado 可适配的关键前提：它的全部功能建立在「启动子进程 + pty + websocket 转发」上。

## 验证结果

```bash
conan create archives/t/terminado/0.18.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

- 包创建成功：`terminado/0.18.1`（package id `fd290cc3f8c030160f3699659cebaef1fab6aa64`）
- test_package 5 项实质断言全部 PASS：
  - `import terminado` 解析到本包 payload（`TERMINADO_PACKAGE_ROOT` 校验）
  - `TermSocket` 确为 `tornado.websocket.WebSocketHandler` 子类、`TermManagerBase.get_terminal` 存在
  - 真 pty 打开（master fd=5）
  - 命令经 pty 回显（`echo HELLO_FROM_PTY` → `b'echo HELLO_FROM_PTY\r\n'`）
  - 依赖 tornado 解析到自身 payload

## 上游测试说明

terminado 0.18.1 上游仅提供 `tests/basic_test.py`（unittest 风格，模块级 `import pytest`）。本机构建期解释器未随包提供 pytest，故该用例在 build() 中如实记为无法运行（warning），**未删改上游断言、未伪造通过**；功能验证由 test_package 的真 pty 用例承担。

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | python-require 配方（pip wheel + site-packages 布局 + PYTHONPATH 注入） |
| `conandata.yml` | 官方 PyPI 源 + sha256 |
| `test_package/` | R34 实质验证（真 pty 往返 + API 基类断言 + 解释器功能探针） |
| `manifest.yaml` | status: built |
---

**编译结束**: 2026-10-13 02:06
**最终状态**: built
