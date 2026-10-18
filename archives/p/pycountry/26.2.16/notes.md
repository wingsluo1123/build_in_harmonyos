# pycountry 26.2.16 适配笔记（HarmonyOS PC / OHOS armv8）

## 一、为什么引入 pycountry

pycountry 是**测试基础设施**，不是终端用户软件。

`archives/x/xkeyboard-config/2.48.1` 的上游套件里，`tests/test_rules_xml.py`
会 `import pycountry` 读 ISO 3166/639 数据，把生成的 rules XML 与 ISO 登记项
交叉校验。pycountry 缺失时 pytest 不会失败，而是把这些用例 **skip** 掉：

| xkeyboard-config 2.48 上游输入 | 实测（本机全量收集 8680 个用例点） |
|---|---|
| 无 xkbcomp、无 pycountry（CI 等价环境） | 4194 passed / 3164 skipped / 1322 deselected |
| 有 pycountry、无 xkbcomp | 5695 passed / 1663 skipped / 1322 deselected |
| xkbcomp + pycountry 齐备 | 8680 passed / 0 failed / 0 skipped |

也就是：pycountry 到位后，**1501 个原本 skip 的 XML 用例开始真实执行**；
与 xkbcomp（1322 项被 `-k "not xkbcomp"` deselect + 1663 项 skip）配套后，
上游全量 8680 用例点可在 CI worker 上全部真跑，不再有 skip/deselect。

## 二、包内容与布局

- 源：PyPI sdist `pycountry-26.2.16.tar.gz`（官方 URL + sha256 见 conandata.yml）
- 内容：`src/pycountry/`——模块（`__init__.py`、`db.py` 等）、ISO JSON 数据库
  （`databases/*.json`）、gettext 翻译目录（`locales/<lang>/LC_MESSAGES/*.mo`，
  实测 163 个语言目录）；共 626 个文件，**纯 Python + 纯数据，无编译、无运行期依赖**
- 布局：安装到 `lib/python3.12/site-packages/pycountry`，并合成
  `pycountry-26.2.16.dist-info/{METADATA,top_level.txt}`，使
  `importlib.metadata.version("pycountry")` 可用（上游套件第 299 行会读分发元数据，
  在源树上这一步必然 PackageNotFoundError）
- 导出：`buildenv_info` / `runenv_info` 均 `prepend_path("PYTHONPATH", site)`，
  `tool_requires("pycountry/26.2.16")` 与普通消费者导入的是同一棵树

## 三、上游自测（测试质量规范层 1）

`build()` 中真实运行上游自带 pytest 套件：

    python3 -m pytest src/pycountry/tests/test_general.py -q --no-header -p no:cacheprovider

- runner 由 `tool_requires("pytest/9.1.1")` 提供（已在制品仓发布，见 pytest 配方）
- 运行目录 `cwd` 设为 staged 的 site-packages，保证测试导入的一定是本包产物，
  而不是宿主上任何一份同名副本（本机 user site 恰有 pycountry，必须屏蔽）

## 四、消费方式（xkeyboard-config 侧，后续 PR）

xkeyboard-config 配方以 `tool_requires("pycountry/26.2.16")` 引入，套件进程即可
`import pycountry`；与 xkbcomp（PR #15222）配套后，上游 8680 个参数化用例点
全部真实执行，`3164 skipped / 1322 deselected` 归零。

## 五、证据与复现

- 源文件 sha256：见 `conandata.yml`（官方 PyPI index 与两个独立镜像的 `#sha256=` 片段
  交叉核验一致，本地下载复算一致）
- 本机 `conan create` 记录：见 `test_package/MANIFEST.yml` 的 `upstream_test_result`
- 输入齐备性对照实验：见 §一 表（xkeyboard-config 2.48 全量 8680 用例点）
