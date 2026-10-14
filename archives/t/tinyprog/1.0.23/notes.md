# tinyprog 1.0.23 适配笔记

## 编译环境

- 构建系统: setuptools（纯 Python，**无编译步骤**）
- 构建日期: 2026-10-09
- 目标平台: HarmonyOS PC / aarch64（`settings.os=OHOS`、`settings.arch=armv8`）
- 解释器: Python 3.12（`/data/service/hnp/python.org/python_3.12/`）
- conan: 2.29.1（OHOS 适配版，社区源）
- profile: `ci/conan/profiles/ohos-aarch64`（host = build）
- 状态: built（`conan create` 端到端 rc=0；W3 本地 CI 模拟通过；CI 首轮/次轮红的根因均已修，见「CI 首轮失败与修复」「CI 第二轮失败与修复」）

## 编译步骤

tinyprog 是**纯 Python 应用**（setuptools，无 C 扩展），因此**没有编译/交叉编译步骤**，
适配完全是一个打包问题。配方 `build()` 等价于：

```bash
# 1) 上游包本体 —— 依赖由 conan / pip 分别解决，故 --no-deps
python3 -m pip install --no-compile --no-deps --target=<stage> <src>/programmer

# 2) 制品仓无可用配方的运行时依赖（连同其传递依赖）
python3 -m pip install --no-compile --target=<stage> \
  intelhex==2.3.0 jsonmerge==1.9.2 tqdm==4.70.1 pyusb==1.3.1 packaging==26.3 \
  jsonschema==2.6.0          # 传递依赖同样钉死，闭包必须保持纯 Python（见问题 7）

# 3) 闭包门禁：stage 全树不得出现 .so/.pyd/.dylib（出现即失败并点名漂移依赖）

# 4) 布局门禁 + 目标解释器语法门禁
#    断言 stage/tinyprog/、stage/tinyprog-1.0.23.dist-info/、stage/bin/tinyprog 存在
#    compileall 全部 101 个 .py

# 5) 上游测试 census（见 §4）+ 安装后控制台脚本端到端冒烟
```

本地 W3 验证即 `conan create`（finish 内部执行），CI 用同一 profile 复现。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 纯 Python 依赖 `pyserial`/`six` 在消费者环境不可见 | Conan 2 对 `python-require` 依赖默认 `run=False` → `Requirement.files=False` → `graph_binaries._skip_binaries()` 标 `BINARY_SKIP`，节点无 `package_folder`、无 runenv `PYTHONPATH` | `requirements()` 中显式 `self.requires(..., run=True)`（纯 Python 依赖的强制项，非可选优化） |
| 2 | 拼依赖 `PYTHONPATH` 时部分依赖探测不到 | 本仓库纯 Python 配方 payload 布局不统一：`lib/pythonX.Y/site-packages`（packaging 风格）、`lib/python/site-packages`（pyserial/six 实测）、flat 包根 | 写 `_dep_site()` 探测器按序尝试三种布局；**runenv 与 buildenv 都写**（`six/1.17.0` 实测只发布 runenv，构建期消费者看不见） |
| 3 | `self.dependencies` 遍历时抛 `TypeError: expected str ... not NoneType` | 图上存在未解析（无 `package_folder`）的依赖节点 | `_dep_site()` 首行 `if not folder: return None` 空值保护 |
| 4 | `packaging` 无法声明为 conan 依赖 | `packaging/26.3` 配方存在但**不可消费**：`conan install --requires=packaging/26.3` 报 `Invalid: 'settings.os.version' value not defined` | 改为 pip 装配进包内（若声明为 `requires()`，每次 CI 必然全红） |
| 5 | 制品仓是否已有依赖 binary 无法用 `conan list` 判断 | cnb.cool 搜索 API 对 binary 返回不完整（显示 "No packages found" 但实际已上传） | 用 `conan download <name>/<ver> -r=ohpcd --only-recipe` / `conan install --requires=` 实测（R35） |
| 6 | 公网 PyPI 与清华镜像都拉不到依赖 | 本环境仅鸿蒙社区镜像可达（实测） | `_pip()` 固定社区索引 `pypi.cnb.cool`（可用 `OHC_PIP_INDEX` 覆盖） |
| 7 | CI 首轮红：构建期冒烟报 `ImportError: Error loading shared library .../rpds/rpds.cpython-312-aarch64-linux-ohos.so: Permission denied` | 顶层依赖只钉直接 requirement，传递依赖 `jsonschema (>2.4.0)` 交给 resolver；镜像对 `rpds-py` 的可见性逐次不同 → 本地回溯到无依赖的纯 Python `jsonschema 2.6.0`，CI 选中 `>=4.18`（拖入 `referencing`→`rpds-py` 原生扩展）。CI profile 把 `/data/service/hnp/bin` 前置，HNP 进程不能 dlopen 用户存储的 `.so`（E212） | 钉死闭包 `jsonschema==2.6.0`（闭包纯 Python 的最新版），并在 `build()` 加"stage 全树不得含原生扩展"门禁，使漂移在本地而非 CI 暴露（知识 E14725） |

## CI 首轮失败与修复（PR #15147）

| 项 | 内容 |
|----|------|
| 现象 | CI `conan-build-test` 在 build step 失败：``ConanException: `tinyprog --help` failed (rc=1)``（`conanfile.py` 的 `self._smoke(stage)`） |
| 报错 | `ImportError: Error loading shared library <build-release>/stage/rpds/rpds.cpython-312-aarch64-linux-ohos.so: Permission denied` |
| 链路 | `tinyprog/__init__.py:3 import jsonmerge` → `jsonmerge/resolver.py` → `jsonschema` → `referencing` → `rpds`（原生扩展） |
| 根因 | 配方只钉顶层依赖，传递依赖 `jsonschema` 随镜像索引浮动——**同一配方两次解析产物不同**：本地 101 个 `.py` 且零原生扩展，CI 158 个且含原生 `rpds`。CI 里 `python3` 是 profile 前置的 HNP python，按 `uname()` 报 HarmonyOS 走 HNP 分支，**不能 dlopen 用户存储路径的 `.so`**（E212） |
| 修复 | ① `PIP_REQUIRES` 增补 `jsonschema==2.6.0`（`jsonmerge` 只要求 `>2.4.0`，2.6.0 是闭包纯 Python 的最新版；3.x/4.x<4.18 需原生 `pyrsistent`，≥4.18 需原生 `rpds-py`）；② `build()` 新增闭包门禁：stage 全树出现 `.so/.pyd/.dylib` 即失败并点名漂移依赖 |
| 判据 | `find <stage> \( -name '*.so' -o -name '*.so.*' -o -name '*.pyd' \) \| wc -l` = **0**——载荷无原生扩展，运行期 dlopen 无从发生，E212 不可能触发 |
| 复验 | 本地 W3（`conan create` 端到端）重新通过；CI 重新触发复验 |

> 「本地 W3 绿」不等于「CI 绿」：本次两边解析出的依赖闭包不同，根因是**闭包未钉死**。
> 已按知识草稿 E14725 沉淀；修复后同一配方在任何环境都解析出同一份纯 Python 载荷。

## CI 第二轮失败与修复（PR #15147 / build #89823）

| 项 | 内容 |
|----|------|
| 现象 | CI `conan-build-test` 再次在 build step 失败：``ConanException: `tinyprog --help` failed (rc=1)`` |
| 报错 | `ImportError: Sorry: no implementation for your platform ('posix') available`（pyserial 打印 `sys.platform = 'ohos'`、`os.name = 'posix'`） |
| 链路 | `tinyprog/__init__.py` → `from serial.tools.list_ports import comports` → `serial/tools/list_ports.py`（按 `os.name=='posix'` 分派）→ `serial/tools/list_ports_posix.py:114`（按 `sys.platform` 前缀分派，`ohos` 不在已知列表 → 直接 `raise ImportError`） |
| 根因 | **`sys.platform` 在 OHOS 解释器构建间不稳定**：本地/HNP 解释器报 `linux`（命中 `plat[:5]=='linux'` 分支，故本地全绿），而 worker 自带解释器报 `ohos`（未命中任何分支 → 抛错）。pyserial 3.5 是**外部 conan 依赖**（本仓无其配方，W2 单包不能顺带改），无法在其源码内加 `ohos` 分支 |
| 修复 | 随包下发 `sitecustomize.py`：CPython 启动时按 `PYTHONPATH` 自动导入它，在 `sys.platform` 为 `ohos`/`harmonyos` 时把 Linux 端口枚举后端 `serial.tools.list_ports_linux` 注册到 pyserial 分派器要查的 `serial.tools.list_ports_posix` 名下；其它平台零动作。`conanfile.py` 在 `build()` 把该文件拷入 stage（随 `package()` 一起进包），`test_package/test_11` 放宽 `sys.platform` 断言、`test_12` 增加"shim 已生效"断言 |
| 判据 | 模拟 `sys.platform='ohos'` + pyserial 3.5：无 shim 复现 ImportError，有 shim 时 `import serial.tools.list_ports` 成功且 `comports()` 返回 `[]`；`sys.platform='linux'` 时 shim 为 no-op（不注册别名，行为与上游一致） |
| 复验 | 本地 W3（`conan create` 端到端）通过；CI 重新触发复验 |

## 依赖预检（W0）实测口径

用 `conan download` / `conan install`（**不用** `conan list`，R35）逐包实测：

| 上游 requirement | ohpcd 制品仓实测 | 本配方的获得方式 |
|---|---|---|
| pyserial | `pyserial/3.5`，binary 存在 | `requires(run=True)`（conan） |
| six | `six/1.17.0`，binary 存在 | `requires(run=True)`（conan） |
| intelhex | 无已发布配方 | pip 装配 |
| jsonmerge | 无已发布配方 | pip 装配 |
| tqdm | 无已发布配方 | pip 装配 |
| pyusb | 无已发布配方 | pip 装配 |
| packaging | 有配方但**不可消费**（`settings.os.version` 未定义） | pip 装配 |

> 无可用配方的依赖不能在本 PR 内顺带适配——配方 PR 必须原子（W2/PF1，CI JC6 硬拦，
> 同时 `create-pr` 的 PF4 依赖闸会在建 PR 前逐个探测制品仓）。这与 `acstore`/
> `adb-enhanced`/`alot` 采用的 pip 装配方式是同一处理。

## 上游测试与适配测试（census）

**上游没有可运行的 Python 测试套件**——这是实测结论，不是跳过：

- `programmer/README.md` 原文："Tests have been removed for now pending refactoring
  of test methodology"；
- `setup.py` 未声明 `test_suite` / `tests_require`；
- 仓库 `tests/` 目录下只有 Verilog RTL testbench（24 个 `.v`），它们仿真的是
  bootloader **固件**，不驱动本 Python 包，且需要 icarus-verilog 模拟器
  （本 CI 镜像未提供 `iverilog`）——记为环境能力缺口（W0b），不是包本身的失败。

因此本适配**自行提供测试证据**（R34：测试必须实质依赖被测包）：

- `build()` 内 `_run_upstream_tests()` 打印精确 census（Python 测试文件数、RTL 数、
  模拟器可用性），避免用一句 "0 passed" 掩盖"套件被静默跳过"；
- `build()` 内用**目标解释器**对 101 个随包 `.py` 做 `compileall` 语法门禁；
- `build()` 内驱动**已安装的控制台脚本**端到端冒烟（`--help` rc=0；
  `-l` 在无开发板时为 rc=1，这是上游既定行为，改断言其输出含 "TinyProg"）；
- `test_package/` 提供 12 个消费者用例（3 个鸿蒙特有断言），
  完整清单见 `test_package/MANIFEST.yml`。

## 源码修改

**无上游源码改动。** `patches/` 为空——上游零改动，适配全部在配方内完成
（pip 平铺装配 + 依赖补齐 + 随包 `sitecustomize.py` 平台 shim + 消费者侧断言）。
`sitecustomize.py` 是**随包下发的附加载荷文件**（不是对上游源码的补丁），且仅在
`sys.platform` 为 `ohos`/`harmonyos` 时生效——对其它平台完全透明。因此没有平台宏、
没有 stub，不触及 R8 的平台宏约束（与 `cruft` 随包下发 `sitecustomize.py` 同一处理）。

## 平台事实（实测）

| 事实 | 实测值 |
|------|--------|
| `sys.platform` | **不稳定**：HNP 解释器报 `linux`；worker 自带解释器报 `ohos`（其他构建另有 `harmonyos` / `ohos-*`） |
| `os.uname().sysname` | `HarmonyOS` |
| `platform.system()` | `HarmonyOS` |
| 安装布局 | `pip --target` 平铺（`tinyprog/` + `tinyprog-1.0.23.dist-info/` + `bin/tinyprog`） |

> `os.uname()` / `platform.system()` 稳定报 `HarmonyOS`，但 `sys.platform` 随解释器构建而变
> ——依赖它做平台分派的第三方代码（此处是 pyserial 3.5）在 OHOS 上会踩空。适配以随包
> `sitecustomize.py` shim 兜底（见「CI 第二轮失败与修复」）；平台指纹由 `test_package/`
> 断言而非假设（R32 的 `settings.os` 判断在本包无适用点）。

## R49 合规

所有写入均落在 `<self.build_folder>/stage` 私有前缀，`package()` 从该处 copy 到
`package_folder`；**没有**任何对 `/usr/local` 或其他共享前缀的写入（R49 第①禁）。
---

**编译结束**: 2026-10-12 10:35
**最终状态**: built
