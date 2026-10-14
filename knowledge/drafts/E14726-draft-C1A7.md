# E14726 — OHOS 解释器 `sys.platform` 不稳定（`ohos`/`linux` 随构建而变）

## 错误特征

OHOS 上运行 `.py` 相关步骤时报：

```
ImportError: Sorry: no implementation for your platform ('posix') available
```

同时 pyserial 在 stderr 打印诊断：

```
don't know how to enumerate ttys on this system.
! I you know how the serial ports are named send this information to
! the author of this module:

sys.platform = 'ohos'
os.name = 'posix'
pySerial version = 3.5
```

特征：**本地全绿、CI/目标机红**，且报错来自一个与被适配物"无关"的第三方库
（本例 pyserial）。判据是 `sys.platform` 在两端取值不同。

## 触发条件

- 语言: Python（纯 Python 应用/库同样会踩，与是否交叉编译无关）
- 阶段: runtime（import 期即触发；构建期自检、消费者测试都会命中）
- 前提: 被适配物（或其依赖）在 import 期就调用了某个**用 `sys.platform` 做平台分派**
  的第三方模块

## 根因分析

OHOS 上这三个指纹**不总是一致**：

| 探测方式 | 实测值 |
|---|---|
| `os.uname().sysname` | `HarmonyOS`（稳定） |
| `platform.system()` | `HarmonyOS`（稳定） |
| `sys.platform` | **不稳定**：HNP 解释器 → `linux`；worker 自带解释器 → `ohos`；另有构建报 `harmonyos` / `ohos-*` |

pyserial 3.5 的 `serial/tools/list_ports_posix.py` 按 `plat = sys.platform.lower()`
前缀分派后端，只认识 `linux` / `darwin` / `cygwin` / … ：

```python
plat = sys.platform.lower()
if plat[:5] == 'linux':
    from serial.tools.list_ports_linux import comports
...
else:
    sys.stderr.write("don't know how to enumerate ttys on this system...")
    raise ImportError("Sorry: no implementation for your platform ('{}') available"
                      .format(os.name))
```

而 `serial/tools/list_ports.py` 按 `os.name == 'posix'` 分派到该模块——因此
`from serial.tools.list_ports import comports` 在 `sys.platform == 'ohos'` 时**直接抛错**。
被适配物若在 import 期就依赖它（`tinyprog/__init__.py` 即如此），则 import 即失败。

**关键点**：`sys.platform` 的不确定性属于"环境语义不可迁移"——本地命令在 CI 逐字可执行，
但语义不同（W0b）。本地 `sys.platform == 'linux'` 的成功**不能**外推到 OHOS。

**为什么不能在本包内直接改依赖**：本仓 W2/PF1 要求配方 PR 单包原子，pyserial 是**外部
conan 依赖**（本仓无其配方），不能在一个 tinyprog 的 PR 里顺带修 pyserial。

## 解决方案

### 推荐方案：随包下发 `sitecustomize.py` 平台 shim

CPython 启动时会按 `PYTHONPATH` 自动导入 `sitecustomize`。把 shim 与载荷放在一起
（`exports_sources` + `build()` 拷入 stage + `package()` 随包），它在 OHOS 上把**正确的
后端模块**注册到第三方分派器要查的模块名下：

```python
# sitecustomize.py（随包下发）
import sys

if sys.platform.startswith(("ohos", "harmonyos")):
    try:
        from serial.tools import list_ports_linux as _list_ports_linux
    except ImportError:
        pass          # 该解释器里没有 pyserial，无需处理
    else:
        sys.modules.setdefault(
            "serial.tools.list_ports_posix", _list_ports_linux)
```

要点：

1. **只注册具体模块，不改全局 `sys.platform`**——避免污染同进程其它按 `ohos` 分流的代码
   （见下方禁止做法）。
2. `sys.modules.setdefault` 幂等；`try/except ImportError` 兜底（依赖不在路上时不炸）。
3. 非 OHOS 平台**零动作**（对其它平台透明）。
4. 本仓先例：`cruft` 随包下发 `sitecustomize.py` 修 OHOS 子进程启动问题。

同时把**测试里写死的平台指纹放宽**（本地实测 `linux` 只是"一种"取值）：

```python
self.assertTrue(sys.platform.startswith(("linux", "ohos", "harmonyos")))
```

### 兜底方案：在依赖自己的配方里加平台分支

若该依赖在本仓**有配方**（或可另开 PR 单独适配），从根上修更好：在其源码分派点追加
`ohos`/`harmonyos` 分支（本仓 `bpytop` 对 psutil 的 `_common.py` 即此做法）：

```python
LINUX = sys.platform.startswith(("linux", "ohos"))
```

### 禁止做法

- ❌ 在包内把全局 `sys.platform` 改写成 `'linux'`（`sys.platform = 'linux'`）——会污染整个
  进程，让真正按 `ohos` 分流的代码被静默关闭；应改为只注册具体后端模块。
- ❌ 本地绿就当通过——`sys.platform` 两端不同，必须显式对比两端的取值。

## 验证

```bash
# 1) 目标解释器上的真实指纹（本地 != 目标是常态）
python3 -c "import sys, platform; print(sys.platform, platform.system())"

# 2) 模拟 ohos：无 shim 应 ImportError，有 shim 应成功
python3 -c "
import sys; sys.platform = 'ohos'
import serial.tools.list_ports as m; print(m.comports.__module__)"      # -> ImportError（无 shim）
# 加载 shim 后应打印 serial.tools.list_ports_linux（OHOS 上）

# 3) 透明性：非 OHOS 上 shim 应为 no-op
python3 -c "
import sys; assert sys.platform != 'ohos'
# 加载 shim 后 'serial.tools.list_ports_posix' 不应出现在 sys.modules 中（未被注册）"
```

## 关联条目

- 相关: E212（HNP python 对用户路径 `.so` 的 dlopen 限制——同一"本地/CI 解释器不同"家族）、
  E355（OHOS 平台串在不同框架里命名不一，需并集匹配）
