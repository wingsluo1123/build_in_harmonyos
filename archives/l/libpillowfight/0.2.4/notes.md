# libpillowfight 0.2.4 适配笔记

## 库信息
- **名称**: libpillowfight
- **版本**: 0.2.4
- **语言**: C (C99/C11)
- **构建系统**: CMake
- **上游仓库**: https://github.com/openpaperwork/libpillowfight
- **许可证**: GPL-2.0-only

## 语言确认
- 纯 C 库（12 个算法源文件：_ace.c/_blackfilter.c/_blurfilter.c/_border.c/_canny.c/_compare.c/_gaussian.c/_grayfilter.c/_masks.c/_noisefilter.c/_sobel.c/_swt.c + util.c/_version.c），CMakeLists.txt 为主构建。
- Python 文件为绑定层（setup.py 构建 pypillowfight 扩展）与 pytest 测试基础设施，非库主体。
- 平台宏：NO_PYTHON（排除 Python 绑定代码路径），_GNU_SOURCE（qsort_r，OHOS 支持）。
- 无第三方库依赖，仅依赖系统 libm 和 libpthread。

## _version.h 动态生成
上游构建系统要求 `src/pillowfight/_version.h` 存在，定义 `INTERNAL_PILLOWFIGHT_VERSION` 宏（`_version.c` 的 `pf_get_version()` 返回该宏）。源码包与官方归档均不含该文件（上游由 Makefile `make version` 生成）。在 conanfile.py 的 `build()` 中 CMake 配置前动态生成。

## 上游 pytest 测试说明（R03 已真实运行）
上游测试使用 pytest 框架（Python，unittest 风格），共 13 个测试文件（tests_*.py）+ 测试图片资源。
R03 在**设备端真实运行**全部 13 入口：python3 3.12.9 + pytest 9.1.1；测试依赖 Pillow 12.3.0
（OHOS 无 wheel，经制品仓 libjpeg/10 提供 jpeglib.h/libjpeg.a 后源码构建安装成功，JPEG 解码验证通过）；
pypillowfight 绑定在本机编译加载（运行时 qsort_r 符号缺口由 LD_PRELOAD shim 提供 GNU 语义，不改上游源码）。
结果：15 用例，2 通过（tests_canny、tests_sobel）/ 13 失败（全部 AssertionError 字节等值断言，
像素级 ±1~2 浮点/JPEG 精度漂移，归属环境，非适配补丁/依赖缺失/未尝试）/ 0 跳过。
消费者测试（test_package）与鸿蒙特有测试仍作为 C 库交付验证，回归通过。

### R04 漂移源隔离与对齐（15 用例，2 通过 / 13 失败，残余交分析端裁决）
五项隔离实验结论（日志见终态证据）：①有损/无损对照分类表（纯滤波器为量化边界翻转，ace/all
为种子采样漂移，swt 为算法级差异）；②-ffp-contract=off 重建后漂移完全不变（证伪 FMA 收缩）；
③设备 libm 的 exp/log 与正确舍入值 0 ulp（证伪 libm）；④同像素 libjpeg/10 vs libjpeg-turbo
编码差异 129956 px/max 6，同一参考 jpg 两解码器字节不同（编解码器选择是边界翻转主源）；
⑤输入/期望图解码确定性全部成立。补充：设备 musl rand 序列与 glibc 参考不一致 → ace 大漂移根因。
对齐修复（run 环境级，不入库源码/配方）：**libjpeg-turbo 3.2.0 重建系统 Pillow**（纯滤波器
TEST_DIFF -95%）+ **glibc 语义 rand/srand shim**（ace 5.92M→1.45M px）+ qsort_r shim 沿用。
残余 13 失败为字节级等值断言对跨环境参考图的量化边界敏感性，穷尽任务规定实验与对齐手段后仍
无法逐字节复原，附完整证据链交分析端裁决；未改上游测试/参考图/断言。

### R05 参考图自指纹与统一基线（最终冲刺轮，仍 2/15，残余交最终裁决）
参考图自指纹实验（穷举候选编解码器）：turbo 1.5.3/2.0.6/2.1.5.1/3.1.1 网络不可达（尝试证据已记录）；
turbo 3.0.4（制品仓 + venv Pillow）、turbo 3.2.0（系统 Pillow）、libjpeg/10（制品仓 cjpeg）完成扫描
**0/15 命中**（解码→重编码字节与参考文件全字节面不同，最近差异≈文件大小）；IJG 6b/8d/9e 源码
已下载（sha256 记录）并构建，运行期失效（Unrecognized input file format）已记录。结论：JPEG
有损编解码不可逆，"自指纹逐字节复现"判据对任何编码器结构性不可达，无法锁定生成参考图的版本。
统一基线：turbo 3.2.0 编解码器 + glibc rand 家族 shim（rand/srand/random/srandom 逐值校验）+
qsort_r shim + 默认编译参数；编码参数核对（默认 save==quality 75）与解码确定性复验通过。
全量复跑 15 用例 2 通过/13 失败/0 跳过（TEST_DIFF 与 r04 对齐后持平：纯滤波器 2k~12k、gaussian
108k、ace 1.45M、swt 87k+78k）；残余失败漂移量化、空间分布（弥散/全帧）、函数级定位证据链完整，
交分析端最终裁决。

### R06 2018 历史栈复现与上游测试环境敏感性取证（2/15，交最终裁决）
依据分析端取证的 issue #15（参考图由 PyPI wheel Pillow 5.0 时代生成）复现 2018 历史栈：Pillow 5.0.0
sdist（官方 sha256 校验一致）与 6.0.0 构建成功，但本设备 python 3.12 上**运行期不可用**（Pillow 5.0
C 扩展 ABI 段错误——PY_SSIZE_T_CLEAN 编译修复不消除运行期崩溃；Pillow 6.0 JPEG 解码失效）；
libjpeg-turbo 2.0.6（-fPIC）构建成功、1.5.3 构建不可达（cmake CMP0022 政策 + autotools config.status
awk 权限，失败原文已记录）；5.0+turbo 2.0.6 配对构建失败（conflicting types）。oracle（tests_blackfilter）
判别：无命中候选——参考环境（2018 Pillow + python 3.6 时代）在本平台结构性不可复现。**上游测试环境
敏感性取证**（回应"通过率太低"审查质疑）：issue #15（Fedora 系统 Pillow 大量失败、维护者确认参考图
绑定生成环境、virtualenv 才通过、commit 9719e414 因环境变更重生成参考图）、Debian 0.3.1
"skip failing tests on i386"、Ubuntu LTO 下 canny 失败先例——本库 2/15 与上游生态公认的测试环境
敏感性缺陷同类，失败归属上游参考图环境锁定（平台/上游归属）。

## 构建问题与修复
- 0.2.4 官方归档为 GitHub tag tarball，sha256=32933926d9e16c9575c262188eec98c264c4a9505b6674754fff85d1e59cd8dd（与任务要求一致，tag 0.2.4 → commit 3a7ebba75f4c060ac1707900bd8891e8d200b1c6）。
- 初始构建无需补丁；CMake 自动识别 OHOS 平台；`-DNO_PYTHON` 确保只编译 C 库。
- conanfile 使用 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 规避 cmake ≥4 对上游 `cmake_minimum_required(3.0)` 的策略版本报错（0.3.1 先例）。
- 与 0.3.1 配方的差异：源码 URL 使用任务指定的 GitHub 官方归档；layout 使用默认 `cmake_layout`（0.2.4 tarball 的 CMakeLists.txt 位于根目录）；test_package 的 `test()` 实际运行消费者与鸿蒙特有测试二进制（0.3.1 仅 `file` 检查，任务要求实际调用 API 且可失败）。

## 语言预检（lang-preflight）偏差记录
- 初次 lang-preflight（默认任务语言 cpp）因顶层 setup.py 存在按 manifest 优先级判 `detected_language=python` 并自动写 env_unsupported 终态（source_stats: python:17, c:15, bash:1，占比 53% < 70% 阈值）。
- 复核结论：库主体为 C（CMake 主构建 + 12 个 C 算法源文件），python 为绑定层（setuptools Extension）与测试设施；R47 边界规则明确"绑定包按主体语言判""辅助脚本不算主体"；同库 0.3.1 已按纯 C 适配并合入 main（manifest language: C）。
- 处置：按证据判 C（cpp 兼容族，任务默认 cpp 匹配），继续 C 适配；终态报告如实附带 lang-preflight 原始输出与复核证据。

## 测试
- 上游测试（R03 设备端真实运行）：13 个 pytest 入口，15 用例 2 通过 / 13 失败 / 0 跳过；
  失败均为 AssertionError 字节等值断言（像素级浮点/JPEG 精度漂移，环境归属）；逐入口台账见
  reports/test-report.md 与 R03 证据台账。
- 消费者测试 test_consumer：调用 pf_get_version() 断言 == "0.2.4"（回归复跑通过）。
- 鸿蒙特有测试 test_harmonyos：OHOS aarch64 目标实际调用 pf_ace() 处理 8x8 合成双色位图，
  断言输出结构正确且通道在 [0,255]（回归复跑通过）。

## 适配路径
- 路径 A：常规基础适配（无补丁），知识沿用既有条目。
- 配方文件：conanfile.py, conandata.yml, manifest.yaml, notes.md, test_package/

**编译结束**: 2026-09-29
**最终状态**: built
---

**编译结束**: 2026-09-29 11:06
**最终状态**: built
