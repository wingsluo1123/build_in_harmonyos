# purl 1.6 适配笔记

## 目标与源码

目标为 codeinthehole/purl 的 Python URL 操作库，版本 1.6。官方 Git 标签 `1.6` 指向 `2bd51cabecfd4dcd20544fba7092cfd98dc7dac0`。

使用官方 GitHub 标签源码，SHA256 为 `7feebbda6e40463096e49bc7ffeccfe644e5db307083d1e323609b8c1682fdd2`。PyPI sdist 不含 `tests/` 和 `pytest.ini`，不能用它声称完成上游全量测试。GitHub 标签源码包含四个测试模块和完整 doctest 配置。上游 Python 源码和测试均未修改。

## W0 依赖与语言预检

`setup.py` 明确声明 `install_requires=['six']`；PyPI JSON 的 `requires_dist=null` 不等于无依赖。Conan 精确依赖为 `six/1.17.0`；上游使用 pytest，因此以 `tool_requires` 声明 `pytest/9.1.1`。

两项依赖已通过 `conan download --only-recipe` 核验；真机 `conan install --build=never` 成功下载 six、pytest 及 pytest 的 iniconfig、packaging、pluggy、pygments 二进制包。未从源码构建依赖，也未向配方引入 pip 下载。

语言预检使用 `lang-preflight purl 1.6 --lang python`，结果为 Python / setuptools / 100% Python 主体源码。

## 配方与环境

- 完整源码复制到构建私有 staging 目录，在该目录执行 `python -m pytest`，保留上游 `pytest.ini` 的 doctest 配置。
- 使用 `no_copy_source=True` 保持源码目录与 staging、generators 目录独立。
- 仅打包 `purl` 三个 `.py` 模块及上游 LICENSE，不打包测试、pytest 或字节码。
- 安装路径为版本无关的 `lib/python/site-packages`；通过 `buildenv_info` / `runenv_info` 传播 `PYTHONPATH`。
- six 显式声明 `headers=False, libs=False, run=True`，用于传播 Python 运行依赖。
- 消费测试检查 `purl.__file__` 位于 `PURL_PACKAGE_ROOT` 内，防止系统已有模块掩盖包产物缺失。
- 纯 Python 包使用 `package_type="unknown"`，避免误用 Conan 插件专用的 `python-require`；不输出 C/C++ 库、头文件或 CLI。
- 清除 package ID 的平台和 ABI 信息，因为包内仅包含跨平台 Python 源码。真实执行验证范围为 OHOS AArch64 / Python 3.12.9。

## 测试与边界

2026-10-12（Asia/Shanghai），在 HarmonyOS HongMeng Kernel 1.12.0 / AArch64，Python 3.12.9 / Conan 2.29.1 上完成最终归档配方的 `conan create`，退出码 0：

- 上游 pytest：171/171，包括 README 与两个源码 doctest，零失败、零跳过。
- 包消费测试：10/10，验证解析、不可变变换、重复查询参数、Unicode、含 @ 密码、pickle、模板展开及导入来源。
- W3 真机本地 CI 模拟通过；L0/L1/L4/L5 通过，L2 因无 CLI 跳过。
- 移走安装包 `lib/` 后导入 purl 明确失败，恢复后 10 项测试全部通过。

W3 验证副本初次因设备缺 bash/git 中止；从已发布 Conan 二进制获取独立工具环境后，取消跟踪验证副本误加入的 `.handoff.json` 并采用仓库原版 `.gitignore`，门禁通过。这些处理均限于独立验证副本，未修改共享 CI 脚本。原始日志按仓库 finish 流程的 `reports/` 约定归档。

设备专用 profile 和独立 Conan 缓存属于验证环境，未修改仓库共享 CI profile。旧适配提交的 CI #86310 已被机器人记录为通过，原始评论见 `reports/ci-baseline-86310.json`。当前知识更新提交须新 CI 核验，人工审核、合并和制品发布未完成；manifest 使用 `built`。

## 最终状态

本地适配与验证结束，状态为 `built`；上游 171 项和消费者 10 项全部通过，W3 与独立审计通过。后续 PR 的远端 CI、审核及发布状态以平台实际结果为准。

## 路径 B 知识总结

本次申报“知识库扩展”，新增 `knowledge/drafts/E429-draft-P16B.kv` / `.md`：PyPI 元数据未报告依赖时，通过官方声明和隔离导入恢复运行依赖闭包。E429 仅为草稿候选号，正式编号与是否入库由主编确认。

purl 1.6 的官方 API 返回 `requires_dist=null`，而同版本 sdist 的 `setup.py` / `requires.txt` 声明 six，官方模块实际 import six。真机 `python -I -S` 中仅提供 purl 时明确缺 six；提供 Conan 缓存中的 six 后，URL 操作断言通过。原始记录见 `reports/metadata-runtime-closure.log`。

已对最新 main 查重：E512/E319 覆盖 Python 运行环境与 noarch 打包；已有 sdist/官方标签及测试分母草稿直接引用。本次增量仅为“未报告依赖造成漏报”的诊断与受控闭包验证，不重复申报上述已有方法。路径 B 按贡献创新候选申请，是否符合赛事范围及获得积分由官方审核。
