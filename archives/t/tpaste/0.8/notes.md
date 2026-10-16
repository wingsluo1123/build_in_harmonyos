# tpaste 0.8 适配笔记

## 源码来源（需特别说明）
- tpaste 没有独立上游发布包。`0.8` 是 **Alpine Linux 包版本**：脚本由 aports 的 `main/tpaste/APKBUILD`
  在 `package()` 里用 `printf` 生成（`pkgver=0.8`、`license=GPL-2.0-only`、`depends=curl`、`arch=noarch`、`options=!check`）。
- 官方出处（固定 commit）：`https://gitlab.alpinelinux.org/alpine/aports/-/blob/3f28b79bb6e626953e3786be38349719ebd1789d/main/tpaste/APKBUILD`
- conandata 下载同 commit 的 raw APKBUILD，取自 GitHub 官方只读镜像 `alpinelinux/aports`：
  gitlab.alpinelinux.org 对 Conan 的 User-Agent 返回 HTTP 418（实测 urllib UA 200 / `Conan/2.29.1` UA 418），GitHub 镜像三种 UA 均 200。
  三个来源（GitLab raw、GitHub raw、git.alpinelinux.org plain）下载内容 sha256 均为 `5a50dbf249186b2ce5c954dcf45d96d13f72f9018a1f8dca9fb4769c671d2f2b`。
- APKBUILD 的 `subpackages="dpaste ix"` 是另外两个 Alpine 子包，不属于 tpaste，本 PR 不收。

## 语言预检
- 只读判定 `detect_language` → `other`（无可统计源文件，无 manifest）。依据：源为 shell 语法的 APKBUILD，生成的脚本 `#!/bin/sh`。
- 这是 Shell 项目，大赛接受；`lang-preflight tpaste 0.8 --src <dir> --lang other` 如实申报，exit 0。

## 编译步骤
- 无构建系统、无需交叉编译（脚本与架构无关）。`init-build` 对单文件源报 `解压失败: not a gzip file`，改用 `init-archive … shell` 建骨架。
- 配方 `build()`：解析 APKBUILD 的 `pkgver`（必须等于 conan version）与 `url`，按 `package()` 的模板生成
  `#!/bin/sh\n\nexec curl -sSF 'tpaste=<-' https://tpaste.us`（无结尾换行，与上游 printf 一致），`sh -n` 语法检查。
- `package()`：装到 `bin/tpaste`（755），许可证 GPL-2.0 文本装到 `licenses/COPYING`。
- `requires("curl/8.15.0")`：运行时 exec curl。W0：`curl/8.15.0` 配方与 OHOS 二进制均在 ohpcd（`conan install --requires=curl/8.15.0` 成功），其 `openssl/3.5.6.1`、`zlib/1.3.1.1` 已发布。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 解压失败 | 源是单文件 | 用 `init-archive` 建骨架 |
| 2 | gitlab raw 在 Conan UA 下 418 | 反爬（E347） | 用 GitHub 官方镜像同 commit raw |
| 3 | conan-verify G1 要求 `export_sources`/`apply_conandata_patches` | G1 为字符串匹配 | 加无操作的统一样板（本版本无补丁） |

## 源码修改
无补丁。

## 依赖版本
curl/8.15.0（运行时）。

## 上游测试清点（R51）
- 上游 tests/ 目录 0，ctest/pytest 注册 0；APKBUILD 声明 `options="!check"`。上游测试 N=0，无可运行项。
- 补全：`test_package/test_tpaste.sh` 15 条检查（见下），为鸿蒙特有测试 / 消费者用例。

## 验证结果
- `conan-verify`：G1–G4 通过，`conan create`（profile `ohos-aarch64`）含 test_package 通过。
- 消费者用例（`test_package/conanfile.py` 在 `conan create` 的 `test()` 中运行，同时本地对缓存里的包再次实跑）：
  `sh test_tpaste.sh <缓存包>/bin/tpaste` → `passed=15 failed=0`，退出码 0。
- 用例内容：运行**打包出的** `tpaste`，PATH 前置确定性假 curl，断言 curl 收到的 argv 恰为 `-sSF` / `tpaste=<-` / `https://tpaste.us`、
  stdin 字节级转发（含无结尾换行与特殊字符、空输入）、curl stdout 透传、curl 退出码 22 原样传出、位置参数不注入、缺 curl 时失败；
  另逐字节比对脚本与 APKBUILD printf 预期输出。
- 局限：脚本是与架构无关的 POSIX sh，本地用构建机 `sh` 实跑；**未在 OHOS aarch64 上实跑**（x86 runner 无法运行动态 OHOS 产物，E544），
  真实 curl 到 tpaste.us 的网络调用未测试（外部 HTTPS 服务，用假 curl 观测调用，不访问网络）。

## 注意事项
- 运行依赖外部 HTTPS 服务 tpaste.us，服务可用性不属于适配范围。
- 软件级 `commands.json`：`binary:false`（脚本，非 ELF）。
---

**编译结束**: 2026-10-08 14:24
**最终状态**: built
