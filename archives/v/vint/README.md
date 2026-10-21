# vint

静态分析 **Vim script（viml）** 的工具：报告语法与风格问题（未定义变量、不推荐的命令、缩进/空白、
缺失 `scriptencoding` 等），可接入 CI 对 `.vim` 脚本做 lint。
上游：<https://github.com/Vimjas/vint>

| 版本 | 说明 |
|------|------|
| [0.3.21](0.3.21/notes.md) | 当前适配版本（HarmonyOS PC / ohos-aarch64） |

## 这个包提供什么

- `bin/vint` —— 命令行入口（`vint --version` → `0.3.21`；`vint <file.vim>` 输出问题列表）
- `python/` —— vint 本体与随包运行时依赖（PyYAML / ansicolor / chardet / setuptools）

## 适配要点（细节见 0.3.21/notes.md）

1. **运行时依赖必须钉 `setuptools<81`**：vint 直接 `import pkg_resources` 却没声明该依赖，
   而新版 setuptools（84.0.0）已移除 `pkg_resources` —— 装最新版会连 `import vint` 都失败。
2. **本体用 `--no-deps` 安装**：`setup.py` 里 append 的 `enum34`/`pathlib`/`typing` 是 py2 backport，
   在 py3.12 下会遮蔽标准库同名模块。
3. **命令脚本自建**：`pip install --target` 因目标根目录存在同名 `vint/` 包目录而不会生成 `vint`
   脚本；`vint` 也没有 `__main__`（`python -m vint` 不可用）→ 按上游 `entry_points` 生成 `bin/vint`。
4. **上游用例真跑**：`272` 个（unit/integration/acceptance）→ `271 passed, 1 skipped`（**271/271，100%**）。
   上游 tox 把 pytest 钉在 3.3.2（py3.12 装不上）→ 用现代 pytest 跑**同一套用例**。
5. **测试环境三处适配**（不改上游）：补回 `bin/vint` 可执行位、造 `python` shim（其 shebang 是
   `#!/usr/bin/env python`）、静音 Python 警告（否则告警会污染 CLI 输出的前缀断言）。
