# DRAFT-souffle-2.5-conan-run-trait-runtime-path
> Conan 运行时工具依赖须 requires(run=True) 才会注入 test_package 的 conanrun PATH，配合上游部分跳过时标记 status=incomplete

## 问题特征（真实日志片段/标记）

test_package case 2 端到端执行时崩溃，依赖图已解析并安装 mcpp/2.7.2 仍报缺预处理器：


libc++abi: terminating due to uncaught exception of type std::runtime_error: failed to locate mcpp or gcc pre-processors


本轮 HMBS_TEST_PACKAGE_RESULT 只通过 case 1：


HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"sh test.sh","discovered":2,"passedCount":1}


修复后两用例全过：


HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"sh test.sh","discovered":2,"passedCount":2}


另一类矛盾证据：上游 ctest 有大量 ohos_feature 缺口却被标 passed：


HMBS_UPSTREAM_TEST_RESULT={"discovered":2468,"executed":36,"passed":36,"failed":0,"skipped":2432,"status":"passed"}


## 根因

1. Conan 2 对普通 `requires` 默认 `run=False`。运行时工具包（此处 `mcpp/2.7.2`，static library，产物 `bin/mcpp`）即使已解析安装，其 `bin/` 也不会被 `VirtualRunEnv` 注入消费者 test_package 的 `conanrun` 运行环境 PATH。souffle CLI 默认（未给 `--no-preprocessor`）在 `MainDriver.cpp` 的 `use_preprocessor` 分支用 `which()` 定位外部 C 预处理器，故 `which("mcpp")` 仍失败并抛同一异常。
2. 上游测试语义：`conanfile.py` 的 `_run_upstream_tests()` 末尾无条件 `_emit_upstream_marker("passed", ...)`。当 2468 项 ctest 中 2432 项因 ohos_feature 缺口（compiled 变体需运行时 C++ 编译器、helper 依赖 gzip/sqlite3）未执行时，98.6% 未执行与 `status=passed` 自相矛盾，触发 rule4「passed 状态与上游结果矛盾」。

## 修复方案（rec）

1. `archives/s/souffle/2.5/conanfile.py` 的 `requirements()` 中把运行时依赖写为 `self.requires("mcpp/2.7.2", run=True)`，使 mcpp 的 `bin/` 进入消费者 `conanrun` PATH，`which("mcpp")` 命中，默认解释执行模式（`interpretTranslationUnit`，无需运行时 C++ 编译器）跑通 case 2。
2. `manifest.yaml` 声明 `runtime: mcpp/2.7.2`，与依赖图一致。
3. `_run_upstream_tests()` 按跳过数区分状态：`skipped>0` 时输出 `status="incomplete"` 并附 `ohos_feature` gaps（`gaps=discovered-executed`）与 reason；仅 `skipped==0` 才输出 `status="passed"`。
4. 同步 `manifest.yaml` 与 `test_package/MANIFEST.yml` 的 `upstream_test_total`，由 2518 修正为真机 `ctest -N` 实测 2468，保持 `discovered`、`executed`、`skipped` 恒等式一致。
5. `test_package/test.sh` 用 `TOTAL`/`PASSED` 计数器，每个真实用例通过才累加，失败经 `fail_test()` 输出 `passed:false` 并非 0 退出，保留全部原有断言。
6. 同步 `notes.md` 与 `.hmbs/pr-body.md` 的真实通过率与 status 语义，避免与真机 marker 矛盾。

验证：等待 HMBS 同步未提交工作树，在真机复跑完整 `conan create`，确认 test_package 以 `passedCount=2` 通过、上游 marker 以 `status=incomplete + ohos_feature gaps` 通过 rule4。

## 禁止策略

- 禁止在 `skipped>0` 时把上游 marker 标为 `status=passed`（`forbid_1_pattern`）。
- 禁止删除或静默跳过 test_package 断言以凑 `passedCount`。
- 禁止把运行时工具依赖仅写成普通 `requires`（缺 `run=True`）后宣称端到端通过。

## 与相近条目的边界（查重）

- `DRAFT-ccrtp-1.0.0-demo-as-upstream-regression`：处理上游无 formal 测试时以 demo 改造新增回归，属「零证据/测试来源」问题；本条处理的是依赖注入 PATH 与「跳过时状态语义」，两者都涉及上游结果门禁但根因不同。
- 平台能力样板类（shell/tmpdir/chmod 等）与异因相邻条目均未覆盖 Conan `run` trait / 运行时依赖 PATH 注入场景，现有技能库无重复。

## 适用判断

适用于 Conan 2 配方中 CLI 端到端 test_package 依赖运行时工具可执行文件（预处理器、解释器、辅助命令）的三方库；以及上游测试套件存在 ohos_feature 缺口、`skipped>0` 需如实标注 `status=incomplete` 的库。判定要点：日志出现 `failed to locate ...` 类运行时缺工具，或上游 marker 出现 `skipped>0` 且 `status=passed` 的矛盾。
