# DRAFT-ohos-two-cpython-abi-tag-ext-suffix：
# OHOS 上并存两套 CPython，扩展 ABI 标签由**驱动构建的那个解释器**决定
# （`.cpython-312-aarch64-linux-ohos.so` vs `.cpython-312.so`）

- **来源**：refnx 0.1.62 适配（2026-10-15）
- **领域**：Python / 构建期与校验期解释器一致性（OHOS 平台级坑）
- **严重度**：🟡 medium（两个方向都会浪费一整轮构建）

## 现象

同一台 OHOS 设备上，用不同的 `python3` 得到**不同**的扩展文件后缀：

```bash
$ /data/service/hnp/bin/python3 -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))"
.cpython-312.so                                  # 设备 HNP 解释器（自有 ABI 标签）

$ <制品仓 python/3.12.9>/bin/python3.12 -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))"
.cpython-312-aarch64-linux-ohos.so               # OHPCD Conan 制品仓 CPython
```

于是两个相反方向的故障都会出现：

1. **构建期**：用设备 HNP 解释器驱动 meson → 4 个扩展被打上 `.cpython-312.so` 名字，
   而目标 CPython 期待 `.cpython-312-aarch64-linux-ohos.so` → 运行期
   `ImportError: dynamic module does not define module export function (PyInit_...)`。
2. **校验期**：产物命名**正确**（由制品仓解释器构建），但校验脚本拿了 PATH 上的
   设备 `python3` 当基线 → 把**全部合规扩展判成缺陷**（假失败），白白重跑一轮。

## 根因

设备 HNP 解释器与制品仓 CPython 是**两个不同的发行**，各自用不同的 `EXT_SUFFIX` 约定：

| 解释器 | EXT_SUFFIX |
|---|---|
| 设备 `/data/service/hnp/bin/python3` | `.cpython-312.so` |
| 制品仓 `python/3.12.9`（`tool_requires`） | `.cpython-312-aarch64-linux-ohos.so` |

**用哪个解释器驱动 meson，就决定了扩展落盘的文件名**；反过来，校验通道若拿 PATH 上的
`python3`（设备 HNP 的，`.cpython-312.so`）当基线，就会与正确的产物标签对不上。
**两条路径（构建期 / 校验期）必须使用同一个目标解释器。**

## 解决方案

### 推荐方案（priority 1，`pin-target-interpreter-tool-requires`）

构建与校验都**显式** `tool_requires("python/3.12.9")`，并把它交给 meson 的 `[binaries] python`。
校验脚本**先取候选解释器的 EXT_SUFFIX，只有当它含 `-linux-ohos` 时才作为基线**，否则跳过并
记录该备选解释器的真实后缀：

```bash
python3 -c "import sysconfig;print(sysconfig.get_config_var('EXT_SUFFIX'))" \
  | grep -q -- "-linux-ohos" || echo "not the target interpreter"
```

> 校验顺序很关键：**先验证候选解释器身份，再拿它当基线**——否则会把正确命名判成缺陷。

### 回退方案（priority 2，`abi-tag-assertion-from-config`）

校验脚本**不要硬编码后缀字符串**，改为 `__import__` 后比对
`os.path.basename(mod.__file__).endswith(sysconfig.get_config_var("EXT_SUFFIX"))`；
并用 `sys.dont_write_bytecode` + 逐扩展 `os.walk` 计数，把产物总数**钉成构建系统已知的固定值**
（refnx 的 `EXPECTED_EXTENSIONS = 4`），只移走一个产物也会红。

```bash
python3 -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))"
```

### ★ 禁止做法

- ❌ 拿 shell 里 `which python3` 找到的解释器当**构建或校验基线**。

**后果**：构建时给扩展打错 ABI 标签（运行期 ImportError），校验时把合规产物判成缺陷
（假失败）——**两种方向都要重跑整轮**。

## 复现证据（refnx 0.1.62 实测）

| 场景 | 结果 |
|---|---|
| 静态通道用设备 HNP 解释器当基线 | 4/4 扩展被判 ABI 不符（假失败） |
| 改为 `tool_requires python/3.12.9`，先校验其 EXT_SUFFIX 含 `-linux-ohos` | 4/4 扩展通过；`EXPECTED_EXTENSIONS=4` 钉住总数 |
| 破坏性验证：移走 1 个扩展 | 静态检查由"3/3 全绿"变为**6 项全红**（判别力成立） |

## 关联条目

- 亲缘：E004（musl 不导出解释器符号 → 扩展必须自带 `DT_NEEDED libpython`）
- 邻近：[[DRAFT-ohpcp-cpython-stdlib-extensions-missing-native-dt-needed]]（同为"平台提供多个
  CPython"引发的坑，但根因是 stdlib 扩展缺原生库 NEEDED，而非 ABI 标签）
