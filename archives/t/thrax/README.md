# thrax

OpenGrm Thrax 是 Google 开源的**加权有限状态转换器（FST）语法编译器与改写工具集**：用声明式的
语法文件（`.grm`）描述字符串到字符串的映射，编译为 FST 归档（`.far`）后可在运行期用于改写、
随机生成、统计分析。广泛用于语音识别、自然语言处理、文本规范化（TN/ITN）等场景。

## 主要功能

- **语法编译**：`.grm` → `.far`（FST 归档），支持正则、上下文相关规则、PDT/MPDT 等重写机制
- **运行期改写**：`thraxrewrite-tester` 按规则改写输入串（文本规范化、分词、缩写展开）
- **随机生成**：`thraxrandom-generator` 按语法随机采样字符串（用于语言模型语料合成、测试）
- **FST 注册表**：运行期按名字（`vector`、`byte`、`pdt` 等）构造 FST 类型，可被 .far 引用
- **可编程接口**：`libthrax.so` + 77 个头文件，供 C++ 程序直接调用

## 编译产物

- `bin/` 下 4 个可执行文件：`thraxcompiler`、`thraxrewrite-tester`、`thraxrandom-generator`
  （3 个**编译出的** ELF 工具，whole-archive 链接修复针对它们）+ `thraxmakedep`
  （上游 shell 脚本，经 `EXTRA_DIST` 安装，Makefile 依赖生成器）
- `libthrax.so` — 语法编译器与运行期支持库
- 77 个头文件（`include/thrax/`）
- 10 个语法素材与示例（`share/thrax/grammars/*.grm`）

## 鸿蒙平台适配

thrax 在鸿蒙（OpenHarmony/HarmonyOS）平台上需要以下处理：

1. `config.guess` — 补 aarch64 + HarmonyOS 识别（复用 Linux 三元组分支，最小改动）
2. **链接口径**：`src/bin` 三个编译出的 CLI 的 `LDADD` 需把 `-lfst` 包进 whole-archive
   （写成**单个** `-Wl,--whole-archive,-lfst,--no-whole-archive`，拆成两个 `-Wl` 会被 libtool 重排失效）。
   原因：`fst/register.h` 的 `REGISTER_FST` 在 `libfst.a` 内是**文件局部符号**，裸 `-lfst` 按需抽取
   不会拉入该成员，运行期 FST 类型表为空 → `.far` 报 `Unknown FST type`，`import` 语法编译 Signal 11
3. **依赖 include 注入**：`AutotoolsToolchain` 会整段覆盖自定义 `CPPFLAGS`（生成文件里只剩 `-DNDEBUG`），
   故改走 `extra_cflags`/`extra_cxxflags`；`-L` 走 `extra_ldflags` 以保证位于链接行最前
4. 依赖 `openfst/1.8.4.1`（必须是含 GRM 扩展 `far`/`pdt`/`mpdt` 的适配版）

## 可用版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.3.10 | built | 2026-10-11 |
