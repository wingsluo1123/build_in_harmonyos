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
  - 上游测试 489 = 477 passed + 9 failed + 1 skipped + 0 errors + 2 timeout（9 failed/2 timeout 为外部依赖边界：音频 portaudio/libsndfile、Playwright、help extra numpy 冲突）
  - **默认核心测试 test_voice 5 个仍失败**（portaudio/libsndfile 制品不可安装）
  - 冷 CONAN_HOME source() 下载连续三次卡死（环境待 CI 验证）
