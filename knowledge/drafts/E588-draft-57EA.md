# E588 — 纯 Python 包消费者测试覆盖 PYTHONPATH，本地全绿而 CI 全红

## 错误特征

`conan create` 在 `test_package` 阶段失败，`bin/<tool>` 子进程退出码非 0，日志形如：

```
[FAIL] G4a ... rc=1
[FAIL] G4b ... rc=1
Traceback (most recent call last):
  File "bin/toot", line 5, in <module>
    from toot.cli import cli
ModuleNotFoundError: No module named 'click'
ERROR: conanfile.py: Error 1 while executing
[fail] toot/0.52.1 — conan create failed
```

特征：同一份配方的 `test_package` 直接在源码树上跑（不经子进程）时断言全过，
只有走子进程的那几条挂；且**本地 `conan create` 全绿，CI worker 上全红**。

## 触发条件

- 语言: 纯 Python（`package_type` 为 `application` / `python-require`）
- 阶段: `conan create` 的 `test_package`（`conan test`）
- 工具链: conan 2.x + `VirtualRunEnv`（`conanrun`）
- 测试代码自行拼装子进程环境变量，例如
  `env["PYTHONPATH"] = pkg` / `os.environ["PYTHONPATH"] = pkg`

## 根因分析

`test_package` 常把包根塞进子进程的 `PYTHONPATH`，写法多为整体赋值。这是**覆盖而非
追加**：`conanrun`（`VirtualRunEnv` 生成的 `conanrunenv-release-*.sh`）注入的全部依赖
路径被整条丢弃。实测该脚本导出的 `PYTHONPATH` 有 17 条，`click`、`urwid`、`requests`、
`chardet`、`soupsieve` 等都在其中 —— 一旦被覆盖，子进程只能 import 到包自身。

**为什么本地看不出问题**：开发机上宿主解释器的 site-packages 已经装有 `click` /
`urwid` / `requests` 等依赖，子进程即便丢了 `conanrun` 路径也照样 import 成功，
`conan create` 全绿，形成**假绿**。CI worker 是干净环境，解释器里没有这些三方包，
同一段代码立刻 `ModuleNotFoundError`。

判别方法（决定性）：用 `python3 -S` 重跑被测二进制。`-S` 不加载 site-packages：

```
PYTHONPATH=<pkg>              python3 -S bin/toot --version  → rc=1  ModuleNotFoundError: No module named 'click'
PYTHONPATH=<conanrun 全量>    python3 -S bin/toot --version  → rc=0  toot v0.52.1
```

若依赖只来自 `conanrun` 的 `PYTHONPATH`，`-S` 下应仍为 `rc=0`。

> 反向坑：不要采信"`conanrun` 的 `PYTHONPATH` 只影响子进程、脚本自身不会继承"这类
> 判断 —— `conanrun` 确实导出了完整依赖路径，据此去覆盖环境变量**正是缺陷本身**。

## 解决方案

### 推荐方案

1. 构造子进程环境时，把包根 **prepend** 到继承来的 `PYTHONPATH` 之前，保留全部依赖条目：

   ```python
   env = dict(os.environ)
   env["PYTHONPATH"] = os.pathsep.join([pkg] + [p for p in (env.get("PYTHONPATH") or "").split(os.pathsep) if p])
   ```

2. 在 `test_package` 内增加一条**隔离断言**，把本地与 CI 的判别条件固化进测试：
   用 `sys.executable` 加 `-S` 重跑被测二进制并要求 `rc=0`。`-S` 不加载
   site-packages，所以该断言通过 ⇒ 依赖更全的 CI 环境必然通过。

### 禁止做法

- ❌ `env["PYTHONPATH"] = pkg` / `os.environ["PYTHONPATH"] = pkg`（整体赋值）
  —— 丢弃 `conanrun` 注入的依赖路径，本地因宿主 site-packages 侥幸通过，CI 必挂。
- ❌ 靠 `--ignore=tests/xxx.py` / `--deselect` 把失败用例裁掉
  —— 静默降低测试覆盖，使声明数量与实际执行数量不一致。
- ❌ 把该失败判断为"依赖包未构建"并去捯饬依赖配方
  —— 根因在被测包自己的测试代码里，改依赖配方无效且越权（W2）。

## 验证

```bash
# 隔离解释器下必须 rc=0（依赖全部来自 conanrun）
. conanrun.sh && PYTHONPATH=<pkg_folder>:$PYTHONPATH python3 -S bin/<tool> --version; echo rc=$?
# 反证：只有包根时应失败
PYTHONPATH=<pkg_folder> python3 -S bin/<tool> --version; echo rc=$?
```

## 关联条目

- 相关: E587
