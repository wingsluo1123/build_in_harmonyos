# ddate

Discordian 日期转换器 — 将公历日期转换为 Discordian 历法日期（YOLD 纪年）。

ddate 是一个轻量级终端工具，灵感来自《伊鲁敏纳特斯三部曲》中的 Discordian 宗教历法。它将当前系统日期或指定日期转换为 Discordian 格式，如 "Today is Sweetmorn, the 30th day of Confusion in the YOLD 3192"。

## 编译指导

ddate 使用 CMake 构建系统（非 autotools）。在 HarmonyOS/OpenClaw 平台编译时需注意：

- CMake 4.x 需要添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 参数（CMakeLists.txt 声明了 `cmake_minimum_required(VERSION 2.8)`）
- 作为终端工具，必须静态链接（R26）：`-DCMAKE_EXE_LINKER_FLAGS="-static"`
- 无外部依赖，仅使用 musl libc
- 无 CTest 测试套件（make check 不可用），通过 smoke test 验证

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [0.2.2](./0.2.2/) | published | 2026-06-26 |
