# E590 — pip --target 安装 OHOS 平台 wheel 时扩展后缀不匹配导致模块无法导入

## 错误特征

CI 构建日志先出现 pip 拒绝安装，再出现 PIL 不可用、上游测试文件被丢弃：

```
WARN: pillow via ohos wheel unavailable: pip install failed (rc=1) for pillow:
ERROR: When restricting platform and interpreter constraints using --python-version,
       --platform, --abi, or --implementation, either --no-deps must be set,
       or --only-binary=:all: must be set and --no-binary must not be set.
WARN: PIL unavailable: tests/test_utils.py cannot be collected
→ upstream suite result: 5 passed, 116 skipped
```

即便 wheel 装上了，导入扩展模块仍报：

```
ImportError: cannot import name '_imaging' from 'PIL'
```

特征：**本地全绿、CI 全红**，且失败表现为"测试数量变少"而非测试报错 —— 上游测试
文件在收集阶段就被整份跳过，测试覆盖被静默裁剪。

## 触发条件

- 语言: Python（含 C 扩展的 wheel，如 `pillow`）
- 阶段: `build()` 内用 `pip install --target` 装平台 wheel
- 工具链: 鸿蒙 PC 解释器（`EXTENSION_SUFFIXES = ['.cpython-312.so', '.abi3.so', '.so']`）
  + 社区适配源（`pypi.cnb.cool`）提供的 OHOS wheel

## 根因分析

**根因一：扩展后缀不在解释器查找列表内。** OHOS wheel 里的扩展模块名带完整平台标签，
例如 `_imaging.cpython-312-aarch64-linux-ohos.so`；而解释器的
`importlib.machinery.EXTENSION_SUFFIXES` 只有 `.cpython-312.so` / `.abi3.so` / `.so`。
文件名不在列表内 ⇒ `from PIL import Image` 报 `cannot import name '_imaging'`。

**关键陷阱**：只把 `-linux-ohos` 删掉会得到 `_imaging.cpython-312-aarch64.so`，
仍不是合法后缀，导入照旧失败 —— 必须**整体重写**为本解释器自己的 cpython 标签
`_imaging.cpython-312.so`。

**根因二：pip 在平台约束下强制要求 `--only-binary`。** 带 `--platform`（或
`--python-version` / `--abi` / `--implementation`）时 pip 直接拒绝并 `rc=1`，wheel
根本装不上。缺了这一步，连"改名"的机会都没有。

**为什么本地看不出问题**：开发机宿主 site-packages 已装 `pillow`，配方走 tier-1
（宿主探测）即命中，`conan create` 根本不会走到装 OHOS wheel 的分支，于是"本地全绿"。
CI worker 没有 pillow，才暴露出两个根因。

## 解决方案

### 推荐方案

1. 用 `--platform` 装 wheel 时必须同时带 `--only-binary=:all:`（或 `--no-deps`）：

   ```bash
   pip install --no-compile --target=$SITE --platform ohos_aarch64 --only-binary=:all: pillow
   ```

2. 装完遍历目标目录，把 `.so` 文件名里外来的平台标签重写成本解释器的 cpython 标签
   （形如 `.cpython-312.so`）。重写规则按 `sys.version_info` 的 `major.minor` 生成并
   **锚定**，避免误改其他 Python 版本的标签或已合法的文件名：

   ```python
   tag = f"cpython-{sys.version_info.major}{sys.version_info.minor}"
   # 只重写"外来的本解释器标签"，不动 .abi3 / .so / 异版 cpython-311 等
   ```

3. 用 `python -S` 做一条不依赖 site-packages 的导入断言，确认扩展真能导入
   （否则宿主已装的同名包会继续掩盖问题）。

### 禁止做法

- ❌ 只删 `-linux-ohos`（留下 `-aarch64`，问题从"装不上"变成"装了不能用"）。
- ❌ 带 `--platform` 却不带 `--only-binary=:all:` / `--no-deps`（pip 直接报错退出）。
- ❌ 把 PIL 标记为"可选 extra"就此放过 —— 只要上游测试在模块级 `import PIL`，
  缺它就会让测试文件在收集阶段被整份丢弃，属于静默降低覆盖。
- ❌ 运行时往 `importlib.machinery.EXTENSION_SUFFIXES` 里 append 后缀当交付方案：
  只作用于当前进程、无法传递给下游消费者，且掩盖了产物名不合规本身（仅可应急）。

## 验证

```bash
# 1. 解释器允许的后缀
python3 -c "import importlib.machinery as m; print(m.EXTENSION_SUFFIXES)"
# 2. 装 wheel（注意 --only-binary）
pip install --no-compile --target=$SITE --platform ohos_aarch64 --only-binary=:all: pillow
# 3. 隔离解释器下导入（-S 不加载 site-packages）
PYTHONPATH=$SITE python3 -S -c "from PIL import Image; print(Image.__version__)"
```

实测对照（toot 0.52.1，pillow 12.3.0）：装完改名前 8 个 `.so` →
`ImportError: cannot import name '_imaging'`；重写后缀后 8 个 →
`_imaging.cpython-312.so` → `PIL OK 12.3.0`。回归守卫：只改 1 个外来标签，
`cpython-311` 异版、`.abi3`、已合法名均未被动。

## 关联条目

- 相关: E587
