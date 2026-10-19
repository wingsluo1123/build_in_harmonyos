# 测试报告 — libwraster 0.96.0

## 1. 基本信息

| 项 | 值 |
|---|---|
| 软件 / 版本 | libwraster 0.96.0 |
| 上游 | WindowMaker 0.96.0（`wrlib/` 子目录，window-maker/wmaker） |
| 来源 | https://github.com/window-maker/wmaker/releases/download/wmaker-0.96.0/WindowMaker-0.96.0.tar.gz |
| sha256 | 4fe130ba23cf4aa21c156ec8f01f748df537d0604ec06c6bbcec896df1926f6d |
| profile | ohos-aarch64（os=OHOS 6.0 / arch=armv8 / clang 15 / Release / 静态库） |
| 日期 | 2026-10-15 |
| 归档 | `archives/l/libwraster/0.96.0` |

## 2. 构建验证（W3 本地 CI，阻塞门禁）

- 入口：`ohc-run.py finish libwraster 0.96.0 published`（step [5/10] → `ci/conan/build_and_test.sh`）
- 结果：**exit_code = 0**（`archives/l/libwraster/0.96.0/.ci-result.json`）
- 完整性凭据：`integrity_hash = e60814783896dabe`，`log_sha256 = cec761e34f17dd94988af35a69cb094401adc0884a093f080c311c30a60532af`
- 完整日志：`.ci_logs/conan_build_libwraster_0.96.0.log`

## 3. 包内自动测试（Conan `test_package/`，L1）

`conan create` 在 W3 流程中真实构建并**执行**了消费端测试
（日志第 664–684 行：`======== Testing the package: Executing test ========` →
`RUN: ./libwraster_test`），测试二进制先经 ELF codesign
（`add codesign section success`）后运行。

```
# assertions=15 failures=0
```

| # | 断言 | 覆盖的真实 API |
|---|------|----------------|
| 1 | `RCreateImage(64,64,1)` 非 NULL | RCreateImage |
| 2–3 | 图像宽高 = 64 | RImage 结构（公开字段） |
| 4–5 | 清屏为红后可读回红色 | RClearImage / RGetPixel |
| 6–7 | 写蓝点后读回蓝色 | RPutPixel / RGetPixel |
| 8–12 | 缩放为 32×32、中心像素保持蓝色 | RScaleImage / RGetPixel |
| 13 | 释放缩放图不崩溃 | RReleaseImage |
| 14 | 错误码文案非空 | RMessageForError |
| 15 | 释放原图不崩溃 | RReleaseImage |

结论：**15/15 通过，0 失败**。测试真实链接 `libwraster.a` 并调用被测包的公开
API，非空壳测试（无仅打印/仅 `return 0` 的桩）。

## 4. 上游测试清点（R51）

**清点结果**：上游 `wrlib/tests/` 存在 4 个 `noinst_PROGRAMS`（`wrlib/tests/Makefile.am`）：

| 程序 | 源文件 | 性质 |
|------|--------|------|
| testdraw | testdraw.c | X11 交互式演示（draw 示例） |
| testgrad | testgrad.c | X11 交互式演示（渐变色） |
| testrot | testrot.c | X11 交互式演示（旋转） |
| view | view.c | X11 图像查看器 |

配套素材：`test.png`、`tile.xpm`、`ballot_box.xpm`。

**是否被上游自动化运行**：否。`wrlib/Makefile.in:845` 的
`check: $(BUILT_SOURCES)` 没有任何 `TESTS` 注册，即上游**没有自动化测试套件**
（4 个程序均为 `noinst_PROGRAMS`，只编译不执行）。

**实际运行尝试与结论**：
- 4 个程序的源文件均调用 `XOpenDisplay`（testdraw.c / testgrad.c / testrot.c / view.c），
  属于需要活跃 X server 的**交互式**程序：无断言、无有意义的退出码语义。
- 本机为 HarmonyOS PC 目标环境：`DISPLAY` 未设置，且不存在 `/tmp/.X11-unix`
  （本机无 X server）；此外 4 个程序未在本配方的构建目标内产出
  （配方只构建 `wrlib/` 库本体及其安装目标）。
- 因此**无法运行**：这是"需要活跃 X server 的交互式图形程序 + 目标平台无 X
  server"的具体技术原因，非"没环境"的托词。
- 上游测试计数：**0 项可自动化运行的测试**（4 个程序不计入）；
  本包自建 `test_package` 补足 **15 项断言**（见第 3 节）。

## 5. 配方验证（conan-verify）

| 门禁 | 结果 |
|------|------|
| G0 预构建风险评估 | ✅ PASS（知识命中 E490，配方已按 chmod 0o755 处理） |
| G1 配方完整性 | ✅ PASS |
| G2 conan create | ✅ PASS |
| G3 系统同名库隔离 (R26) | ✅ PASS（无 `bin/`，纯库包；无系统同名库冲突） |
| G4 产物完整性 | ✅ PASS |
| L2 / L4 / L5 | ⏭️ 跳过（验证器报告标注"无 cache 路径"，G4 同时报"无法找到程序包 ID"） |

> L2/L4/L5 的跳过是验证器侧未解析到程序包 ID 所致，**不作绿灯声明**；
> W3 全流程（含 L0/JC 垃圾门禁与 L1 实测执行）已 exit 0 通过。

## 6. 交付物

```
include/wraster.h
lib/libwraster.a
lib/pkgconfig/wrlib.pc
licenses/COPYING
share/locale/
```

## 7. 结论

- 构建：W3 本地 CI exit 0（含 conan create + 消费端测试实跑）。
- 测试：包内 15/15 断言通过；上游无可自动化运行的测试（4 个交互式 X 程序，
  已逐项给出不可运行的具体技术原因）。
- 配方：G0–G4 全部 PASS。
