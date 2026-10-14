# tubeup

`tubeup` 是一个纯 Python 命令行工具：用 **yt-dlp** 下载视频/音频，把下载产物与元数据（标题、上传者、标签、字幕、缩略图、`.info.json` 等）整理后用 **internetarchive** 库上传到 **archive.org**，用于互联网视频的长期归档。

## 功能概述

- 支持 yt-dlp/yt-dlp 兼容的任意站点 URL（YouTube、Twitch、SoundCloud 等）
- 自动生成 archive.org item 元数据：`title` / `creator` / `collection` / `date` / `year` / `subject` / `originalurl` / `licenseurl` / `scanner`
- URL 标识符净化（`sanitize_identifier`）、空文件清理、下载中断残留（`.part`/`.ytdl` 等）检测
- CLI 参数用 docopt 从 `__main__` docstring 解析：`--metadata` / `--cookies` / `--proxy` / `--username` / `--password` / `--use-download-archive` / `--dir` / `--ignore-existing-item` 等
- 入口点：上游 `[project.scripts] tubeup = "tubeup.__main__:main"`，本配方打包为 `bin/tubeup`

## OHOS 适配

- **纯 Python**：上游为 setuptools 项目，无 C/C++ 扩展；按本仓 `python-require` 模板打包——把 `tubeup/` 复制到 `lib/python3.12/site-packages/tubeup/`，并生成 `bin/tubeup` 入口脚本（注入 site-packages 到 `sys.path` 后调用 `tubeup.__main__:main`）。
- **依赖**：`internetarchive` 与 `docopt` 声明为 Conan requires（ohpcd 已有发布版本）。
- **yt-dlp 的例外处理**：上游硬依赖 `yt-dlp`，但其 Conan 包**尚未发布**到 ohpcd 制品仓。按 R36 不能声明未发布的依赖（CI L0i / PR 前置 PF4 会拦截），因此：
  - `patches/0001-guard-optional-yt-dlp.patch` 把 `tubeup/TubeUp.py` 顶层的 `from yt_dlp import YoutubeDL` 改为可选导入；
  - 仅在真正进入下载流程（`get_resource_basenames`）时抛出明确的 `RuntimeError`，提示需要安装 yt-dlp；
  - CLI 解析、collections/license 判定、yt-dlp 选项生成、archive.org 元数据构造、标识符/文件工具函数等**全部保持可用**。
  - 待 `yt-dlp` Conan 包发布后，可去掉该补丁并把 `yt-dlp` 加入 `requirements()`。
- **文件名安全**：`restrictfilenames=True` 保留启用，避免 HMDFS 上特殊字符文件名问题。
- **已知差异**：无 yt-dlp 时无法下载（受控报错），不影响本包导入与元数据能力。

## 依赖关系

| 类型 | 依赖 | 状态 |
|------|------|------|
| 构建/打包 | `jsonpatch==1.35`、`jsonpointer==3.2.1`（`pip --target` 打入本包） | 无 Conan 包，见上文 |
| 运行（Conan requires） | `internetarchive/5.10.1`、`docopt/0.6.2`、`tqdm/4.70.1` | 已发布 |
| 运行（可选） | `yt-dlp`（默认 extra: brotli/certifi/mutagen/pycryptodomex/requests/urllib3/websockets，curl-cffi extra） | ohpcd 未发布，见上文 |

## 参考资料

- 上游仓库：https://github.com/bibanon/tubeup
- PyPI：https://pypi.org/project/tubeup/
- internetarchive 库：https://github.com/jjjake/internetarchive
- yt-dlp：https://github.com/yt-dlp/yt-dlp
