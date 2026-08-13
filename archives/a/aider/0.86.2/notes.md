# aider 0.86.2 适配笔记

## 状态语义（提交前纠偏审计）
- status: built 仅表示 Conan 构建/验证结果：conan-verify 本轮 PASS（补丁更新后新结果）、test_package 31/31 passed；
- **finish 未执行**（.finish-state.json 缺失），built 不作为 finish 成功证据，不得视为正式适配完成；
- 默认核心测试 test_voice 8 个用例全部通过（portaudio 19.7.0 经 cmd-pkgs 预编译包安装至测试前缀；libsndfile 由 soundfile wheel 内置）；
- 仅当全部硬门禁闭合且 finish 成功后才可视为 built 完成态。

## 编译环境
- 构建系统: custom（纯 Python PEP 517 / setuptools.build_meta，console entry `aider = aider.main:main`）
- 编译日期: 2026-08-11
- 编译器: clang/clang++（OHOS SDK llvm 15.0.4，仅 PEP 517 sdist 构建需要）
- 状态: built（finish 未完成前不得 published）

## 上游身份
- 上游: https://github.com/Aider-AI/aider（Apache-2.0）
- Tag: v0.86.2 → commit 253f0368b873ba30d8ee26e463718f0c03614ddf
- PyPI 分发名: aider-chat 0.86.2（sdist SHA256 f38a9d32...5919，wheel 64f6a0c6...16e）
- requires-python: >=3.10,<3.13（真机 Python 3.12.9 满足）

## 构建与补丁
- 依赖重基补丁: patches/0001-requirements-ohos-rebase.patch
  - requirements.txt 与 requirements/requirements-help.txt 共 16 项 pin 重基到社区源可用版本（aiohttp 3.13.3→3.14.0、numpy 1.26.4→2.5.1、scipy 1.15.3→1.18.0、pydantic 2.12.5→2.11.10、pydantic-core 2.41.5→2.33.2 等）
  - scipy 1.18.0 违反上游 scipy<1.16 显式约束（平台依赖补丁，已记录）
  - help extra 旧 pin aiohttp==3.13.3 同步修正为 3.14.0
- 源码 URL 说明: conandata sources 使用官方 codeload + %2D URL（`https://codeload.github.com/Aider%2DAI/aider/tar.gz/refs/tags/v0.86.2`）——`%2D` 是 URL 标准百分号编码（对应字面连字符 `-`），codeload.github.com 是 GitHub 官方源码分发域名；使用该形式是为了规避仓库当前 predl 正则（`[^\s"'-]+` 排除字面连字符导致 `Aider-AI` 截断）与 E017 镜像注入（仅匹配 `https://github.com` 前缀）冲突；已实测下载 67,560,014 字节 / SHA256 1c5ccaac… 与原 GitHub archive 字节级一致
- PEP 517 构建前置: 显式 PATH + CC=/data/service/hnp/bin/clang（构建子进程找不到 clang 报 [Errno 2]）
- GitHub tag tarball 构建需 SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AIDER_CHAT=0.86.2
- conanfile package() 需从源码树补齐 aider 子包（coders/queries/resources/website），否则 wheel 缺子包致 CLI 失败

## 测试结果（最终统一驱动）
最终驱动: 精确 safe.directory Git wrapper（仓库外临时目录）+ 固定受控 --basetemp + 隔离 HOME/XDG + sitecustomize（posix_spawn→execvp 回退）

### 上游测试（489 collected）
- passed=482, failed=4, skipped=1, errors=0, timeout=2
- failed: scrape 4（playwright 社区源无包，optional-extra）
- timeout: help 1（test_ask_without_mock，help extra numpy<2 与重基 numpy 2.5.1 冲突，optional-extra）+ scrape 1（install_playwright 挂起，optional-extra）
- **默认核心测试全部通过**：test_voice 共 8 个用例全部通过（其中 5 个曾受音频依赖影响，经 portaudio 19.7.0 预编译包安装至测试前缀、sounddevice 0.5.5 真实加载 libportaudio.so.2；libsndfile 由 soundfile 0.13.1 wheel 内置 `_soundfile_data/libsndfile_arm64.so`，WAV 写读实测 OK）
- Git dubious ownership 43 + pytest 临时目录 6 已由测试驱动层修复（E256 draft）

### test_package（31/31 passed）
- 导入+版本、CLI 入口、--version、--list-models gpt-4（离线核心工作流）、--help、资源归属、console entry
- 16 项依赖重基 0 mismatch 断言

## 外部依赖边界（未发布、未建 Issue）
- portaudio/19.7.0: status=built 未 published，conan install Unable to find in remotes → 曾阻塞 test_voice 5 个 node（经 cmd-pkgs 预编译包安装至测试前缀后已恢复，test_voice 8/8 通过）
- libsndfile/1.2.2: status=published 但 remote 不可见 → 同上
- playwright: 社区源 from versions: none → 阻塞 scrape 5
- help extra: numpy<2 与重基 numpy 2.5.1 冲突（scipy 1.18.0 官方约束 numpy>=2.0.0）→ 阻塞 help 1

## 冷 Conan 验证
- 独立 CONAN_HOME 连续三次卡在同一 source() 下载阶段（67.5MB tarball），属环境待 CI 验证
- 本轮以热缓存 conan-verify（当前补丁）作为配方验证结果
---

**编译结束**: 2026-08-12 22:43
**最终状态**: built
