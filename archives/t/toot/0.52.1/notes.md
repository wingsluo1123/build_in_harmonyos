# toot 0.52.1 — 适配笔记

纯 Python 应用（无 C/C++ 编译步骤），全部适配工作发生在打包期。

## 1. 关键坑：动态版本 ← setuptools_scm

上游 `pyproject.toml` 声明 `[build-system] requires = ["setuptools>=64",
"setuptools_scm>=8"]`，且 **version 是 dynamic**（`[tool.setuptools_scm]` 为空段，
由 git 元数据推导）。PyPI 的 sdist 不含 `.git`，因此：

```
python3 -m pip install --target=<dir> toot-0.52.1.tar.gz
→ <dir>/toot-0.0.0.dist-info/          # 版本退化为 0.0.0
→ toot.__version__ == "0.0.0"
```

**实测复现**（`$HOME/ohc-tmp/t20`、`t21`，两条构建路径均如此）：
默认 build isolation 与 `--no-build-isolation`（预装 setuptools_scm）都产出
`toot-0.0.0`。

**修法**：构建期注入 `SETUPTOOLS_SCM_PRETEND_VERSION=0.52.1`，产物变为
`toot-0.52.1.dist-info`，`bin/toot --version` 输出 `toot v0.52.1`。

> 这是本适配最容易被静默破坏的点 —— 版本号退化不会让构建失败，只会产出
> 一个版本错误的包。`test_package/test_toot.py` 的 G1/H2/H2b 三条断言专门
> 守住它（H2 明确断言版本 "非 0.0.0"）。

## 2. 依赖边界

上游 `requires_dist`（8 项）：

| 依赖 | 约束 | 制品仓 | 处理 |
|---|---|---|---|
| beautifulsoup4 | <5.0,>=4.5.0 | 4.15.0 ✅ | conan requires |
| click | ~=8.1 | 8.4.2 ✅ | conan requires |
| python-dateutil | <3.0,>=2.8.1 | 2.9.0.post0 ✅ | conan requires |
| requests | <3.0,>=2.13 | 2.22.0 ✅ | conan requires |
| wcwidth | >=0.1.7 | 0.2.12 ✅ | conan requires |
| urwid | ~=3.0 | ❌ 无配方 | pip 填入 |
| tomlkit | <1.0,>=0.10.0 | ❌ 无配方 | pip 填入 |
| pysocks | >=1.7.1 | ❌ 无配方 | pip 填入 |

制品仓探测口径（R35：禁用 `conan list` 判 binary）：`conan download <pkg> -r=ohpcd
--only-recipe`。对照实验——不存在的包返回 `error:system acceleration policy not
enabled`，据此区分"不存在"与"存在但无 binary"。urwid/tomlkit/pysocks 三者均无
配方，`conan-install --requires=urwid/3.0.2` 直接报错。

**urwid 必须锁 3.0.2**：urwid 3.0.5 的依赖是 `wcwidth>=0.4`，而制品仓只有
`wcwidth/0.2.12` → `tests/tui/test_rich_text.py::test_url_to_widget` 报
`AttributeError`（实测 1 failed / 35 passed）。降到 3.0.2（依赖无下界）后
**全绿**。

W2 单包闸（PF1）：配方 PR 不得捎带其他包目录，故 urwid/tomlkit/pysocks 不走
"先适配再发布依赖"，改为构建期 pip 装入包内 —— 与 `acstore` / `adb-enhanced`
/ `alot` 同法。

## 3. Conan 2 陷阱：`python-require` 传递依赖被 BINARY_SKIP ⭐

这是本次适配排查耗时最长的点，值得单独记录。

**现象**：`conan create` 时 `test_package` 的 `test()` 报
`ModuleNotFoundError: No module named 'chardet'`（随后 idna/urllib3/six/
soupsieve/typing-extensions 同类），`11/13 通过`（当轮 13 条断言；§8 增补 H6 后
为 14 条）。

**证据链**：

1. `conan create` 日志 `Skipped binaries` 列出 **9 个包**：beautifulsoup4、
   chardet、idna、python-dateutil、six、soupsieve、typing-extensions、
   urllib3、wcwidth。
2. 生成的 `test_package/conanrunenv-release-armv8.sh` 里 `PYTHONPATH` **只有**
   click / requests / certifi / toot 四条路径 —— 被跳过的包不产生
   `runenv` 路径。
3. **外部真实消费者同样如此**：`conan install --requires=toot/0.52.1` 也把这
   9 个包标为 Skipped。所以这不是 test_package 的问题，而是**真实的打包缺陷**
   —— 用户装完 toot 后 `import requests` 会失败。

**根因**（读 Conan 2 源码定位）：

`conan/internal/model/requires.py` 的 `Requirement.process_package_type()`
按**依赖包自身**的 `package_type` 强制 traits：

```python
if pkg_type == PackageType.APP:      # application
    ... set_if_none("run", True)
elif pkg_type == PackageType.SHARED: # shared-library
    ... set_if_none("run", True)
elif pkg_type == PackageType.STATIC: # static-library
    ... set_if_none("run", False)
...
```

该 if/elif 链**没有 `PackageType.PYTHON`（`python-require`）分支**。于是纯
Python 依赖的 `Requirement.run` 保持默认 `None → False`，`Requirement.files`
（= `headers or libs or run or build`）为 False，最终在
`conan/internal/graph/graph_binaries.py::_skip_binaries` 的

```python
if req.files or (req.direct and is_consumer):
```

处不被计入 `required_nodes` → 标 `BINARY_SKIP` → 无 `package_folder`、无
runenv PYTHONPATH。（`no_skip` 是 Conan 的另一逃生口，但它作用在
`transitive_deps` 上，需运行时 conf，不适用于配方。）

**为什么 toot 直接在 `requirements()` 里写 `run=True` 不够**：`run=True` 只对
toot 的**直接**依赖生效，并且 `transform_downstream` 不会把 `run` 自动传播给
传递依赖。所以 6 个**传递**运行时依赖（chardet/idna/urllib3/six/soupsieve/
typing-extensions）仍然被跳过。

**修法**：在 toot 配方的 `requirements()` 中把这 6 个传递运行时依赖**显式提升
为直接依赖**并带 `run=True`。它们进入 toot 自身的 `transitive_deps` 后
`files` 为 True，节点得以保留。

**验证**（每次改动后重抓 graph，注意用带 user/channel 的完整引用，否则会命中
缓存里无 user/channel 的旧 revision）：

```
conan graph info --requires=toot/0.52.1@ohpcd/stable -pr:a=<ohos profile> \
    --format=json
```

| 阶段 | Skipped 节点数 |
|---|---|
| 初始（5 直接依赖，无 `run=True`） | 9 |
| toot 直接依赖加 `run=True` | 6（6 个传递依赖仍被跳过） |
| 6 个传递依赖提升为直接依赖 | **0** |

> **踩坑提醒**：中途曾依据一份**过期**的 `conan graph info` 输出（revision
> `bf37eb4b…`，来自 `run=True` 之前的导出）得出"`run=True` 完全无效"的错误
> 结论，白白多花了一轮排查。**判定前务必确认 graph 用的是当前导出的
> revision**（`conan export` 后 revision 会变，如本次为 `e896a167…`）。

## 4. 上游测试套件的依赖面

`tests/` 的第三方 import 面：`PIL.Image`（`tests/test_utils.py:10`，模块级）、
`urwid`（`Divider`/`Filler`/`Pile`）、`click.testing`（`CliRunner`/`Result`）、
`pytest`、`pytest-asyncio`。`tests/utils.py` 只提供 `run_with_retries(fn)`
（失败重试，退避至 ~6s）。

**PIL 是 31/36 个通过用例的硬前提**：`tests/test_utils.py` 有 31 个用例，而
忽略该文件时整个套件只剩 **5 passed / 116 skipped**。配方里 `_pil_site()` 显式
探测 PIL 可用性，不可用时**打印警告**而非静默丢弃该文件。

本机 `pillow 11.0.0` 可用（宿主 site-packages，走系统 `.cpython-312.so` 后缀）；
CI worker 没有它，必须由配方在构建期装入。ohos wheel 携带
`_imaging.cpython-312-aarch64-linux-ohos.so`，不在解释器
`EXTENSION_SUFFIXES`（`['.cpython-312.so', '.abi3.so', '.so']`）内 —— **只删
`-linux-ohos` 会留下 `-aarch64`，依然不可导入**，必须重写为本解释器自身的
cpython 标签（实现见 §8.3）。`images` 虽是上游可选 extra，但
`tests/test_utils.py` 在模块级就 `from PIL import Image`，所以**要"上游测试全部
执行"就必须提供 PIL**，不能靠 `--ignore` 裁掉该文件。

**测试结果**：`152 collected → 150 passed / 0 failed / 2 skipped`（执行覆盖率
152/152）。上一版的 `36 passed / 116 skipped` 是因为 114 个集成用例被
`TOOT_TEST_BASE_URL` 门控跳过；本轮为它们实现了自带 API 桩服务，见 §4.1。

仅剩的 2 个 skip 是上游自己写在函数体第一行的
`pytest.skip("TODO: fix mocking")`（`tests/test_config.py:63`、`:110`），上游 CI
同样跳过，本适配不改上游测试源码，故原样保留。

**click 版本也是执行率问题**：集成测试读 `Result.stderr`，click 8.1.x 的
`CliRunner()` 默认 `mix_stderr=True` → 取 `.stderr` 抛
`ValueError: stderr not separately captured`，`tests/integration/test_auth.py`
会有 7 条用例假失败。click 8.2 起移除该参数。配方锁 `click/8.4.2`（落在上游
`~=8.1` 区间内）实测 13/13 通过；若哪天制品仓版本回落到 8.1.x，这 7 条会以
`ValueError` 失败而非真实回归，务必先查 click 版本。

### 4.1 自带 Mastodon API 桩服务（`test_support/mastodon_api_stub.py`）

`tests/integration/` 的 114 个用例把 CLI 子命令打到"一个真实的 Mastodon 实例"
上。真 Mastodon 是 Rails 应用 + PostgreSQL + Redis + Elasticsearch +
Node/yarn，HarmonyOS PC 与 CI worker 上这五样都没有（也没有 docker/podman），
公共实例又不可复现、需凭据、依赖外网。因此采用本仓库**已合并的先例**：
`restclient-cpp/0.5.3` 的 `files/loopback_httpbin.py`、`libetebase/0.5.8` 的
`etebase_stub_server.py` —— 用纯 stdlib 实现一个有状态的 REST 桩服务，让用例
真实收发 HTTP，而不是 mock `toot.http`。

坑（每条都是实现里必须精确对上的地方）：

1. **地址与端口写死**：`tests/integration/test_auth.py:90,99-100,106,127,
   136-137` 断言字面量 `http://localhost:3000` 与 `app.instance ==
   "localhost:3000"`。桩把 `/api/v1/instance` 的 `uri` 回写成请求的 `Host`
   头，于是 `TOOT_TEST_BASE_URL` 用什么宿主都自洽；端口必须 3000。
2. **时间戳格式**：`toot.entities` 用 `parse_datetime` 宽容解析，但上游测试
   自己 `strptime(..., "%Y-%m-%dT%H:%M:%S.%fZ")`，故输出的时间串必须带 6 位
   小数和字面 `Z`。
3. **分页 Link 头**：`toot.http._next_path` 用正则要求 `rel="next"` 出现在
   `<…>` 之后**且该 link 行以 `<` 开头**，所以 `next` 必须排在 `prev` 之前，
   且只在真有后续条目时发出（否则 `toot timeline` 会无限翻页）。
4. **布尔查询参数**：Mastodon 把 `exclude_replies=True` 这类值以字符串传输，
   上游测试断言过滤生效，需按 `"True"/"true"/"1"` 判真。
5. **错误文案逐字**：`Record not found`（→ `NotFoundError`）、`Record
   invalid`、`You have already voted on this poll`（多选投单选时也返回这句）、
   `The chosen vote option does not exist`、`Invalid email or password.`
   （`error_description`）。toot 把 `ApiError` 子类化自 `click.ClickException`，
   测试断言的是 `Error: <原文>`，文案差一个字符就红。
6. **媒体元数据**：`tests/assets/small.png` 的宽高要真从 PNG IHDR
   （`struct.unpack(">II", payload[16:24])`）解析；`small.webm` 测试断言
   `duration==5.0 / 560x320`，桩里按 ffmpeg 实测值硬编码并注明来源。
7. **一次登录一个新 token**：`toot auth` 流程会在重登后写新 token，桩若复用
   token 会让 `test_relogin` 类用例看不出差别。
8. **`display_name` 默认必须是空串**：`test_accounts` 断言
   `stdout == "Accounts:\n* @<username>"`，任何自动填充的显示名都会破坏它。
9. **空时间线恰好一条分隔线**：`print_timeline()` 的分隔线在循环体内，0 条
   状态时只剩表头分隔线 → 断言 `stdout.strip() == "─" * 80`。
10. **调度状态**：`scheduled_at` 解析失败要回 422 `Record invalid`；成功时
    **不得**立即发布，且 `GET /api/v1/scheduled_statuses` 要按 5 秒内排序返回
    8 条（`test_post_scheduled_in`）。

工程约束：桩只在 `build()` 期间存活（`Popen` → 轮询 `/api/v1/instance` 直到
200 → 跑 pytest → `terminate()`），`--verbose` 的访问日志落在
`<build_folder>/build-release/testlogs/mastodon_api_stub.log`，构建日志打印
`stub server served N API request(s)` 作为"集成用例真的打过网络"的留痕；
`export_sources()` 导出、`package()` 从 `stage` 拷贝，所以桩**不进包**
（产物仍是 129 个 `.py`）。

## 5. 无补丁

`patches: []`。纯 Python 包不需要改上游源码，HarmonyOS 适配完全由构建期环境
变量（`SETUPTOOLS_SCM_PRETEND_VERSION`）承担。配方中保留
`apply_conandata_patches(self)` 调用（空列表 → no-op），维持标准配方形态，便于
后续需要补丁时直接加 `conandata.yml`。

## 6. 平台与环境

- 平台：HarmonyOS PC aarch64，`HongMeng Kernel 1.13.0`、`platform.system() ==
  "HarmonyOS"`；`sys.platform` 因解释器来源而异 —— 本机 python.org 构建报
  `"linux"`，CI worker 上设备自带 hnp 解释器报 `"ohos"`。两种都是鸿蒙真实上报，
  断言与配方判定必须同时接受（R32）。
- 解释器：hnp `python3.12`（`/data/service/hnp/python.org/python_3.12/bin/python3.12`）。
- 配方 `settings = "os", "arch", "compiler", "build_type"`，`package_type =
  "application"`，不设 `settings.os` 分支 —— 纯 Python 负载各平台一致，
  也避免了 `== "Linux"` 与 OHOS 的判定陷阱（R32）。
- 平铺安装（`pip --target`）：`toot/` 与 `toot-0.52.1.dist-info/` 直接落在包根，
  `cpp_info.bindirs = ["bin"]`，`runenv_info` 注入 `PYTHONPATH`。
- R49：构建装入 `<build_folder>/stage`，`package()` 从 stage 拷贝，不写任何共享
  前缀（`/usr/local` 等）。

## 7. 构建产物

`conan create` 日志（`reports/conan-create.log`）：打包 129 个 `.py`、1 个 `.css`、
1 个 `.js`、26 个文件（含 `bin/toot`）、4 个 `.txt`、2 个 `.md`、1 个 `.json`、
1 个 `.typed`、1 个 `.pyc`。

`WARN: deprecated ... 'env_info' used in: soupsieve/2.4.1, chardet/5.2.0` ——
依赖配方残留 Conan 1.x `self.env_info.PYTHONPATH`（Conan 2 下无效），这正是
第 3 节问题中 "依赖不导出 runenv PYTHONPATH" 的原因之一；本包通过
`package_info()` 自行注入全部依赖路径规避，无需改动依赖配方（W2）。

## 8. 首轮 CI 失败与修复（PR #15046，build #84757）

平台 CI 在 `conan-build-test` 失败：`test_package` rc=1，14 条中 **4 条不过**
（G4a / G4b / H5 + H3），且上游套件只跑出 **5 passed / 116 skipped**。三处根因
全部落在 toot 自己的配方/测试内，未改任何依赖包配方。

### 8.1 子进程 PYTHONPATH 被覆盖（G4a/G4b/H5）

`test_toot.py` 原先写 `env["PYTHONPATH"] = pkg`，把 `conanrun` 注入的依赖路径
整条丢弃。原注释"conanrun 的 PYTHONPATH 只影响子进程，脚本自身不会继承"是**错误
判断** —— `conanrun` 确实导出了完整依赖路径（实测 17 条，click 在内），覆盖它
才是缺陷本身。

开发机看不出问题（宿主 site-packages 自带 click），CI worker 的解释器没有 click
→ `ModuleNotFoundError: No module named 'click'`。精确复现：

```
PYTHONPATH=<pkg>            python3 -S bin/toot --version  → rc=1 (No module named 'click')
PYTHONPATH=<conanrun 全量>  python3 -S bin/toot --version  → rc=0 (toot v0.52.1)
```

修法：`_consumer_env()` 把包根排第一位、**保留全部继承的依赖条目**；新增 **H6**
断言（`python -S` 下仍可运行）固化该判别条件。`-S` 不加载 site-packages，所以
H6 通过 ⇒ 依赖更全的 CI 环境必然通过。

### 8.2 平台指纹写死 `linux`（H3）

CI worker 报 `sys.platform='ohos'`，本机报 `'linux'`。断言改为
`sys.platform in ("linux", "ohos")`（R32 同口径）。

### 8.3 PIL 装不上 + 后缀不匹配（上游套件被裁剪）

CI 日志：

```
WARN: pillow via ohos wheel unavailable: pip install failed (rc=1) for pillow:
ERROR: When restricting platform ... either --no-deps must be set,
       or --only-binary=:all: must be set and --no-binary must not be set.
WARN: PIL unavailable: tests/test_utils.py cannot be collected
→ upstream suite result: 5 passed, 116 skipped
```

① `_pil_site()` 第 2 档用 `--platform ohos_aarch64` 却缺 `--only-binary=:all:`
→ pip 直接拒绝，wheel 根本装不上；② 即便装上，后缀也不合法（见 §4）。

独立验证（本地 tier-1 命中宿主 PIL 会短路，`conan create` 不会走到该分支，
所以必须单独验证，否则 CI 上仍然是坏的）：

| 阶段 | 结果 |
|---|---|
| 装 OHOS wheel 后、改名前 | 8 个 `.so` → `ImportError: cannot import name '_imaging'` |
| 改名后 | 8 个 → `.cpython-312.so` → `PIL OK 12.3.0` |
| 回归守卫 | 只改 1 个（`cpython-312` 外来标签）；`cpython-311` 异版、`.abi3`、已合法名均未被动 |

修法：第 2 档补 `--only-binary=:all:`；新增 `_normalise_extension_suffixes()`，
用锚定 `major.minor` 的正则按本解释器标签重写后缀。PIL 恢复后
`tests/test_utils.py` 重新参与收集，CI 与本地一致跑满
**36 passed / 116 skipped**，不再需要 `--ignore`。
---

**编译结束**: 2026-10-12 10:53
**最终状态**: built
