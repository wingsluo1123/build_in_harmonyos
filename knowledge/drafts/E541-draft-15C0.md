# E541 — 纯 Python 三方库被误派发到 C/C++ Conan 适配管线

## 错误特征

典型信号（命中任一即可判定）：

- `lang-preflight` 输出：`任务标记 cpp，实测源码为 python（setuptools），无法按 cpp 适配`
- 终态 result.json：`detected_language: python`，`language_evidence.build_system: setuptools`
- 源码树存在 `pyproject.toml`（含 `[build-system] requires = ["setuptools"]`）且**无任何 C/C++ 源文件**（无 `.c/.cc/.cpp/.h`）
- PyPI 元数据：wheel 标签为 `py3-none-any`（纯 Python、平台无关、无二进制扩展）
- 源码统计：Python 源文件主体占比 ≥ 70%，无 `setup.py` 的 `ext_modules`、无 C 扩展编译步骤

实测案例：`inkbird-ble 1.7.0`（Bluetooth-Devices/inkbird-ble，INKBIRD BLE 设备纯 Python 解析器，
homeassistant 生态），GitHub language=Python，源码 2 个 Python 文件主体占比 100%。

## 触发条件

- 构建系统: setuptools / poetry / hatchling（纯 Python 打包）
- 阶段: 派发/选型阶段（lang-preflight 前）——误认领进入 C/C++ conan 适配管线

## 根因分析

派发/选型阶段仅凭库名认领任务，未做源码语言预检。纯 Python 库（构建系统 setuptools/poetry，
产物 `py3-none-any` wheel）没有 C/C++ 编译产物，根本不适用鸿蒙PC 的 conan C/C++ 交叉编译管线
（该管线产物是 aarch64-linux-ohos 的 .a/.so/可执行文件）。

技能库的 R47/lang-preflight 工具已能在 checkout 后拦截，但知识图谱（engine 五阶段匹配 +
prescan 规则集）此前**没有对应条目**：

1. engine 匹配此类日志/信号时无 E 条目可命中，无法给出标准处置方案；
2. `pre-scan-rules.yaml` 没有 pyproject.toml/setuptools 探测规则，`prescan` 命令扫不出该风险；
3. 选型/派发阶段缺少可静态执行的早期识别信号（PyPI wheel 标签、pyproject 构建后端声明）。

本条目补齐该缺口，并通过 `prescan_pattern` 字段自动派生 `PSCAN-KB-E541` 预扫描规则
（知识增长即扫描能力增长）。

## 影响范围

所有纯 Python 三方库：蓝牙传感器解析器族（inkbird-ble、bthome-ble、sensor-state-data 等）、
homeassistant/其他 Python 生态的协议解析、数据格式库。特征是"上游仓库 language=Python 且
PyPI 只有 py3-none-any wheel"。

## 解决方案

### 推荐方案：lang-preflight 终态上报（R47）

checkout 后、进入适配主流程前立即执行语言预检；判定 python 时直接终态上报，禁止硬着头皮适配：

```bash
python3 ${SKILL_ROOT}/scripts/ohc-run.py lang-preflight <name> <ver> --src ${SRC_DIR}
# exit 非 0 且 detected_language=python → 终态 env_unsupported + detected_language + language_evidence
```

带 `detected_language` 上报 → 平台转 lang_hold 挂起等 Python 生态（非失败）；缺语言字段 = PROTOCOL_VIOLATION。

### 回退方案：派发前静态探测（选型阶段）

```bash
# PyPI wheel 标签法：py3-none-any = 纯 Python，选型阶段直接跳过
curl -s https://pypi.org/pypi/${NAME}/json | grep -o 'py3-none-any'
# 或源码探测：pyproject.toml 声明 setuptools/poetry 后端且无 C 源文件
```

### 禁止做法

- ❌ 在 C/C++ conan 配方内用 `pip install` / `setup.py install` 手工打包顶替（伪造产物、
  配方自包含性破坏、CI 无法复现）
- ❌ 无视预检结果硬着头皮走 conan create（浪费整轮编译预算，终必失败）
- ❌ 终态上报缺 `detected_language`/`language_evidence` 字段（协议 §2.4 强制，缺失被拒收）

## 验证

```bash
# 确认预检判定
python3 ohc-run.py lang-preflight inkbird-ble 1.7.0 --src <src_dir>
# 确认预扫描规则派生后可命中
python3 ohc-run.py prescan <src_dir> --json | grep PSCAN-KB-E541
```

## 关联条目

- 相关: E004（Python 扩展模块 LD_SHARED 问题——C 扩展型 Python 包，与本条目"纯 Python 无扩展"互补）
- 相关: E036（sysconfig 平台判定——C 扩展型 Python 包交叉编译）
- 区分口径: 源码含 C 扩展（setup.py ext_modules / py3-abi3 / 平台限定 wheel）→ 走 C/C++ 管线适配扩展模块；无扩展 → 本条目，env_unsupported 释放
