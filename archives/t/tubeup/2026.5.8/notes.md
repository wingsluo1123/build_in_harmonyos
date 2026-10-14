# tubeup 2026.5.8 适配笔记

## 编译环境

- 类型：纯 Python（noarch），Conan `python-require` 配方
- 适配日期：2026-10-13
- Python：3.12.8（OHOS 运行时，`sys.version_info[:3] == (3, 12, 8)`）
- 平台：OHOS aarch64（`platform.system() == "HarmonyOS"`, `platform.machine() == "aarch64"`）
- 最终状态：built

## 编译步骤

```bash
conan create archives/t/tubeup/2026.5.8 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

配方按 `python-require` 模板打包：`tubeup/` 源码目录复制到
`lib/python3.12/site-packages/tubeup/`，并按上游 `[project.scripts]`
生成 `bin/tubeup` 入口脚本（注入 site-packages 后调用 `tubeup.__main__:main`）。
不运行 setuptools/pip 构建后端，copytree 打包零依赖、可复现。

## 依赖预检（W0/R36）

```bash
bash ci/scripts/preflight_check.sh tubeup/2026.5.8 \
  --deps "internetarchive/5.10.1 docopt/0.6.2 yt-dlp/2026.5.8"
```

| 依赖 | ohpcd 状态 | 处理方式 |
|------|-----------|---------|
| `internetarchive/5.10.1` | ✅ 已发布（含 OHOS/armv8 binary） | 声明为 `requires` |
| `docopt/0.6.2` | ✅ 已发布（含 OHOS/armv8 binary） | 声明为 `requires` |
| `tqdm/4.70.1` | ✅ 已发布（含 OHOS/armv8 binary） | 声明为 `requires`（internetarchive 运行时 `from tqdm import tqdm`） |
| `yt-dlp` | ❌ 未发布（只有旧的 dev 手工归档，无 Conan recipe） | **不可声明**（R36/L0i/PF4 会拦截）→ `patches/0001` 守护补丁 |
| `jsonpatch` / `jsonpointer` | ❌ 未发布；cmd-pkgs `py3-jsonpatch` 亦未就绪 | `internetarchive` 在 import 期 `from jsonpatch import make_patch`，故 pip 打入本包 staging（`jsonpatch==1.35 jsonpointer==3.2.1`） |
| `requests` / `urllib3` / `certifi` / `idna` / `charset_normalizer` | 运行环境自带（Conan 自身依赖，用户级 site-packages） | 不声明 |

> 说明：发布的 `internetarchive/5.10.1` 包只包含 `internetarchive/` 本体，未声明也未捆绑
> `jsonpatch`/`tqdm`/`requests` 等运行时依赖（其 recipe 在 build() 里用
> `pip install --break-system-packages` 装到构建机系统环境，属仓库既有的遗留做法）。
> tubeup 侧因此显式声明 `tqdm`（Conan 已有），并把无法走 Conan 的 `jsonpatch`/`jsonpointer`
> 钉版本打入本包，确保干净消费者可直接 `import tubeup`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|---------|
| 1 | test_package 报 `/bin/sh: python3: inaccessible or not found` | `self.run(..., env="conanrun")` 用 `/bin/sh`，conanrun 的 PATH 不含 python3（本机 python3 位于 `/data/service/hnp/bin`，不在 buildenv 的 PATH 中） | test_package 改用 `sys.executable` 调用脚本（internetarchive test_package 同款做法） |
| 2 | `import internetarchive` 报 `No module named 'jsonpatch'` | 发布的 internetarchive 包不含 jsonpatch，且 jsonpatch 无 Conan 包 | `build()` 中 `pip install --target=<stage>` 钉版本打入本包 |
| 3 | tqdm 在 CI 可能缺失 | internetarchive 在 import 期导入 tqdm，环境不保证提供 | 声明 `requires("tqdm/4.70.1")`，并在 test_package 把全部依赖的 site-packages 拼进 PYTHONPATH |
| 4 | yt-dlp 未发布 | 上游硬依赖，ohpcd 无 Conan recipe | `patches/0001-guard-optional-yt-dlp.patch` 使顶层 import 降级为可选，仅在下载路径抛受控 `RuntimeError` |

## 源码修改

`patches/0001-guard-optional-yt-dlp.patch`（patch_type: portability）：

1. `tubeup/TubeUp.py` 顶层 `from yt_dlp import YoutubeDL` → `try/except ImportError` +
   `YoutubeDL = None`；
2. `get_resource_basenames()` 进入下载前检查 `YoutubeDL is None`，抛出明确
   `RuntimeError`（提示安装 yt-dlp）。

补丁不含平台宏，仅做可选的依赖降级；CLI 解析、collection/license 判定、
yt-dlp 选项生成、archive.org 元数据构造、utils 工具函数在无 yt-dlp 时全部保持可用。
待 yt-dlp 的 Conan 包发布后，可移除该补丁并把 `yt-dlp` 加入 `requirements()`。

## 验证结果

### 上游测试（OHOS aarch64，Python 3.12.8）

```text
$ cd <upstream-src>   # tests/ 含 constants.py 与 test_tubeup_files/ 测试数据
$ PYTHONPATH=<deps>:<src> python3 -m pytest tests -q
...........................                                              [100%]
27 passed in 2.05s
```

- `tests/test_main.py`：2 个（docopt CLI 短选项解析）
- `tests/test_tubeup.py`：20 个（目录处理 / logger / collection 判定 / ydl 选项 / 元数据 / upload_ia / archive_urls）
- `tests/test_utils.py`：5 个（sanitize_identifier / check_is_file_empty）
- 补丁应用后重跑：仍 27 passed（未回归）

### Conan 打包与消费者测试

```text
$ conan create archives/t/tubeup/2026.5.8 -pr:h=... -pr:b=... --build=missing
...
tubeup/2026.5.8: package(): Packaged 7 '.py' files
tubeup/2026.5.8: Package '...' created
tubeup/2026.5.8 (test package): RUN: python3 test_tubeup.py ...
OK: tubeup 2026.5.8 consumer API test passed
tubeup/2026.5.8 (test package): RUN: python3 test_tubeup_ohos.py ...
OK: tubeup OHOS consumer test passed (system=HarmonyOS, machine=aarch64)
```

### 打包入口脚本

```text
$ PYTHONPATH=<conan site-packages> <pkg>/bin/tubeup --version
2026.5.8
$ PYTHONPATH=<conan site-packages> <pkg>/bin/tubeup --help
tubeup - Download a video with Youtube-dlc, then upload to Internet Archive, ...
```

## 注意事项

- 本包描述符仅安装到 `lib/python3.12/site-packages`，不宣称跨 Python 小版本兼容。
- `restrictfilenames=True` 保留启用，避免 HMDFS 上特殊字符文件名问题。
- 无 yt-dlp 时无法下载（受控报错），不影响导入、CLI 帮助/版本与元数据能力。
- L2 冒烟：本地 W3 模拟报 `L2: No bin/ directory found — skipping`（该本地 L2 只看
  archive 构建 bin/）。CI 的 L2 从包缓存 `find ... -name bin` 取到包内 `bin/tubeup`
  并直接执行 `--version`，因不加载 conanrun 环境、依赖不在 PATH 上而如实报
  `tubeup version/help failed`（CI 该检查为非阻塞，`L2_RESULT` 保持 skip）；在
  `conanrun` 环境/PYTHONPATH 下入口脚本功能正常（`--version` → `2026.5.8`）。

---

**适配结束**: 2026-10-13
**最终状态**: built
---

**编译结束**: 2026-10-13 15:15
**最终状态**: built
