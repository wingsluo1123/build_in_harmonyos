# toot

Mastodon CLI client.

`toot` is a command-line client for the [Mastodon](https://joinmastodon.org/)
social network. It lets you post statuses, read timelines, manage accounts,
follow requests, lists, polls and tags, and launch an interactive terminal UI
(`toot tui`) built on urwid.

Pure Python package — no C/C++ compilation step. Built with setuptools +
setuptools_scm, installed via pip.

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 0.52.1  | built  | Pure Python, setuptools/setuptools_scm build; version pinned via `SETUPTOOLS_SCM_PRETEND_VERSION` |

## Runtime dependencies

From the Conan registry (declared in `conanfile.py` `requirements()`):

| Package | Version | Role |
|---------|---------|------|
| beautifulsoup4 | 4.15.0 | HTML 解析（`toot.utils.parse_html`） |
| click | 8.4.2 | CLI 框架（`toot.cli`） |
| python-dateutil | 2.9.0.post0 | 时间解析（`toot.utils.datetime`） |
| requests | 2.22.0 | HTTP 客户端（`toot.http`） |
| wcwidth | 0.2.12 | 终端宽字符宽度（`toot.wcstring`） |

Filled from PyPI inside `build()`（制品仓暂无对应配方，见 `notes.md` 依赖决策）:

| Package | Version | Role |
|---------|---------|------|
| urwid | 3.0.2 | 终端 TUI（`toot tui`） |
| tomlkit | 0.15.1 | `settings.toml` 解析（`toot.settings`） |
| pysocks | 1.7.1 | `requests[socks]` 代理支持 |

## Usage

```bash
conan install --requires=toot/0.52.1 -g VirtualRunEnv
source conanrun.sh
toot --version
toot --help
```

## Platform

HarmonyOS PC / aarch64 (`settings.os=OHOS`, `settings.arch=armv8`).
