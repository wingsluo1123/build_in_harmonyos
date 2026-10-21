# synadm 0.49.2 适配笔记

## 结论速览

- **类型**：纯 Python CLI（Matrix Synapse homeserver 管理工具），**无 C/C++ 编译步骤**；
  按任务口径以 `python` 语言处理（`lang-preflight --lang python` 通过），**未按 C/C++ 规则硬适配**，
  配方不引入任何编译器依赖（`cc/cxx: none`），`build()` 只做字节码预编译（`compileall`）。
- **源码改动**：**零补丁**（`patches/` 为空，`patches_applied: []`）。上游代码在 OHOS 上可直接跑，
  适配全部落在配方 staging/vendoring 层与 test_package 层。
- **上游测试**：**0 个自动化用例**（三项独立证据见 §"上游测试为 0 的取证"）。
- **适配套件**：**63 用例 / 114 断言**，`Ran 42 tests ... OK` + `Ran 21 tests ... OK`，
  `conan create` rc=0。其中鸿蒙特有套件 21 用例（含 AF_UNIX 管理链路、HMDFS/只读 /tmp 语义、原生解释器调用）。
- **状态**：built（W3 本地 CI + `conan create` 全绿；conan-verify G1 对纯 Python 配方误报，见下节）

## 编译（打包）步骤

纯 Python 无 configure/make，实际命令就是完整的构建+验证入口：

```bash
export PATH="$HOME/.local/bin:$PATH"
export OHC_PROJECT_DIR=/storage/Users/currentUser/sztu/.worktrees/synadm-0.49.2
conan create archives/s/synadm/0.49.2 \
  -pr=$OHC_PROJECT_DIR/ci/conan/profiles/ohos-aarch64 --build=missing
```

配方内部流程（`archives/s/synadm/0.49.2/conanfile.py`）：

| 阶段 | 动作 |
|---|---|
| `export()` | `conandata.yml` 钉版：官方 PyPI sdist（sha256 `1cd4dc33…`）+ 3 个 vendored 依赖 sdist |
| `_stage()` | 建 `lib/python3.12/site-packages` + `bin` + `licenses`；铺 `synadm/`；写 dist-info（含 `console_script = synadm = synadm.cli:root`）；生成 `bin/synadm` wrapper（`#!/usr/bin/env python3` + `sys.exit(root())`）；`chmod 0755` |
| `_vendor()` | copytree 三个 vendored sdist 的模块树，**ignore** `__pycache__/tests/test/testutils.py/*.egg-info/*.dist-info`；为每个件写 PEP-427 归一化的 dist-info |
| `build()` | `PYTHONPYCACHEPREFIX=<build>/pycache python3 -m compileall -q <site>`（**不污染包目录**，OHOS 只读场景下产物更干净） |
| `package_info()` | 遍历 `self.dependencies.host.values()` 收集各依赖可导入根 → `buildenv_info`/`runenv_info` 逆序 `prepend_path("PYTHONPATH", …)`，再追加自身 site 与 `bin`；`cpp_info` 清空 libs/includedirs/libdirs，`bindirs=["bin"]` |
| `package_id()` | `self.info.clear()`（noarch：所有 profile 共用一包） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ModuleNotFoundError: No module named 'chardet'`（test_package 级联 7 error + 多 failure） | registry `requests/2.22.0` 对自身运行时依赖**未标 `run=True`** → Conan 把它们归入 "Skipped binaries"，对本包 `package_info()` 完全不可见（`dependencies.host` 过滤 `{"build":False,"test":False,"skip":False}`） | 把 requests 的导入闭包（certifi/chardet/idna/urllib3）**直接声明**为 `requires(..., run=True)`；`package_info()` 改为遍历 `self.dependencies.host.values()`（详见知识草稿 E600）。实测日志：`published 8 dependency import path(s)` |
| 2 | `PackageNotFoundError: No package metadata was found for click-option-group / requests-unixsocket` | `.dist-info` 目录名保留连字符（PEP-503 展示名），而 `importlib.metadata` 按 **PEP-427** 查目录名（`-` → `_`） | `_write_dist_info()` 目录名用 `dist.replace('-', '_')`；`METADATA` 内 `Name:` 保留原名。已用探针目录实测确认 |
| 3 | 静态守卫 `test_synadm_writes_no_state_to_tmp` 命中 `requests_unixsocket/testutils.py:78 → '/tmp/test_requests.%s_%s_%s'` | 整树 copytree 把上游**测试工具**带进产物；OHOS 上 `/tmp` 是**只读挂载**（Errno 30） | `_vendor()` 的 `ignore_patterns` 剪掉 `tests/test/testutils.py/*.egg-info/*.dist-info/__pycache__`（testutils 还 import waitress/requests_mock，均非运行期依赖） |
| 4 | 本地 stub Synapse 对 `?from=0&limit=100` 返 404（`KeyError: 'total'`） | 测试路由用完整 `self.path` 匹配，query string 参与比较 | 路由前 `urllib.parse.urlparse(self.path).path`；且入站路径需 `unquote`（synadm 的 `query()` 以 `safe=""` 引号化 MXID） |
| 5 | `TypeError: dict() got multiple values for keyword argument 'base_url'` | 测试用 `dict(base_url=..., **CONFIG)` 合并 | 改 merge-dict 写法 `{**CONFIG, "base_url": self.base_url, **overrides}` |
| 6 | `KeyError: 'user_id'` | `query("get", "v2/users/{user_id}", "<positional>")` —— 位置参数会被 `quote(safe="")` 后按 `{0}` 填 | 用 kwarg 形式 `query("get", "v2/users/{user_id}", user_id="@alice:example.org")` |
| 7 | CLI 报 `Error: No such command 'show'` | 子命令名记错 | 正确命令是 `synadm user details <MXID>` |
| 8 | `FileNotFoundError` in `requests_unixsocket/adapters.py:36 sock.connect`（同一 client 第二次请求） | 上游 `requests_unixsocket` 会**原地改写** `session.base_url`，二次编码后路径失效 | 每个请求用新建 client（已在测试注释中写明） |
| 9 | `AssertionError: 'python3.12' != 'lib'` | site 目录层级算错 | `os.path.basename(os.path.dirname(SITE))` |
| 10 | `ThreadingHTTPServer` 起不来（AF_UNIX） | `HTTPServer.server_bind()` 假定 `(host, port)` 元组 | 自定义 `_UnixHTTPServer`：`address_family = socket.AF_UNIX` + 覆写 `server_bind` 直接 `socket.socket.bind(self.socket, self.server_address)` + `listen()` |

## 上游测试为 0 的取证（务必如实申报，不得少报/虚报）

任务要求"完整运行上游全部测试用例"。实测上游**没有可运行的自动化测试**，三项独立证据：

1. **官方 PyPI sdist** `synadm-0.49.2.tar.gz`：解包共 **27 个文件**，无 `test*/` 目录、
   无 `test_*.py` / `*_test.py`、无 `pytest.ini` / `tox.ini` / `setup.py` 测试入口。
2. **codeberg 上游 master 树**：**79 个条目**，按 `test|spec|check` 关键字过滤命中 **0** 个测试路径。
3. **`.forgejo/workflows`**：仅 `lint.yaml`（逐字确认只执行 `flake8 synadm`，无测试调用）与
   `release.yaml`（打包发布）。

处置：`test_package/MANIFEST.yml` 标 `upstream_test_count: 0` + `upstream_tests: []` + 上述证据；
覆盖责任由适配套件 63 用例承担（42 通用消费者 + 21 鸿蒙特有），全部为 R34 实质测试。
**不**把 flake8 引入配方 `build()`：registry 无 flake8 件，为跑静态检查而 bootstrap 新依赖会给 CI
带来不必要的不稳定面（记录为已知取舍）。

## Vendoring 决策与取证

3 个上游声明的运行时依赖在制品仓**确实无件**（PF4 依赖闸逐个探测 + `conan download <ref> -r=ohpcd --only-recipe` 双重实证），
且全部在模块顶层 `import`，缺任何一个则 `import synadm.api` 与所有 `synadm.cli.*` 立即失败：

| 件 | 版本 | 用途 | 许可证 |
|---|---|---|---|
| dnspython | 2.8.0 | `dns.resolver`（`synadm/cli/_helper.py` 的 server 发现路径） | MIT |
| click-option-group | 0.5.9 | optgroup / required / 互斥选项组（`cli/_common.py, history.py, matrix.py, media.py, room.py, user.py`） | BSD-3-Clause |
| requests-unixsocket | 0.4.1 | `http+unix://` 本地 unix socket 管理链路（`synadm/api.py`） | Apache-2.0 |

三者各自的进一步依赖（requests≥1.1 / click≥7.0 / 无）均已由本配方提供，闭包到此为止。
按钉版官方 PyPI sdist（URL + sha256）vendor 进本包 site-packages，许可证文件随包（`licenses/`）。
先例（本仓库已合并）：`archives/d/dehydrated-hook-ddns-tsig/0.1.4`（dnspython）、`archives/i/interrogate/1.7.0`（py）。
**未**因依赖缺失而 `--status dependency_missing` 止损：三者均为纯 Python、可钉版官方源、有已合并先例，
捎带适配（自己发 conan 包）反而违反 W2 PR 原子性。

## 依赖版本

已发布件（全部 `run=True`）：`click/8.4.2`、`requests/2.22.0`、`tabulate/0.10.0`、`pyyaml/6.0.2`、
`certifi/2026.7.22`、`chardet/5.2.0`、`idna/3.18`、`urllib3/2.7.0`。
Vendor 件：dnspython 2.8.0 / click-option-group 0.5.9 / requests-unixsocket 0.4.1。
已知无害告警：`RequestsDependencyWarning: urllib3 (2.7.0) or chardet (5.2.0) doesn't match a supported version`
（requests 2.22.0 的 legacy 范围检查；仅 stderr 警告，63 用例在该警告存在时全过）。

## 验证结果

```bash
$ conan create archives/s/synadm/0.49.2 -pr=$OHC_PROJECT_DIR/ci/conan/profiles/ohos-aarch64 --build=missing
...
synadm/0.49.2: published 8 dependency import path(s): click, requests, tabulate, pyyaml, certifi, chardet, idna, urllib3
Ran 42 tests in 15.754s
OK
Ran 21 tests in 5.700s
OK
exit: 0
```

逐项清单见 `reports/test-report.md`；数字口径见 `test_package/MANIFEST.yml`。

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | 纯 Python 配方（noarch、application、vendoring + PYTHONPATH/PATH 环境注入） |
| `conandata.yml` | 官方 sdist + 3 个 vendored 件钉版（URL/sha256）+ PF4 探测取证注释 |
| `test_package/conanfile.py` | 消费者入口：优先 OHOS 原生解释器 `/data/service/hnp/bin/python3`，`env="conanrun"` 下跑两个套件并聚合失败 |
| `test_package/test_synadm.py` | 42 用例 / 67 断言（通用消费者视角，本地 HTTP stub） |
| `test_package/test_synadm_ohos.py` | 21 用例 / 47 断言（鸿蒙特有：AF_UNIX 链路、HMDFS/只读 /tmp、posix 分支与权限收敛、原生调用） |
| `test_package/MANIFEST.yml` | 上游 0 用例取证 + 两套件声明（`test_type: "R34"`） |
| `reports/test-report.md` | 63 用例逐项结果 + 5 个关键问题的根因/方案 |
| `manifest.yaml` / `notes.md` | 版本级归档元数据 |
| `../commands.json` | R38/L0k 命令行工具声明（`type: "tool"`） |

## 注意事项

1. **消费方用法**：`conan install --requires=synadm/0.49.2 --build=missing` 后必须
   `source conanrun.sh`（或 `VirtualRunEnv` 生成的 env）再调用 `synadm`，否则 PYTHONPATH/PATH 未注入。
2. `package_id()` 已 `self.info.clear()`：改 profile 不会重建；如需 Python 版本相关行为，
   site 路径按**当前解释器** `pythonX.Y` 计算，不要硬编码 3.12。
3. 鸿蒙侧写配置/日志必须走 `$HOME`（`~/.config/synadm`、`~/.local/share/synadm/debug.log`）；
   不要试图写 `/tmp`（只读）。`TMPDIR=/data/storage/el2/base/files/home/.tmp`。
4. HMDFS 大小写不敏感：包内路径树已加静态冲突校验，新增资源文件时保持全小写目录名（另见 L0m slug 门禁）。
5. 本地未跑真实 Synapse 联调（环境无服务端）。AF_UNIX 链路用本地 unix socket stub 验证了协议层行为；
   若后续有测试 homeserver，建议补一条 `synadm -c <cfg> user list` 对真实 `/_synapse/admin/v2/users` 的联调记录。
6. **为什么状态是 built 而不是 published**：`conan-verify` 的 G1 门禁用字符串判据要求配方含
   `export_sources` 与 `apply_conandata_patches` 两项。本包是纯 Python：没有需要导出的本地源文件
   （配方用 `exports_sources = "conandata.yml"` 属性声明），且**零补丁**，两者都不存在。
   为过闸写两段死代码既不诚实也会污染产物，故按 R27 如实停在 `built`——同仓库内
   `archives/i/interrogate/1.7.0`、`archives/u/update_checker/1.0.1` 两个已合并纯 Python 包情况相同。
   真实验证以 **W3 本地 CI（`ci/conan/build_and_test.sh`，即远端 CI 同源脚本）通过** + `conan create`
   rc=0 为准，证据随包提交在 `reports/w3-local-ci.log`（第 15 行 `RC=0`；第 383-400 行
   `L1a`/`L1b` 用例执行取证、`L1e` 破坏性反向验证通过、`L0_RESULT=pass` / `L1_RESULT=pass` /
   `L2_RESULT=skip` / `L4_RESULT=pass` / `L5_RESULT=pass`）。本地流程状态文件 `.ci-result.json`
   （`exit_code=0`、`log_sha256 d30b6633…368bf52`）按 code-style §24 不入库，仅作 finish/submit 校验用。
   另：`finish` 的 G0 clean-verify（`./configure`）对无 configure 的 Python sdist 必然 exit 127，
   gen_summary 崩溃源于既有 `archives/q/qpdf/12.3.2/manifest.yaml`（与本包无关）。
7. **设备原生环境 ≠ CI worker 沙箱**（PR #15991 首轮 CI 红后修正，教训见图谱草稿
   `knowledge/drafts/E610-draft-A14E.kv`）：鸿蒙套件最初把三处**本机实测**写成断言，远端 CI
   worker 三项都不成立——`sys.platform` 非 linux 前缀、`chmod 0600` 落地为 `0640`（挂载追加
   group 位）、`AF_UNIX bind()` 返回 `EPERM`。三处均已改成：平台前提只锁 `os.name == "posix"`
   并静态证明包内 0 处读 `sys.platform`；权限只锁"other 无访问位 + group 无写/执行位 + owner 可读写"；
   需要监听器的 5 个 socket 用例对候选目录逐个 `bind()` 探测，全失败则 `skipTest(实测 errno)`。
   当前结果：**设备原生 63/63 全绿；CI worker 套件 A 42/42、套件 B 16 PASS + 5 SKIP，rc=0**；
   修复后远端 CI 复跑 **build #93306（SHA `0f23b320`）校验通过**（conan test_package ✅ / L0 ✅ / L1 ✅），
   即"修复有效"已由远端实测闭环（worker 行 16/5 的拆分仍为推算，见 test-report.md §4.5 第 4 条）。
   刻意不用"放宽断言到空"或吞异常换取绿灯——那会让红灯变成静默的零覆盖。
---

**编译结束**: 2026-10-15 18:09
**最终状态**: built
