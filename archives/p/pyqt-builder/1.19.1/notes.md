# PyQt-builder 1.19.1 — HarmonyOS PC 适配说明

## 包性质

PyQt 的构建系统，**纯 Python**（`py3-none-any`）。上游 `pyproject.toml`：

```toml
[build-system]
requires = ["setuptools>=77", "setuptools_scm>=8"]
build-backend = "setuptools.build_meta"

[project]
dependencies = ["packaging", "sip >=6.7, <7"]
```

sdist 已自带生成好的 `pyqtbuild/_version.py`（`__version__ = '1.19.1'`），
故 `setuptools_scm` 只是构建期声明，实际打包**无需触发**——直接
copytree 到 site-packages 即可（packaging / sip 同款做法）。

## 关键点：sip 是运行期依赖，不是构建期

`pyqtbuild` 的三个核心模块在 **import 时**就 `from sipbuild import ...`：

```
pyqtbuild/bindings.py:10:  from sipbuild import Bindings, BuildableExecutable, ...
pyqtbuild/builder.py:9:    from sipbuild import (Buildable, BuildableModule, Builder, ...)
pyqtbuild/project.py:9:    from sipbuild import Option, Project, UserException
```

因此配方**必须声明 `sip`**（上游约束 `sip<7,>=6.7`，本仓用 `sip/6.16.1`）。
这也意味着本包的消费者测试天然覆盖「sip + PyQt-builder 链路可导入」。

## 数据树必须原样打包

`pyqtbuild/` 不只是 `.py`，还带三棵数据目录：

| 目录 | 内容 |
|---|---|
| `bundle/dlls/` | msvc-32/64/arm64 与 openssl 的 Windows DLL（打包 Qt wheel 用） |
| `bundle/packages/` | 各 PyQt 包的元数据模块（pyqt5.py / pyqt6.py / …） |
| `bundle/qt_wheel_distinfo/` | Qt wheel 的 METADATA / WHEEL 模板 |

所以 `package()` 用整树 `copytree`（含 `symlinks=True`），不能只挑 `.py`。

## CLI

上游 `[project.scripts]` 两个入口，配方生成对应 `bin/` 脚本：

```
pyqt-bundle      -> pyqtbuild.bundle.bundle_main:main
pyqt-qt-wheel    -> pyqtbuild.bundle.qt_wheel_main:main
```

按 R38（有 bin/ 可执行即需软件级 `commands.json`），已随包提交。

## 测试

**上游无测试套件**（sdist 内无 `tests/`、无 CI 测试步骤）。
按 TEST_QUALITY_SPEC.md 3.3 走豁免 `upstream_has_no_test_suite`，
功能覆盖由 `test_package/test_pyqt_builder.py` 的 8 项消费者断言提供：

- `pyqtbuild` 导入成功（**同时验证 sip 依赖已就位**）；
- 版本常量 `PYQTBUILD_VERSION_STR == "1.19.1"`；
- 四个公开类存在（`PyQtBindings` / `QmakeBuilder` / `PyQtProject` /
  `QmakeTargetInstallable`）——正是 PyQt6 构建后端所依赖的 API；
- `bundle/packages/pyqt6.py` 与 `bundle/qt_wheel_distinfo/METADATA`
  存在（证明数据树未在打包中丢失）；
- 两个控制台脚本可执行且 `--help` 正常返回。
