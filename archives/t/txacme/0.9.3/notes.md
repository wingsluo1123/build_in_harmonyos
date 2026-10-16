# txacme 0.9.3 适配笔记

## 软件概述

- 名称/版本：`txacme` / `0.9.3`
- 上游：`mithrandi/txacme`（`Home-page: https://github.com/mithrandi/txacme`）
- 类型：**纯 Python 库**（ACME 协议 / Let's Encrypt 的 Twisted 客户端实现）
- 产物：import 包 `txacme`、`twisted.plugins.txacme_endpoint`、`integration`（无 CLI，R38 不适用）

## 编译环境

- 构建系统：**custom**（无编译；setuptools 打包，源码树 0 个 C/C++/Cython 文件）
- 语言预检：`lang-preflight --lang python` → detected=python（源文件 35 个，python 100%）
- 宿主 Python：3.12.9（`aarch64-linux-ohos`，OHOS PC 运行时；`conan` 2.29.1）
- 环境变量：`CC=clang`、`CXX=clang++`、`TMPDIR=/storage/Users/currentUser/tmp`
- 编译日期：2026-10-14

## 适配步骤

1. `init-build txacme 0.9.3 --url=<PyPI sdist>` 获取上游源码（sha256 校验一致）。
2. `lang-preflight txacme 0.9.3 --src <src> --lang python` → 匹配（python）。
3. `conan-init` 生成配方骨架 → 改写为 `package_type = "python-require"` 纯 Python 打包形式。
4. 安装运行时依赖并运行上游测试 → 定位 Python 3.12 兼容问题 → 打 4 个兼容补丁。
5. `conan-verify` → G0-G4 + L2/L4/L5 全 PASS。
6. `finish txacme 0.9.3 built` → W2 结构 + R36 依赖 + W3 本地 CI 模拟通过，写入 `.ci-result.json`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 嵌套源码误判：把 `docs/` 当源码根提升 | 上游 sdist 顶层无 Makefile/configure，启发式算法误选含 `Makefile` 的 `docs/` | 手工按 `--strip-components=1` 正确解压 `.orig/.work` |
| 2 | `ImportError: cannot import name 'Mapping' from 'collections'` | Python 3.10+ 移除 `collections.Mapping` | 补丁 0002：`from collections.abc import Mapping` |
| 3 | `ImportError: cannot import name '_PY3' from 'twisted.python.compat'` | Twisted ≥ 22.10 移除 `_PY3` 兼容常量 | 补丁 0001/0004：改为 py3 本地常量 `_PY3 = True` |
| 4 | `ModuleNotFoundError: No module named 'service_identity._common'` | service_identity ≥ 24 重构，`_common` 迁至 `hazmat` | 补丁 0003：`from service_identity.hazmat import ...` |
| 5 | pip 安装 `cryptography-50.0.1` 报 `THESE PACKAGES DO NOT MATCH THE HASHES` | OHOS PyPI 镜像该版本 wheel 文件与索引声明的 sha256 不一致（其余版本正常） | 本地约束 `cryptography==49.0.0` 规避（镜像侧问题，非本库问题） |
| 6 | 本地 `conan create` 卡在 `source()` 下载 | 本环境 `files.pythonhosted.org` 不可达（HTTP 000），CI 才有镜像 fallback | 本地以可达的 OHOS 权威镜像临时改写 URL 验证，**完成后还原为官方 URL** |
| 7 | W3 `junk_check` 报 full 模式命中整仓遗留隐藏文件 | 新建分支无 commit → `git diff origin/main...HEAD` 为空 → 退化为 full 整仓扫描 | 用 `JUNK_PR_DIFF` 复现 CI 的 prdiff 范围（等价 CI buildbot 的 pr.diff），JC pass |

## 源码修改（补丁，4 个）

均为 **Python 3.12 / 现代依赖兼容补丁**（非平台宏补丁，无 `__OHOS__` 守卫）：

- `patches/0001-src-integration-test_client.py.patch`：`integration/test_client.py` — 移除 `twisted.python.compat._PY3` 导入，改用本地常量。
- `patches/0002-src-txacme-challenges-_tls.py.patch`：`txacme/challenges/_tls.py` — `collections.Mapping` → `collections.abc.Mapping`。
- `patches/0003-src-txacme-test-matchers.py.patch`：`txacme/test/matchers.py` — `service_identity._common` → `service_identity.hazmat`。
- `patches/0004-src-txacme-test-test_client.py.patch`：`txacme/test/test_client.py` — 同 0001。

> 未改动任何生成文件、未改动上游功能逻辑；补丁仅为在当前 OHOS Python 3.12 运行时所必需。

## 依赖版本

- conan 依赖：**无**（`requirements()` 为空）。txacme 的全部依赖为 PyPI 包，在 OHOS 制品仓无对应 conan 配方，由 pip 在消费者环境提供：
  `acme(0.40.1) / attrs(26.1.0) / eliot(1.18.0) / josepy(2.2.0) / pem(23.1.0) / treq(26.7.0) / twisted[tls](26.4.0) / txsni(0.2.0) / pyopenssl(26.4.0)`，
  测试期：`fixtures(4.3.2) / hypothesis(4.57.1,<5) / testrepository(0.0.22) / testscenarios(0.7.0) / testtools(2.9.1) / service_identity(26.1.0)`。
- 依赖结论（依赖分析阶段）：强制第三方依赖数量 **N=0**（无原生 C/C++ 依赖需独立适配仓；OpenSSL 由 wheel/宿主 Python 提供）。

## 验证结果

- 上游测试（`trial`，OHOS PC Python 3.12.9）：**109 tests, 99 passed, 10 skipped, 0 failed**（详见 `reports/test-report.md`）
- `conan-verify`：G0/G1/G2/G3/G4/L2/L4/L5 全 PASS，可标记 `published`
- W3 本地 CI 模拟：JC/KC/L0/L1/L4/L5 全通过，Pass rate 100%（日志 `reports/w3-local-ci.log`）
- `conan create`：成功（应用 4 补丁，打包 47 个 `.py`；test_package 在 `ohos aarch64` 通过）

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | `package_type=python-require` 配方，打包 import 包 + 上游测试源码 |
| `conandata.yml` | 官方 sdist URL + sha256 + 4 个补丁声明 |
| `patches/0001-0004` | Python 3.12 / 现代依赖兼容补丁 |
| `test_package/` | 消费者冒烟 + HarmonyOS 特有用例 + 上游 trial 重跑（best-effort） |

## 注意事项

- `requirements()` 故意留空：这些 Python 依赖没有 conan 配方，声明它们会被 CI 的 PF4 依赖闸拦截；运行期由 pip 提供（OHOS 社区 PyPI 索引可安装）。
- 本地验证时源码 URL 临时改用 OHOS 镜像（`files.pythonhosted.org` 在本机不可达）；提交的 `conandata.yml` 保持**官方 URL**，CI 侧由 build_and_test.sh 的 mirror fallback 处理。
- OHOS PyPI 镜像 `cryptography-50.0.1` 的 wheel 与索引 sha256 不一致，安装时请约束其它版本。
