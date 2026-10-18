# wlc 2.0.0 适配记录

- 本地准备开始：2026-10-16T04:01:56.380484+00:00（固定归档提取回执）。
- 本次本地准备结束：2026-10-16T08:33:49.743532+00:00。此结束只指本地候选和 H1 输入整理，目标适配尚未完成。
- 官方规范基线：e3aaad7dbbf22edf5830f26209e519c82d9111a3；源为 PyPI wlc-2.0.0.tar.gz，SHA256 bd499954d3e27e8bb211d2eb9bb5a91cdd4120ed9d5fb8c273296ff22f97d826。
- 本机：Windows / CPython 3.12.14。目标：OHOS aarch64 / Python 3.12.9，H1-008 原218及消费者、H1-009新增回归分别通过，详见文末。

## 根因与最小修复

`Weblate.list_factory` 每轮把原 params 交给 `get`，同时把 path 改成响应中的完整 next URL。requests 2.32.5 把新参数追加到既有 query。首次 params 为 page=1/q=hello，第二页实际变为 page=2&page=1&q=hello。离线回归真实报 `AssertionError: {'page': ['2', '1'], 'q': ['hello']} != {'page': ['2']}`，并未观察或声称真实 Weblate 服务死循环。

修复只有一次局部 `params = None`，位于首次 get 返回后。首请求过滤/分页参数保持；后续 query 由 next URL 拥有。原 normalize_path/同源/端口/认证逻辑未改，原 URL 验证测试保留。新增 test_pagination.py 的一个方法，使用原 responses 框架和原三页固件，验证首参数、2/3 唯一页码、三请求终止、50 个唯一对象及原输入字典未变。

## 已执行的主机验证

`python -B -m unittest discover -s tests -t . -v`：未修改的上游 218/218；原源码加新回归 0/1（预期失败，证明缺陷）；候选 219/219。9 个原 test_ 模块/177 个静态方法是库存数；218 是 unittest 动态执行数，新增回归后 219，不能混加。

setuptools 84.0.0 从候选源码构建真实 wlc-2.0.0-py3-none-any.whl，pip --no-index --no-deps 安装到私有 venv。一个真实消费者从该安装目录导入，三次本机 HTTP 请求返回 50 个唯一翻译对象，有限终止，PASS。该一个消费者不计为 50 个消费者，三次 HTTP 调用也不计为三个测试。pip check：No broken requirements found。

主机总计：218 个原用例 + 1 个新增回归 + 1 个安装包消费者 = 220 个；测试日志保存在本地 H1 输入索引，未当成目标结果。沙箱 DNS、WSL 权限、ensurepip 临时目录权限、回环 WinError10013 及下载连接重置保留；升级执行或后续成功不改写这些旧失败。未改全局安装、凭据、权限或配置。

## 依赖与交付

运行：requests 2.32.5、argcomplete 3.6.3、python-dateutil 2.9.0.post0、pyxdg 0.28、urllib3 2.5.0、charset-normalizer 3.4.3、idna 3.10、certifi 2025.10.5、six 1.17.0；官方纯 wheel URL/SHA 见 conandata.yml。构建/测试：setuptools84.0.0、responses0.26.0、PyYAML6.0.2。主机 PyYAML cp312 Windows wheel 不进入目标输入。

目标 Conan Python 固定 RREV d8eda770878152bea40b42db9f7024cd，已核精确 package/PREV 供应；PyYAML 测试依赖 RREV 945ede326d62a17c4827815da56bb22e，公开 package ID da39a3ee5e6b4b0d3255bfef95601890afd80709/PREV 9138d3195e5c4d7a235a1ebf40e7ec00 清单已 HTTP200。这是供应证据，非本候选 Conan/H1 通过。

## 知识增量与边界

相对于已实读 cloud-utils IMDS mock、restclient-cpp loopback 测试隔离和 Issue3781 PF10 分页证据完整性，本项是“完整 next URL 与首请求 params 的状态所有权”缺陷。mock/回环只用于证明修复，不以测试隔离本身重复申报知识。不称 OHOS 专属、全球原创或已有第二库成功验证。

## 目标尝试与下一步

H1-003 使用输入版本 `001-fixed43-members`（ZIP SHA256 `0f1997c86aff2b998317c1a196b1fcf1bb72849e9d936f43b1307d283e002eec`），终态回执为 `evidence/h1-003/RESULT.json`（SHA256 `e7fcdb15eb00621b09da23b82c88615641b9240f9f45854173cb24ec6ca254a3`）。正式 `finish` 的 G0 为 Python 源码选择 `./configure` 后返回 127，并记录 getcwd Permission denied；该 CLI/语言入口适用性问题沿已核人工 Python 路径披露，不据此改源码构建系统或系统权限。随后 refresh-patch 仅跟踪 `wlc/client.py`，将两份原补丁备份并生成 client 单补丁，而 `conandata.yml` 仍引用测试补丁；G2/W3 在 export_sources 因 `0001-tests-test_pagination.py.patch` 缺失失败。W3 的 12 项预下载因执行环境缺 curl 未落盘；目标 219 项、目标安装消费者、Conan 包与 W3 后续步骤均未运行。上述真实失败保留，不重跑 H1-003。

恢复方案仅改配方补丁元数据：复用原冻结的 `0001-tests-test_pagination.py.patch`、`0002-wlc-client.py.patch`、源归档、219 用例与单消费者，并给两条 Git 风格补丁显式设置 `strip: 1`，符合 Conan 2 `patch()` 默认 strip 为 0 的接口。下一轮从新私有工作树直接执行受支持的 `conan-verify`/Conan create 与完整 W3，不调用会再次 refresh-patch 的 `finish`；按现有固定 tar 与 `.build-cache/predl_cache` 供应路径复用已有输入，不安装 curl 或 shim。由 W3 内首次实际执行原 219 目标用例和一个安装包消费者；不重跑未变主机套件。目标 W4、AtomCode 与后续发布门槛仍待真实结果。

平台 cpp 标签和 Python 实源差异准确披露，人工入口按既有裁决继续，不改标签、不调用 AI Worker 终态协议。

## H1-007 dependency-graph failure and minimal recipe correction

H1-007 used the unchanged `004-strip1-after-H1-003` input and stopped at Conan G2 dependency-graph evaluation: Conan 2.29.1 raised `TypeError: TestRequirements.__call__() got an unexpected keyword argument 'libs'` at `build_requirements()` line 29. G1 passed; no source/build/test/package/W3 phase ran, so target 219 and the installed consumer remain not run. The raw `conan-create.log` and `conan-verify-report.md` are retained with the H1-007 result.

Conan 2 `test_requires` is a specialized test dependency method and accepts the package reference plus supported `options`/`force` arguments; it sets test-only traits itself. The recipe only needs the pinned PyYAML test dependency, so the minimal correction removes the unsupported `libs=False, run=True` keywords and leaves the exact reference unchanged. The runtime Python `self.requires(..., libs=False, run=True)` call is a different supported method and remains unchanged. The next private continuation reuses input004 plus this small recipe/notes delta, the existing source, dependency cache and host evidence; no host tests are repeated.

本项没有发布租约；领取/撤领/push/PR/Issue/comment/CI/提审均未执行。知识文件存在不等于 B 接受、合入或积分。

## H1-008 target regression path finding

H1-008 completed Conan 2.29.1 verification and official W3 with rc0, but its added regression was created at the source root (`s/test_pagination.py`) rather than `s/tests/test_pagination.py`. Therefore the recorded 218 original cases plus installed consumer remain valid for that candidate; the added regression was not collected or executed. W3 rc0 and the missing target regression are separate facts. The official W3 reported the `wlc --version/--help` issue as non-blocking SKIP/WARNING; this continuation does not expand into that CLI issue.

The regression patch already carries Git's `a/` and `b/` path prefixes. The minimal candidate correction sets only that patch's Conan `strip` to 0; the client patch remains at strip 1. A local zero-change source probe applied the unchanged Git-style patch with `git apply -p1`, confirmed the expected `tests/test_pagination.py` path, matched its bytes to the candidate regression (SHA256 `3cc86703d95d21ebe20368a37eaa203f177368125799d6a872f67cab63cb918a`), and unittest discovery collected 219 cases. This host probe does not establish Conan patch behavior on the target; H1 must confirm the actual Conan `source()` patch path and execute only the added target test.

## H1-009 target supplement completed

H1-008：OHOS aarch64 / Python3.12.9 / Conan2.29.1，原有218/218和一个安装消费者通过（3次请求、50个唯一结果）；正式 Conan create/verify rc0，官方 W3 工具 rc0。H1-008 新增回归因落在 source root 未被收集，原 HOLD 保留。H1-009：官方 Conan source()/apply_conandata_patches rc0，唯一 tests/test_pagination.py 字节正确，新增单测单独1/1 PASS。两批证据共覆盖218个原用例和1个新增回归，不声称一次合跑219；009未重建Conan包或重跑W3。008的 wlc --version/--help 保留官方非阻塞 L2 SKIP/WARNING。

H1-009 RESULT SHA256 `4cf5030abba39ef0c90d79aad983a161e66d23825a8c1cd9ee5daa42324b05f5` 绑定实现候选 `5daf2f12322d8fe08f401b88111d062f12a6a918`。原结果/CLI首次参数拒绝及释放回执均保留。源码、两份patch和运行包代码未再改动，后续仅补证据说明、独立W4及实际PR流程。
