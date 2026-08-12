# aider

Aider is AI pair programming in your terminal.

- 上游：https://github.com/Aider-AI/aider（Apache-2.0）
- PyPI 分发名：`aider-chat`（纯 Python PEP 517/setuptools，console entry `aider = aider.main:main`）
- 鸿蒙适配：知识库扩展任务（Issue #2006），路径 B candidate
- 归档：`archives/a/aider/0.86.2/`

## 版本

- 0.86.2（status=built，仅表示 Conan 构建/验证结果；**finish 未执行**，不视为正式适配完成）
  - conan-verify：本轮补丁更新后 **PASS**（G1-G4、L2/L4/L5）；test_package **31/31 passed**
  - 依赖重基补丁：requirements.txt + requirements-help.txt 16 项 pin（0001-requirements-ohos-rebase.patch）
  - 上游测试 489 = 482 passed + 4 failed + 1 skipped + 0 errors + 2 timeout（4 failed/2 timeout 为 optional-extra 外部依赖边界：Playwright 无包、help extra numpy 冲突）
  - **默认核心测试全部通过**（test_voice 8/8：portaudio 19.7.0 经 cmd-pkgs 预编译包 + soundfile wheel 内置 libsndfile）
  - 冷 CONAN_HOME source() 下载连续三次卡死（环境待 CI 验证）
