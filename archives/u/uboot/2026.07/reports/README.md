# reports/ — 随档验证报告说明

本目录的 `conan-verify-report.md` 为平台官方工具（`ohc-run.py
conan-verify uboot 2026.07`）的**原样输出**，随档提交、不做人工编辑。
以下为对报告中「跳过 / 未识别门禁」与量化记录的补充说明（对应检视
意见 P2 的「显式说明」路线）：

- **G0「构建系统: unknown」**：工具未识别 Makefile-only 工程、预查询
  跳过。实际构建系统为 makefile（`2026.07/manifest.yaml` 的
  `build.system` 明示；G2 的 `conan create` 实跑即用上游 Makefile
  全链构建）。
- **G2 日志路径**：报告所引 `conan-create.log` 是设备侧构建期工作
  日志；本仓惯例不随档提交 `.log` 文件（树内零 .log）。conan create
  成功在 MR 内可核凭据 = `notes.md`「验证记录 / 当前配方全链
  （run8）」一节（`CONAN_CREATE_RC=0`、919/919、耗时与引用产物回填）。
- **G4 / L2 / L4 / L5 跳过**：工具在「预置缓存命中」形态下的既有
  行为（无法定位程序包 ID / 无 cache 路径）——G2 已实跑完整
  test_package 全链，测试结果以 `notes.md` 记录为准。
- **量化记录（报告未含）**：终版 run8（2026-10-10）`conan create`
  `CONAN_CREATE_RC=0`、总耗时 4826 秒，test_package 四步全过：
  919/919 子测试（`PASS=919 FAIL=0 SKIP=0`）。本报告 Date
  2026-10-10T22:27:04 对应 run9 conan-verify 复跑（Verdict: PASS、
  约 700 秒，缓存命中形态；见 `notes.md` run8 节尾）。
- **历史记录口径**：2026-10-04 的八门禁复核（`ELAPSED_SECONDS=599`）
  属 16 补丁无 SDL 形态，为历史记录（见 `notes.md` 历史构建记录节），
  不再作为终版依据。

**Verdict 限定语**：报告 Verdict PASS 覆盖实际执行的门禁；G0 预查询、
G4 程序包 ID、L2/L4/L5 五项因上述工具限制 / 缓存形态跳过或未识别，
均已逐项披露如上。
