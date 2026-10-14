# jaraco.stream 3.0.4 — OHOS 适配笔记

> 目标平台：HarmonyOS PC（HAD-W32，aarch64）；profile `ohos-verify`
> 适配日期：2026-10-09 · 任务 id=12629 · 分支 `feat/jaraco.stream-3.0.4`

## 一、R51 上游测试三步法

### ① 适配前清点（上游测试在哪、有多少）

上游把测试**直接放在包目录内**（不是独立 `tests/`），清点口径为「包内测试模块」：

| 来源 | 类型 | 用例数 | 命令 |
|---|---|---|---|
| `jaraco/stream/test_gzip.py` | pytest | 2 | `python -m pytest jaraco/stream/test_gzip.py` |
| `jaraco/stream/buffer.py` | docstring 内嵌 doctest | 3 | `python -m pytest --doctest-modules jaraco/stream/buffer.py` |
| **合计** | | **5** | |

清点证据（源码来自 PyPI sdist `jaraco_stream-3.0.4.tar.gz`）：

```bash
$ tar tzf jaraco_stream-3.0.4.tar.gz | grep -E "test|buffer|gzip"
jaraco_stream-3.0.4/jaraco/stream/__init__.py
jaraco_stream-3.0.4/jaraco/stream/buffer.py        # 3 个 doctest（LineBuffer / DecodingLineBuffer / LenientDecodingLineBuffer）
jaraco_stream-3.0.4/jaraco/stream/gzip.py
jaraco_stream-3.0.4/jaraco/stream/test_gzip.py     # 2 个 pytest 用例
```

两个 pytest 用例会**在本地起一个 HTTP server（localhost:8080）**提供 gzip 数据，
再走 `read_chunks → load_streams → lines_from_stream` 的完整链路 —— 属于端到端用例，
不是纯断言。

### ② 在真机实际运行

设备侧 pytest 由平台的 `pytest/9.1.1` 制品提供（设备解释器本身不带 pytest）：

```bash
# 取 pytest 及其依赖的 site-packages（conan 制品）
conan install --requires=pytest/9.1.1 -pr:h=ohos-verify -pr:b=ohos-verify -g VirtualRunEnv
# 运行上游测试（PYTHONPATH 指向 sdist 源码 + pytest/more_itertools 的 site-packages）
cd jaraco_stream-3.0.4
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH="...:$(pwd)" python -m pytest \
    jaraco/stream/test_gzip.py -q -p no:cacheprovider
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH="...:$(pwd)" python -m pytest \
    --doctest-modules jaraco/stream/buffer.py -q -p no:cacheprovider
```

实测输出（2026-10-09，设备上）：

```
jaraco/stream/test_gzip.py    ->  2 passed in 1.12s
jaraco/stream/buffer.py       ->  3 passed in 0.02s
```

沙箱内 `localhost` 绑定与回环访问均正常，网络型用例无需排除。

### ③ 结果回填

上游测试 **5/5 通过**（`total=5, passed=5, failed=0`，无 skip / xfail），
已填入本目录 `manifest.yaml` 与 `test_package/MANIFEST.yml`。

配方 `build()` 中集成了同样的两条命令：探测到 pytest 就实际执行并输出结果，
探测不到则**显式警告**（不静默跳过）——云 runner 若未预装 pytest，
真机实测数据以本节为准。

## 二、消费者测试（R34 / R12）

`test_package/test_jaraco_stream.py` 站在使用者角度，只调公开 API，**29 项断言**：

| 类别 | 断言数 | 覆盖内容 |
|---|---|---|
| 导入面 | 6 | 包与 `buffer`/`gzip` 子模块可导入、`Tee` 存在、行缓冲三件套与 gzip 工具函数齐全 |
| LineBuffer | 8 | 空缓冲、`feed` 后长度 7、切出 `b'foo'`、未完成行保留（3）、`\n` 与 `\r\n` 都能切、切完清空、不解码（保持 bytes）、可迭代协议 |
| DecodingLineBuffer | 3 | UTF-8 解码正确、`errors='replace'` 容错非法字节、严格模式抛 `UnicodeDecodeError` |
| LenientDecodingLineBuffer | 1 | UTF-8 与 latin-1 混流都能解 |
| gzip 流 | 8 | `read_chunks` 按块切分且不丢尾块、拼接无损、逐行还原 3 行、首/末行 JSON 语义、**多 gzip 成员（2 段）解出 6 行且顺序正确**、`io.BytesIO` 直传用法 |
| 依赖可见性 | 1 | `more_itertools` 由 conan requires 提供并可导入 |
| Tee | 2 | 内容同时写入文件、stdout 可还原 |
| **合计** | **29** | |

实测：**29/29 通过**（`conan create` 的 test_package 阶段）。

## 三、适配要点

1. **纯 Python 包，无需编译**
   适配 = 源码 → `lib/python3.12/site-packages/jaraco/stream` → `PYTHONPATH` 暴露。
   交付三个模块：`__init__.py`（`Tee`）、`buffer.py`（行缓冲）、`gzip.py`（gzip 流）。

2. **运行期依赖 `more_itertools`**
   `gzip.py` 在**导入期**就 `from more_itertools.more import peekable`，故配方
   `requires("more-itertools/11.1.0")`（制品仓已发布）。实测：conan 可正常解析并拉取
   （其自身的 `typing-extensions/4.16.0` 依赖也一并解析）。

3. **⚠ 依赖未导出 PYTHONPATH → 在本包补挂**
   `more-itertools/11.1.0` 的配方把文件装到 `lib/python3/site-packages`，但
   `package_info()` 只写了 `cpp_info.libs = []`，**没有导出 PYTHONPATH**。
   若不处理，消费者 `import jaraco.stream.gzip` 会直接 `ModuleNotFoundError`。
   本配方在 `package_info()` 里读 `self.dependencies["more-itertools"].package_folder`
   并把其 site-packages 一起 `append_path("PYTHONPATH", ...)`。
   （消费者测试刻意走 `conanrun` 环境而不手工拼 PYTHONPATH，就是为了验证这段导出真的生效。）

4. **源码取 PyPI sdist 而非 GitHub tag 归档**
   上游用 `setuptools_scm` 动态取版本，GitHub tag 归档里没有 git 元数据，
   要额外注入 `SETUPTOOLS_SCM_PRETEND_VERSION`；而 PyPI sdist 的 `PKG-INFO`
   已烘焙版本号，且**同样包含上游测试**（`jaraco/stream/test_gzip.py`），
   哈希还不可变 —— 综合更省事也更稳。

5. **`package_type = "python-require"`**
   与 `anytree` 等纯 Python 包保持一致；`more-itertools` 虽声明
   `package_type = "application"`，实测可被正常 require（conan 2.29）。

## 四、交付物

```
lib/python3.12/site-packages/jaraco/stream/__init__.py
lib/python3.12/site-packages/jaraco/stream/buffer.py
lib/python3.12/site-packages/jaraco/stream/gzip.py
lib/python3.12/site-packages/jaraco/stream/test_gzip.py   ← 上游随包分发，原样保留
licenses/LICENSE
```

## 五、已知限制

无。三批测试（上游 pytest 2 + 上游 doctest 3 + 消费者 29）全部通过；
包内不含 C 扩展，无平台相关的可选功能需要裁剪。
