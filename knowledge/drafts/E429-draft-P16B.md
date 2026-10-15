# PyPI 元数据缺失时恢复并验证 Python 运行依赖闭包

本条目总结一种依赖审计模式：`requires_dist=null` 表示 API 没有报告该字段，不能直接判定包无运行依赖。应核对同版本官方声明，再在隔离解释器中证明依赖是否必要。purl 1.6 中，元数据未报告依赖，但 `setup.py` 和 `purl.egg-info/requires.txt` 声明 six；不提供 six 时导入失败，提供 six 后真实 URL 操作成功。

## 草稿状态与来源

- 草稿：`E429-draft-P16B`，对应同名 KV；E429 仅为工具生成的候选号，最终编号与入库由主编确认。
- 作者：2301_79503900。来源：[purl 1.6 PR !15360](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/15360)。
- 验证日期：2026-10-12。平台：HarmonyOS PC AArch64，Python 3.12.9，OHOS Conan 2.29.1。
- 单个独立库案例成功 1 次，修复方案验证失败 0 次；经验比例 1/1，不代表其他库已验证或通用成功率保证。

## 适用范围

适用于 Python 发布元数据不完整、缺少 `Requires-Dist` 或 API 返回 `requires_dist=null`，但有同版本官方源码声明可供核对的依赖审计。可用于 Conan 配方、离线打包与部署前检查。

不推断“所有空列表都一定有依赖”，也不把所有 import 当作运行依赖。标准库、仅测试使用的模块、可选 extra 和环境条件依赖必须分别判断。若声明由动态脚本生成，静态解析不成功应保留未知状态。

## 问题现象与根因

1. 官方 PyPI JSON `https://pypi.org/pypi/purl/1.6/json` 中 `info.requires_dist` 为 null。
2. 同版本 PyPI sdist 的 `setup.py:15` 为 `install_requires=['six']`，`purl.egg-info/requires.txt:1` 为 six。
3. 同版本官方标签源码 `purl/url.py:10` 在模块顶层 `import six`。
4. 在 `python -I -S` 中仅提供已安装 purl 的路径，退出码 1，错误为 `ModuleNotFoundError: No module named 'six'`。

根因是审计输入不完整：API 字段未报告依赖，与源码声明不一致。把“未报告”映射为“零依赖”，会截断真实运行闭包。这里没有把 PyPI 服务故障、Conan 缺包或 Python 标准库兼容问题作为根因。

## 输入与输出

输入：指定版本的官方 PyPI JSON、同版本官方源码或 sdist、目标模块路径、已发布依赖安装路径和目标 Python 解释器。

输出：元数据状态、官方静态声明中的候选运行依赖、与实际 import 的对应关系，以及隔离环境下“缺少该依赖失败、提供该依赖成功”的原始记录。输出是可核验的依赖清单，不是执行 setup.py 的安装结果。

## 使用说明与修复步骤

1. 固定版本和官方来源；把 API 未报告依赖标为未知，保留原始字段。
2. 静态核对 `pyproject.toml`、`setup.cfg`、`setup.py` 和 `*.egg-info/requires.txt`。不要执行陌生 setup.py 来读取字段。
3. 核对顶层 import 与真实 API 的运行路径，区分运行依赖、测试工具和可选 extra。
4. 先用 `conan download --only-recipe` 和 `conan install --build=never` 验证依赖发布与二进制可下载，再固定精确引用。本例为 `six/1.17.0`。
5. 在 Conan 显式声明 six 为运行依赖：`self.requires('six/1.17.0', headers=False, libs=False, run=True)`。pytest 用 `tool_requires`，不进入消费者运行环境。
6. 消费者通过 `VirtualRunEnv` 读取包路径；另外进行隔离导入，不让宿主 site-packages 掩盖缺失依赖。
7. 依赖恢复后执行完整上游套件和真实消费测试，分别记录分母；不通过跳过 ImportError 获得“通过”。

## 可执行示例

读取本例元数据与静态声明，不执行安装脚本：

```python
import ast
import json
from pathlib import Path

metadata = json.loads(Path('pypi-purl-1.6.json').read_text(encoding='utf-8'))
print('API reported:', metadata['info'].get('requires_dist'))
tree = ast.parse(Path('purl-1.6/setup.py').read_text(encoding='utf-8'))
for node in ast.walk(tree):
    if isinstance(node, ast.keyword) and node.arg == 'install_requires':
        print('Upstream declared:', ast.literal_eval(node.value))
```

本例输出 API reported: None / Upstream declared: ['six']。`ast.literal_eval` 仅用于可静态求值的声明；遇到变量、函数或动态表达式，应报错并进入人工核对，不猜测零依赖。

用标准库隔离模式验证依赖必要性；参数为真实安装的 purl site-packages 和 six.py 所在目录：

```sh
python3 -I -S -c 'import sys; sys.path.insert(0, sys.argv[1]); from purl import URL; print(URL("https://example.com"))' "$PURL_SITE"
# 不提供 six：本例退出码 1，明确报 No module named 'six'。

python3 -I -S -c 'import sys; sys.path[:0] = sys.argv[1:3]; from purl import URL; assert str(URL("https://example.com").add_path_segment("a")) == "https://example.com/a"; print("URL_API=pass")' "$PURL_SITE" "$SIX_SITE"
# 提供声明依赖：本例退出码 0，真实 URL API 断言通过。
```

`-I` 忽略外部 Python 环境与用户 site，`-S` 禁止 site 初始化；仅加入两个已验证安装路径。这是受控复现，不删除设备文件，不修改系统 Python。

## purl 案例证据

| 证据 | 实际结果 |
| --- | --- |
| 官方元数据 | `requires_dist=null`，来源及摘录见 `archives/p/purl/1.6/reports/pypi-metadata-evidence.json` |
| 官方声明 | sdist 的 setup.py 与 requires.txt 声明 six，官方标签模块 import six |
| 缺依赖隔离复现 | 退出码 1，缺失模块明确为 six |
| 提供依赖后验证 | 退出码 0，URL 操作真实断言通过 |
| 完整上游套件 | 171/171，100%，零失败、零跳过，含 3 项 doctest |
| Conan 消费者 | 10/10，100%，22 断言，含安装来源验证 |
| 既有远端 CI | #86310 通过；知识更新后的提交须由新 CI 另行核验 |

原始隔离复现：`archives/p/purl/1.6/reports/metadata-runtime-closure.log`。完整构建和消费者日志：`conan-create-device.log`、`w3-local-ci.log`、`negative-device.log`。

## 知识查重与新增价值

查重基线为 2026-10-12 的 origin/main 提交 `01438b6e61889a90d2e9be3d7cff8476b078f7c7`，检索 requires_dist、Requires-Dist、null、metadata、install_requires、six、隔离导入等关键词，并阅读相关条目。

工具预审结果为 `review-similar`，E339/E512 的相似评分均为 0.37，需要人工判断，不是自动判定“无重复”或正式入库通过。下表说明实际根因与新增证据的区别，最终仍由主编审核。

| 已有条目 | 已覆盖 | 本条增量 |
| --- | --- | --- |
| E512 | 系统预装依赖导致本地通过、干净 CI 缺模块 | 从 API 未报告依赖追溯官方声明，用 -I/-S 验证依赖必要性 |
| E339 | 旧 Waf 使用 Python 3.12 已移除的 imp 标准库 | 本条是未声明完整的第三方运行依赖，不是解释器移除标准库 |
| E319 | Python noarch 打包、资源下载、PYTHONPATH | 元数据不完整的依赖审计，不重复 noarch 布局 |
| DRAFT-ohos-dep-version-assert-warn | 依赖版本区间与仓库版本不匹配 | 本条是字段未报告，不是已有区间冲突 |
| DRAFT-rapt-ble-0.1.2-pypi-sdist-no-tests-github-tag-archive | sdist 缺 tests 时回到官方标签 | 直接复用，不作为新增知识申报 |
| DRAFT-multipledispatch-upstream-consumer-test-boundary | 上游与消费者测试分母隔离 | 直接复用，不重复申报 |

本条申请“元数据未报告依赖造成漏报”的诊断与验证方法。目前只验证 purl 一个库的案例；推广范围为同类元数据不完整的包，不声称其他库已完成验证。

## 禁止事项与边界

- 不把 null 转成无依赖，不忽略静态声明与 API 的矛盾。
- 不执行不可信 setup.py，不把所有可选 extra 无条件安装为运行依赖。
- 不以系统预装 six 替代 Conan 声明，不跳过导入失败。
- 不把测试工具或新增消费者用例计入上游测试分母。
- 不把草稿、候选号或路径 B 申请写成正式入库、获批或已获得积分。
- 不修改共享 CI、正式 graph/index 或已有作者的条目；一份 KV/Markdown 对随 purl PR 提交，交主编审核。
