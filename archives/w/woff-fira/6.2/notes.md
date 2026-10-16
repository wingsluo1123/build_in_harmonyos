# woff-fira 6.2 适配笔记

## 基本信息

- 软件：Fira Code WOFF webfont
- 上游版本：6.2
- 来源：<https://github.com/tonsky/FiraCode/releases/download/6.2/Fira_Code_v6.2.zip>
- 源码 SHA-256：`0949915ba8eb24d89fd93d10a7ff623f42830d7c5ffc3ecbf960e4ecad3e3e79`
- 许可证：SIL Open Font License 1.1（保留上游版权和完整许可证）
- 类型：预构建 WOFF 字体数据包，无编译、无 Conan 依赖

## 语言预检

上游发行包只含预构建字体、CSS、样例页和说明文件；它不含待编译源码。默认 `cpp` 预检检测为 `other` 并退出 2。按资源包预检口径使用 `--lang other` 后，预检通过（退出 0）。此分类与交付物一致；配方不引入其他语言的工具链，也不编译源码。实际证据由本次 `lang-preflight` 执行记录保留。

## 包含文件

- `FiraCode-Light.woff`
- `FiraCode-Regular.woff`
- `FiraCode-Medium.woff`
- `FiraCode-SemiBold.woff`
- `FiraCode-Bold.woff`
- `FiraCode-VF.woff`（可变字重）
- 上游 OFL-1.1 许可证

Conan 安装目录为 `share/fonts/woff-fira/woff/`，通过 `cpp_info.resdirs` 暴露。HarmonyOS PC 应用可在 WebView 中用 CSS `@font-face` 或 `FontFace` API 加载。该包不会把 WOFF 注册为 HarmonyOS 全局原生字体。

## 上游测试清点（R51）

上游 release zip 共 23 个条目，只有 `ttf/`、`variable_ttf/`、`woff/`、`woff2/` 资源目录以及 CSS、样例页和 README；没有 `test/` 或 `tests/` 目录、测试注册文件或构建系统。发行包可运行的上游自动化测试为 **0**，因此无上游测试可执行。测试覆盖由本包的 Conan 消费者测试和 HarmonyOS PC WebView 实测提供。

## 测试

| 测试项 | 用例数 | 实际运行 | 结果 |
| --- | ---: | ---: | --- |
| 上游发行包自动化测试 | 0 | 0 | 上游发行包没有可运行测试 |
| Conan 消费者测试 | 1 | 1 | 1/1 通过（100%） |
| HarmonyOS PC 浏览器实测 | 1 | 1 | 1/1 通过（六个字体均加载并绘制） |

本地 CI 通过仓库 `ci/conan/build_and_test.sh`，目标 profile 为 `os=OHOS`、`os.version=6.0`、`arch=armv8`（aarch64）、Clang 15。结果：L0 质量门禁通过，L1 消费者测试通过，L2 因纯数据包没有可执行程序而跳过，L4 无补丁检查通过，L5 提示没有 bin/lib 产物（数据包预期行为）；包构建和测试汇总为 1/1 成功。此包不含需要编译的代码，因此没有执行编译器。

Conan 消费者测试直接读取安装后的包，检查准确的六文件集合、WOFF signature/flavor/长度/表数/reserved 字段、六个 SHA-256，以及打包许可证中的版权和 OFL-1.1 声明。六个文件均通过；断言计数为 45。

HarmonyOS 特有测试通过 USB HDC 启动 MateBook Pro 系统浏览器，直接从本次 Conan 生成的包目录提供字体。设备系统报告 `OpenHarmony-6.1.0.115`，浏览器 UA 为 `OpenHarmony 6.1 / ArkWeb 6.1.0.115 / HuaweiBrowser 6.1.1.351`。浏览器的 Web Font Loading API 成功解码六个文件，并在 Canvas 绘制代码样例；与系统 `monospace` 绘制结果相比，各字体的差异像素数为：Light 11930、Regular 12692、Medium 13450、SemiBold 14229、Bold 14700、VF 12693，所有绘制像素数均大于零。测试通过，HDC 反向端口映射已清理。

### 对话 #1 — 2026-10-15

- 按资源包与字体包的既有知识条目记录本次归档结构和 WebView 使用边界；在 HarmonyOS 真机上运行 `finish` 完整流程。

## finish 门禁结果

- 真机 `finish` 中 Conan 配方验证、Conan 消费者测试、OHOS 6.0/aarch64 W3 本地 CI、包级知识关联检查和 submit 就绪预检均通过；`.ci-result.json` 记录 W3 `exit_code: 0`。
- 整体 `finish` 为 partial，阻塞项是仓库级 W5 知识图谱完整性：基线 E219、E253 的 `root_cause` 为空；E305 的 `root_cause` 与 `rec_approach` 是有正文的 YAML 多行块，但当前检查器只读字段首行并把 `|` 当作空值。未修改本包无关的共享知识条目或检查器。
- G0 和归档终检提示缺少 tar.gz；该制品是从 zip 发布包提取的纯数据包，不产出编译产物或 release/debug tarball。finish 的 SUMMARY 生成器另有 `'str' object has no attribute 'append'` 异常，但未阻断 Conan、W3 或 submit 就绪检查。
---

**编译结束**: 2026-10-15 19:28
**最终状态**: built
