# jaraco.stream

`jaraco.stream` 是 jaraco 生态中的「流式数据处理」库：把 socket / 管道 / 网络响应
这类**分块到达的字节流**，可靠地切分成完整行，并能在可迭代对象上解压 gzip 流
（支持多个 gzip 成员首尾相接）。常用于 IRC 客户端、日志管道、HTTP 流式响应解析。

- Homepage: https://github.com/jaraco/jaraco.stream
- PyPI: https://pypi.org/project/jaraco.stream/
- License: MIT
- Build system: setuptools（setuptools_scm 取版本）
- Package type: pure Python library

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [3.0.4](./3.0.4/) | built | 2026-10-09 |

## 交付内容

| 模块 | 说明 |
|------|------|
| `jaraco/stream/__init__.py` | `Tee` —— 把 stdout 同时写一份到文件 |
| `jaraco/stream/buffer.py` | `LineBuffer` / `DecodingLineBuffer` / `LenientDecodingLineBuffer` —— 行缓冲，支持按 `\n`、`\r\n` 切分与 UTF-8 / latin-1 解码策略 |
| `jaraco/stream/gzip.py` | `read_chunks` / `load_stream` / `load_streams` / `lines_from_stream` —— 在分块流上解压 gzip（含多成员串联）并逐行产出 |

## OHOS 适配要点

- 纯 Python 包，**无需编译**：适配工作为「源码 → site-packages 布局 → PYTHONPATH 暴露」
- 运行期依赖 `more_itertools`（`gzip.py` 导入期即用 `peekable`），制品仓已有
  `more-itertools/11.1.0`，配方直接 `requires`
- ⚠ `more-itertools/11.1.0` 的配方未导出 PYTHONPATH，本包在 `package_info()`
  中替它把路径挂上，否则消费者 `import jaraco.stream.gzip` 会 ModuleNotFoundError
- 源码取 PyPI 官方托管 sdist（哈希不可变、含上游测试、版本号已烘焙，无需
  setuptools_scm 的 git 元数据）
- 上游测试两批（pytest 2 项 + docstring doctest 3 项）均已在真机实际运行：
  **5/5 通过**，详见 `3.0.4/notes.md`
