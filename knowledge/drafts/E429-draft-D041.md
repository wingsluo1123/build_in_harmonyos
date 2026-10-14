# E429-draft-D041 — Python 父 runner 与 script-mode 子解释器的导入路径断层

本条为路径 B 候选草稿，正式编号和入库由主编确认。案例为 dill 0.4.1，不是通过给旧条目换库名申报。

## 现象与根因

官方 `python -m dill.tests` 在源码根目录可定位 runner，但 30 个 `test_*.py` 子进程均报 `ModuleNotFoundError: No module named 'dill'`，runner exit 1。官方 runner 调用 `subprocess.Popen([sys.executable, test])`，未覆盖环境。父进程的 `-m` 模式把 CWD 加到导入路径，子进程的 script 模式把测试文件目录加到 `sys.path[0]`；父进程的内存路径不是可继承的安装状态。

## 输入、输出与处理步骤

输入：有 Python 包自身测试的发布源码、实际 runner 与子进程命令、父/子解释器位置、独立构建目录。输出：原版测试结果、被测模块来源、打包产物与消费者独立验证。

1. 对比父/子的启动模式和环境，确认缺失对象是被测包自身，不能据此追加不存在的运行依赖。
2. 在相同原版源码上取消 PYTHONPATH 取得 30/30 子进程失败；仅加入源码根 PYTHONPATH 后 30/30 子进程成功。它证明环境继承修复了执行，但还不能证明安装产物可用。
3. 通过已发布 setuptools 工具在 build 私有目录构建 `installed/`，包含上游 `dill.tests`。把安装根放进环境 PYTHONPATH，而非仅修改父进程 sys.path。
4. 从独立 verification 目录运行，先断言 `dill.__file__` 位于 installed 根，再执行未修改的官方 runner。Python >=3.11 使用 `-P` 去掉隐式 CWD，旧版本仍靠独立空目录和来源断言；`-s`/PYTHONNOUSERSITE 禁用用户站点。
5. 消费者核验包根，并在新解释器再次核验来源和函数反序列化；移走本任务包的 lib 目录应失败，finally 恢复后消费者应成功。
6. 对产物再做重定位验证；脚本数是 runner 的统计单元，可选 NumPy/SymPy 分支不可被 30/30 exit-code 结果掩盖。

## 真实验证与复现

源码 SHA256 为 `423092df4182177d4d8ba8290c8a5b640c66ab35ec7da59ccfa00f6fa3eea5fa`。HarmonyOS HongMeng Kernel 1.12.0/AArch64、Python 3.12.9、Conan 2.29.1。完整日志哈希、消费者/重定位/负向对照和 W3 结果见 `archives/d/dill/0.4.1/reports/path-b-evidence.md` 与 `validation-summary.md`。原测试及 runner 零修改；recipe-owned CLI launcher 另外列明。

```sh
# RED: source root, no ambient installed dill
unset PYTHONPATH
python3 -s -m dill.tests
# GREEN execution control (same upstream source)
PYTHONPATH="$PWD" python3 -s -m dill.tests
# Actual staged installation, from independent directory
cd "$BUILD/verification"
PYTHONPATH="$BUILD/installed" python3 -s -P -m dill.tests
```

## 查重与增量

检索最新 main 的 graph/doc/operations/drafts，关键词 `PYTHONPATH`、`script-mode child`、`sys.path[0]`、`python -m`、`installed origin`、`subprocess`。E319 是普通 noarch 打包/环境传播；E512 是第三方运行依赖缺失，不能套用于自身包的 script-mode 路径断层。`DRAFT-pytest-rootdir-shadows-installed-package` 是 pytest 主动插入 rootdir 的另一方向，调整 PYTHONPATH 并不能修复它。`DRAFT-pytest-9.1.1-subprocess-dependency-loss` 和 `DRAFT-ohos-test-subprocess-overrides-pythonpath-needs-venv` 是子进程主动覆盖环境、需 userbase/venv。`DRAFT-pyjson5-0.15.0-unittest-pythonpath-recovery` 已覆盖子进程路径恢复及源码/制品的区别；`DRAFT-pytest-9.1.1-negative-test-false-pass` 已覆盖来源断言和负向验证。本草稿不将这些方法重新申报为新知。候选增量是同一个工作目录中，-m 父 runner 成功、script-mode 子解释器失败的启动模式断层实证，以及完整 runner 的安装执行对账；与上述条目存在实质关联，是否构成独立扩展、还是补充到既有条目，明确交主编复核。本案例环境原样继承，增加安装根可生效。CLI wrapper、Conan SemLock 串行下载与 TMPDIR 属已有经验，不单独申报。

## 通用性、限制与反例

适用于 runner 用 `python -m` 或 CWD 载入自身包，再以 script 路径启动独立解释器的 Python 工程。对子进程覆盖 PYTHONPATH、启用 `-I`、pytest 主动改 sys.path、命名空间/.pth 特殊安装或扩展 ABI 问题，必须另按真实机制处理，不能机械使用本条。未修改解释器和共享 CI，未修复设备信号量或可选图形渲染。NumPy/SymPy 5 个条件分支未覆盖；脚本成功不等于所有可选对象类型均测试成功。
