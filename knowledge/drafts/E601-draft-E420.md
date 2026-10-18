# E601 — 手工铺 `.dist-info` 未做 PEP-427 归一化 → `importlib.metadata` 查不到；vendored 包携带 testutils 写死只读 `/tmp`

> 草稿态（`knowledge/drafts/E601-draft-E420.kv`），未进正式索引；正式 E 编号待 `graph promote` 分配。
> 来源适配：`archives/s/synadm/0.49.2`（vendor `dnspython` / `click-option-group` / `requests-unixsocket`）。

> 既有未晋升草稿 `DRAFT-ohos-source-copy-python-no-dist-info-version-unavailable`、
> `DRAFT-ohos-setuptools-bootstrap-and-dist-info` 已记录「不铺 dist-info → `importlib.metadata`
> 查不到版本」。本条的增量是**目录名归一化**这一层：`click-option-group-0.5.9.dist-info`
> 对 `version("click-option-group")` 不可见，必须写成 `click_option_group-0.5.9.dist-info`
> （PEP-427），METADATA 的 `Name:` 仍保留真实分发名；以及 vendored 上游包的测试资产
> （`testutils.py` 硬编码 `/tmp`）在 OHOS 只读 `/tmp` 下必须打包期剔除。晋升时请与上述草稿合并。

## 错误特征

构建期一切正常，运行期（或 test_package 消费者校验）第一次读版本就崩：

```
importlib.metadata.PackageNotFoundError: No package metadata was found for click-option-group
```

以及打包产物里出现本不该存在的测试工具，真实调用时：

```
FileNotFoundError / OSError: [Errno 30] Read-only file system: '/tmp/test_requests_...'
  .../requests_unixsocket/testutils.py:78: return '/tmp/test_requests.%s_%s_%s'
```

第二类尤其阴险：它不在构建期暴露，而是被**静态测试守卫**（"包内 .py 不得写 /tmp"）抓出来的。

## 触发条件

- 阶段：运行期（`importlib.metadata` / `click.version_option()` / 拼 `User-Agent`）
- 条件：
  1. 配方自建 `.dist-info`（Conan 里 vendor 纯 Python 依赖时的常见做法，为了让 metadata 可查），
     目录名照抄了 PyPI 展示名的连字符；
  2. vendor 时用 `shutil.copytree(src, dst)` 整树搬运，没剪测试资产。

## 根因分析

**① 元数据目录名的口径不一致。**

- `pip`/setuptools 装包时，`.dist-info` **目录名**按 **PEP-427** 生成：项目名里的 `-` 替换为 `_`；
- `importlib.metadata` 查找分发时也是按这个规则拼目录名去扫；
- `METADATA` 文件**内部**的 `Name:` 字段则保留原始（PEP-503 归一化前）名字。

只抄了其中一条规则就会分叉：写成 `click-option-group-0.5.9.dist-info` 后，
`version("click-option-group")` 必然 `PackageNotFoundError`。凡是"版本从 metadata 读"的库
（synadm 的 `User-Agent: synadm/<version>`、`click.version_option()`）都在运行期崩，
而这类代码路径往往只在 `--version` 或首次请求时才走到，构建期完全看不出来。

**② OHOS 的 `/tmp` 是只读挂载。**

`os.uname().sysname == "HarmonyOS"`，但 `sys.platform == "linux"`，所以 Python 库里
`if os.name == "posix": 写 /tmp` 这类分支会被**正常走到**并失败：

```
Errno 30  Read-only file system
TMPDIR=/data/storage/el2/base/files/home/.tmp     # 唯一可写临时区在私有 $HOME 下
```

vendored 上游包把测试工具（`testutils.py`、`tests/`）一起带进产物，既引用了非运行期依赖
（waitress / requests_mock），又可能在这些文件里写死 `/tmp`。

## 解决方案

### 推荐方案：`normalize-dist-info-dirname-and-prune-test-assets`

```python
@staticmethod
def _write_dist_info(site, dist, version, licence, top_level, console_script=None):
    # PEP-427: the *directory* name normalizes '-' to '_'; METADATA keeps the
    # original name. Without this, importlib.metadata.version(<dist>) raises
    # PackageNotFoundError (measured: click-option-group, requests-unixsocket).
    info = os.path.join(site, f"{dist.replace('-', '_')}-{version}.dist-info")
    os.makedirs(info, exist_ok=True)
    with open(os.path.join(info, "METADATA"), "w", encoding="utf-8") as h:
        h.write("Metadata-Version: 2.1\n"
                f"Name: {dist}\n"            # ← 原名，带连字符
                f"Version: {version}\n"
                f"License: {licence}\n")
```

```python
shutil.copytree(src, dst,
                ignore=shutil.ignore_patterns(
                    "__pycache__", "tests", "test", "testutils.py",
                    "*.egg-info", "*.dist-info"))   # 自带元数据也剪掉，统一由本配方生成
```

### 禁止做法

- ❌ `f"{dist}-{version}.dist-info"` —— 带连字符的分发名必然查不到。
- ❌ 整树 `copytree` 不加 `ignore_patterns`。
- ❌ `export TMPDIR=/tmp` 或代码里 `open("/tmp/...")`：OHOS 上 /tmp 只读。
- ❌ 把"运行期不该存在的文件"留在产物里指望没人 import —— 用静态守卫封死（见下方验证 ③）。

## 验证

```bash
# ① metadata 归一化前后对比
python3 -c "from importlib.metadata import version; print(version('click-option-group'))"
#   修复前：PackageNotFoundError；修复后：0.5.9

# ② /tmp 只读实证（OHOS 环境前提，写进测试比写进文档更可靠）
python3 -c "open('/tmp/probe','w')"           # 期望 OSError: [Errno 30]
python3 -c "import os;print(os.environ['TMPDIR'])"

# ③ 包内静态守卫：无 /tmp 写入、无测试资产残留
grep -rn "/tmp/"  <package_folder>/lib/python*/site-packages || echo "clean"
find <package_folder> -name "testutils.py" -o -name "tests" -type d | grep . && echo "LEAK" || echo "clean"
```

本项目已把 ①②③ 固化为 test_package 用例：
`test_synadm.py::Test02PackagingMetadata::test_vendored_distribution_metadata`、
`test_synadm_ohos.py::Test03OhosFilesystemSemantics::test_synadm_writes_no_state_to_tmp`、
`...::test_tmp_is_read_only_and_the_suite_still_writes`。

## 关联条目

- 前置：E600（依赖闭包 `run=True` / 遍历 host 依赖 —— 同一适配同一批日志里发现）
- 相关：E429（sdist 时间戳归一化打到上游用例 —— 同为"打包产物细节打到运行/测试"族）
- 相关：图谱既有 `/tmp` 只读、HMDFS 限制类条目（本条不复述，仅引用其环境前提）
