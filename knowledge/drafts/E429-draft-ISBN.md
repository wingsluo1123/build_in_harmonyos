# 废弃入口点 API 迁移：插件发现必须做真实 dist-info 回归

状态：E429-draft-ISBN 为工具生成候选，不是正式编号。路径 B / 贡献创新 10 分仅申请候选；官方审核决定资格、编号与入库。只验证 isbnlib 一个库，不外推通用成功率。

## 现象、根因与适用范围

PyPI 3.10.14 的 requires_dist=null；顶层 import isbnlib 可成功，但 registry 延迟导入 pkg_resources 时失败，原版 pytest 收集产生 2 个错误。pkg_resources 是已废弃并在新版 setuptools 移除的运行时 API。见 [setuptools 历史](https://setuptools.pypa.io/en/latest/history.html#v82-0-0) 和 [Python 入口点文档](https://docs.python.org/3/library/importlib.metadata.html#entry-points)。

本方案适用于 Python 3.8+、仅使用入口点 group/name/load 的插件注册器。不适用于需要 pkg_resources 的旧式依赖激活、extras 求解、资源提取或 Python 2 的程序；这些语义不能靠本补丁等价迁移。

## 输入输出与操作

输入：同版本源码、报错路径、插件分组/配置开关清单、已安装包位置。
输出：不再依赖 pkg_resources 的发现函数、保留插件行为的真实分发元数据回归和隔离运行日志。

1. 在新进程中直接导入注册模块，不能仅以顶层 import 作为验证。
2. 核对实际用到的 pkg_resources 语义。本例只用 iter_entry_points(group)，保留 entry.name/entry.load()。
3. 使用标准库 importlib.metadata.entry_points()；新版通过 select(group=...)，旧 mapping 返回通过 get(group, ())。Python 3.8/3.9 分支仅静态兼容，本次实测 3.12.9。
4. 在 TemporaryDirectory 中生成独立模块、METADATA 与 entry_points.txt，覆盖 isbnlib.metadata 和 isbnlib.formatters，并另加不相关组。不得 mock entry_points 后就宣称插件发现成功。
5. 子解释器使用 -I -S，只显式注入被测安装路径与本次 fixture。调用真实 provider，检查 formatter 项；验证两个关闭开关和无插件默认项。
6. 用真实 Conan package payload 重跑；缺包和缺 _data 的负向测试须失败，防止源码或宿主路径冒充安装产物。

## 实际证据与边界

未修复插件用例退出 1，原始收集错误明确 No module named pkg_resources；0001 补丁后真实插件、关闭插件与默认项验证通过。最终 Conan 消费者 15/15，含单独 spawn 与书目跨进程流程；这些不是插件方案的额外独立库案例。失败复现与重复回归不累加成功次数。

完整上游网络服务断言另行保留；本知识修复插件发现，不保证 Google/OpenLibrary/Wikipedia 等服务可用，不以离线子集冒充全量 100%。

## 查重

基线 b5e60d0ad3f16f717baff6ea0c0cb969be16ad27。检索 pkg_resources、iter_entry_points、entry_points、importlib.metadata、dist-info、插件/关闭开关，覆盖正式 graph/doc、operations 与 drafts。
E512 处理隐式第三方运行依赖与干净 CI；E319 处理 noarch/资源惰性；E447 只涉及 nanopb 工具依赖 pkg_resources；purl 的 E429-draft-P16B 处理元数据缺失回溯和缺依赖/补依赖实验。这些不覆盖标准库入口点语义迁移与真实插件分发发现的分组/开关验证。本次增量以此为限，临时目录和 spawn 修复只复用已有知识，不重复申报。
预审工具结论另见本任务结构化查重结果；相近结果须人工判定，不能称已正式入库。

工具预审实际结果：review-similar，E339 相似度 0.43；其根因为 Python 3.12 移除 imp 导致旧 Waf 初始化失败，方案 types.ModuleType 不涵盖插件分组、真实 dist-info 发现或关闭开关验证。本候选须人工判定增量，不宣称无相似。E345(0.17)为 ABI 私有宿主加载模块，亦非 Python 元数据发现。

补充查重：DRAFT-j2cli-0.3.12b-python-cli-contract 覆盖未声明 pkg_resources、CLI/配置契约及 get_distribution 的版本处理；DRAFT-furo-pypi-wheel-asset-package-exemption 覆盖已打包 wheel 资产与 dist-info 入口点发现。二者未覆盖本候选的 iter_entry_points 标准库迁移、两业务分组和关闭开关的真实分发发现回归。
