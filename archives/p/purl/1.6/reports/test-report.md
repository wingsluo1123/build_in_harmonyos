# purl 1.6 测试报告

验证日期：2026-10-12（Asia/Shanghai）。环境：HarmonyOS HongMeng Kernel 1.12.0 / AArch64，Python 3.12.9，Conan 2.29.1。

## 输入与依赖

- 官方标签 `1.6`：`2bd51cabecfd4dcd20544fba7092cfd98dc7dac0`。
- 源码 SHA256：`7feebbda6e40463096e49bc7ffeccfe644e5db307083d1e323609b8c1682fdd2`。
- `six/1.17.0` 和 `pytest/9.1.1` 的 recipe、binary 通过制品仓下载核验；pytest 的四个运行依赖均下载成功。
- W0 使用 `--build=never`，没有回退构建依赖。原始日志：`w0-dependencies.log`。
- GitHub 标签源码保留全部测试。上游源码、测试和配置均无补丁、无删减。

## 上游完整套件

Conan `build()` 在构建私有 staging 目录执行 `python -m pytest`，采用原版 `pytest.ini`。最终配方使用官方 URL 完整执行 `conan create`，退出码 0；原始日志：`conan-create-device.log`。

| 来源 | 收集数 | 通过 | 失败 | 跳过 |
| --- | ---: | ---: | ---: | ---: |
| tests/test_expansion.py | 68 | 68 | 0 | 0 |
| tests/test_template.py | 2 | 2 | 0 | 0 |
| tests/test_url.py | 96 | 96 | 0 | 0 |
| tests/test_utils.py | 2 | 2 | 0 | 0 |
| README.rst doctest | 1 | 1 | 0 | 0 |
| purl/url.py doctest | 2 | 2 | 0 | 0 |
| 合计 | 171 | 171 | 0 | 0 |

上游测试命令保留文档和模块 doctest。没有 `-k`、ignore、exclude 或 xfail 豁免。

## Conan 消费测试

`test_package/test_purl.py` 使用标准库 unittest，10 项测试、22 个断言全部通过。覆盖安装来源、解析组件、不可变操作、重复查询参数、Unicode 路径、含 @ 的密码、pickle 序列化、保留字符模板、返回 URL 对象和缺失模板变量。

消费测试通过 Conan `VirtualRunEnv` 使用安装包路径；`purl.__file__` 必须位于 `PURL_PACKAGE_ROOT` 中。测试工具 pytest 不进入消费者运行环境。

## 本地 CI 与产物验证

在真机独立 Git 验证副本运行仓库原版 `setup.sh` 和 `build_and_test.sh purl/1.6`；由 `FinishPipeline.step35_local_ci()` 生成成功回执。W3 完整输出为 `w3-local-ci.log`，SHA256：`64ab6c0fe64c237f2285ca185dfec4ff9beb40287c7acd5860bd0c83b291f2da`，与工具生成的 `.ci-result.json` 一致。

- L0/L1/L4/L5：通过；上游完整测试、消费者执行、无补丁和产物存在检查均通过。
- L1e：移走 `lib/` 后消费者失败，恢复后通过。
- L2：跳过，纯 Python 库无 `bin/` 或 CLI。
- 补充负向验证确认具体失败为 `ModuleNotFoundError: No module named 'purl'`，恢复后 10/10 通过。日志为 `negative-device.log`。
- 安装文件仅为 `purl/__init__.py`、`template.py`、`url.py` 和 MIT LICENSE，另有 Conan 管理元数据；不含测试工具、字节码或 ELF。

最终官方 URL 构建的 recipe revision：`80c45428008305aac45a1d36463cee5c`；package ID：`da39a3ee5e6b4b0d3255bfef95601890afd80709`；package revision：`3bccd01dfb70c1aecaa0064969755df7`。W3 脚本临时添加镜像 fallback URL，结束后自动还原官方 URL；最终构建重新验证归档配方及官方源。两次构建的 package revision 相同。

知识图谱验证通过，542 个既有节点检查完成；170 条警告来自已有图谱，本次未修改知识图谱。

## 验证范围

上述结果是实际 HarmonyOS PC 真机执行。旧适配提交的远端 CI #86310 已被机器人记录为通过，原始评论见 `ci-baseline-86310.json`。当前知识更新提交須新 CI 核验，人工审核、合并与 upload 未完成。W3 真机本地 CI 模拟记录在 `w3-local-ci.log`。

## 路径 B 依赖闭包诊断

PyPI purl 1.6 的 `requires_dist=null` 与同版本 setup.py / requires.txt 的 six 声明不一致。静态声明和来源摘要见 `pypi-metadata-evidence.json`。真机 `python -I -S` 中仅提供已安装 purl 路径，明确缺少 six，退出码 1；再提供已发布 six 的安装路径，URL 操作断言通过，退出码 0。原始记录为 `metadata-runtime-closure.log`。

此受控失败用于证明运行依赖必要性，不是既有 CI 构建失败，也不计入上游 171 项或消费者 10 项的分母。知识草稿为 `knowledge/drafts/E429-draft-P16B.kv` / `.md`，候选号和入库由主编确认。
