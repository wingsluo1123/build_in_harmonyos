# kitchen 1.2.6 适配笔记

## 软件信息
- **版本**: 1.2.6 (2019-05-15 最后更新)
- **类型**: 纯 Python 库（setuptools，Python 2/3 双布局 `kitchen2/` + `kitchen3/`）
- **用途**: Unicode/文本转换、i18n 工具集合

## 依赖
- **运行时**: 无外部依赖
- **测试**: 上游用 nose 1.3.7 驱动；该版本为 Python 2 语法（`core.py` 仍用
  `print` 语句），在 Python 3.12 下 **导入即 `SyntaxError`**，不是
  `ModuleNotFoundError`。因此不能靠“装个 nose”解决，改为声明式垫片补丁。

## 全部适配改动都以补丁形式声明（见 `conandata.yml`）

| 补丁 | 内容 | 为什么必须 |
|------|------|-----------|
| 0001 | `i18n` 输出编码：libc 无 `pt_BR.iso88591` 时按 `LC_ALL` 推导请求编码 | HarmonyOS 无该 locale，`getpreferredencoding()` 恒为 UTF-8，Latin-1 断言失败（实测 6 例） |
| 0002 | `text/display.py` 组合字符宽度表按运行解释器自带数据库重建 | 内置表停留在 Unicode 12，新组合字符被判宽度 1（实测 1 例） |
| 0003 | 补跑 nose 专属测试定义的执行器 + 用例数下限闸门 | unittest discovery 看不到生成器形 `test_*` 方法、plain `object` 测试类，否则这些用例被静默丢弃 |
| 0004 | 最小 `nose.tools` / `nose.plugins.skip` 垫片 | 上游测试源码零改写即可运行（只用到 6 个断言函数 + `SkipTest`，共 7 个符号） |

`build()` 不再在 `pip install` 前改写源码树：制品 = 干净上游 tarball + 上述声明补丁，
可复核、可复现。

### 补丁书写坑（本包实际踩到）

新建文件的补丁**必须**用 `/dev/null` 作为 `---` 侧标签：

```
--- /dev/null
+++ b/kitchen3/tests/nose/tools.py
@@ -0,0 +1,57 @@
```

写成 `--- a/<new-path>` 时，GNU `patch -p1` 会因为 hunk 头 `-0,0` 而**成功**创建文件，
但 Conan 实际使用的解析器 `patch_ng` 只在 `---` 行含 `dev/null` 时才走“新建文件”
分支，否则报 `source/target file does not exist` 而构建失败。因此本地验证补丁必须
用 `patch_ng.fromfile(...).apply(strip=0, root=<tree>)`（Conan 的默认 strip 为 0），
不能只用 `patch -p1`。

## 测试结果（数字均取自 `reports/w3-local-ci.log`）

- **上游测试定义总数**: 366（`kitchen2/tests` 239 + `kitchen3/tests` 127）
- **kitchen3**: **127/127 个定义全部执行**
  - 命令 1 `unittest discover`：`Ran 126 tests` → 123 通过 + 3 跳过（可选依赖
    `chardet` 未安装，上游 `skipUnless` 行为）+ 0 失败
  - 命令 2 补跑执行器：`ran=464 unexpected_failures=0 known_drift=3`，覆盖全部 26 个
    nose 专属定义
  - 两组定义互不重叠，故定义覆盖 = 101 + 26 = 127；实际执行用例 = 126 + 464 = 590
- **kitchen2**: 239 项**未执行**并如实披露：Python 2 专用套件，本机与 CI 均无
  Python 2 解释器。2to3 路线实测不可行（转换后导入即
  `TypeError: decoding str is not supported`，加配方修复后仍
  `NameError: name 'set' is not defined`），已停止，不伪报通过。
- **3 条 known drift（CPython 3.12 差异，非适配缺陷）**：`__warningregistry__` 被注入
  模块命名空间导致 `__all__` 断言漂移 2 例；stdlib 3.10 起新增
  `b32hexencode/b32hexdecode` 导致 1 例。处置为**精确白名单 xfail**，并反向验证
  新失败仍会让构建失败（不会掩盖新问题）。
- **消费者测试**: 8/8 通过（含鸿蒙特有测试），直接用 `package_folder` +
  `PYTHONPATH` 导入已安装制品。

## CI 真实构建首轮失败与修复（2026-10-12，build #84754）

CI 基础设施恢复后，本 PR 首次真正进入 `build()`，立刻暴露一处**本地/CI 解释器差异**：

```
RUN: python3 -m pip wheel . --no-deps --no-build-isolation -w .../wheels
pip._vendor.pyproject_hooks._impl.BackendUnavailable: Cannot import 'setuptools.build_meta'
```

- **根因**：CI worker 的构建解释器（`/data/service/hnp/bin/python3`）只有 pip、
  **没有 setuptools**（Python 3.12 起解释器不再附带 setuptools）；而本地 conan 跑在
  `/data/service/hnp/python.org/python_3.12/bin/python3.12` 上，该解释器**带** setuptools。
  于是本地 W3 一直绿、CI 一进真实构建即红——`--no-build-isolation` 禁止 pip 自建构建环境，
  PEP 517 后端便无从导入。
- **修复**（`conanfile.py` `build()`）：构建前探测解释器是否 `import setuptools`——
  能 → 保留 `--no-build-isolation`（不联网、本地行为逐字不变）；不能 → 去掉该参数，让 pip
  自建**隔离构建环境**（setuptools 装入临时 venv，不污染 worker 共享解释器）。
  构建日志会打印实际分支，便于 CI 侧复核。
- **验证（CI 同构环境）**：`python3 -m venv` 造出与 worker 同构的 3.12.8 无 setuptools
  解释器，用它当构建解释器跑真实 `conan create`（profile 与 CI 相同）：

  ```
  building wheel with <venv>/bin/python: setuptools missing (isolated build env)
  Installing build dependencies: finished with status 'done'
  Ran 126 tests in 4.954s / OK (skipped=3)
  extra upstream cases: ran=464 unexpected_failures=0 known_drift=3
  === All 8 tests PASSED (including 1 OHOS-specific test) ===
  ```

  结果 `RC=0`，上游测试与 test_package 结论与本地 W3 完全一致。

  > 复现说明：`conan` 本机只装在系统解释器上，而 venv 内装不上（社区源缺 `PyYAML`）。
  > 因此该次端到端验证使用配方的**逐字副本**，仅把第 99 行 `sys.executable` 改为可注入
  > （`os.environ.get("KC_E2E_PYTHON", sys.executable)`）以指定构建解释器，
  > 其余部分（含本次修复）与被提交配方完全一致；提交进 PR 的配方仍是 `sys.executable`。

## 本地验证环境坑（与配方无关，但会挡住 W3）

本机 `/tmp` 只读，而 W3 用 **zsh** 执行 `ci/conan/build_and_test.sh`；zsh 的
here-document 临时文件只认 `TMPPREFIX`（默认 `/tmp/zsh`），**不看 `TMPDIR`**，于是
报 `can't create temp file for here document: read-only file system`，被误呈现为
`L0i: conanfile.py AST 解析失败`。解法：

```bash
TMPPREFIX=$HOME/tmp/zsh TMPDIR=$HOME/tmp zsh ci/conan/build_and_test.sh kitchen/1.2.6
```

CI 的干净环境不受影响。

## 适配要点
1. 纯 Python 包：`pip wheel` 构建后用 `pip install --target=... --no-compile` 安装
   （`--no-compile` 使 `__pycache__/*.pyc` 不进制品）
2. `package_info` 里 `runenv_info.append_path("PYTHONPATH", package_folder)`，消费者
   直接可用
3. `validate()` 接受 `Linux`/`OHOS`（R32 口径 `in ("Linux", "OHOS")`）
4. `build()` 只用 `sys.executable`，不依赖 shell 变量（R33）

---
**编译结束**: 2026-10-02 14:26
**CI 修复**: 2026-10-12（build #84754：worker 解释器缺 setuptools → 改用隔离构建环境）
**最终状态**: built（补丁与配方改动后 W3 本地 CI 于 2026-10-12 11:17 复跑通过，exit_code=0）
