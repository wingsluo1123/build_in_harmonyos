# libbcg729 1.1.1 适配笔记

## 软件信息
- **名称**: libbcg729（任务卡 #13871 名为 bcg729；包名跟随仓内既有 `libbcg729` 生态名，与 1.1.2 版本线同包名单线演进，避免制品仓双包分裂）
- **版本**: 1.1.1 (2020-11-17 release tag)
- **描述**: ITU G.729 Annex A/B 语音编解码开源实现（纯 C 定点，支持并发编解码通道）
- **License**: GPL-3.0-only
- **上游**: https://github.com/BelledonneCommunications/bcg729

## 编译环境
- 构建系统: cmake（上游原生 CMakeLists.txt，未重造）
- 编译日期: 2026-09-23
- 编译器: clang（ohos-aarch64 profile clang 15）
- 状态: built

## 源码核实
- **真实上游**: BelledonneCommunications/bcg729
- **正式 1.1.1 tag**: codeload 归档直下（GitHub API rate limit 规避），sha256 `68599a850535d1b182932b3f86558ac8a76d4b899a548183b062956c5fdc916d`
- CHANGELOG 1.1.1: "compatibility with old compilers"（fixedCodebookSearch.c 的 Phi 初始化 `{0}`→`{{0}}`）

## 构建配置
上游 CMake 选项（conanfile.py generate() 设置）：
- `ENABLE_STRICT=OFF` — 上游默认 YES 加 `-Werror -Wextra`，OHOS 交叉工具链上无害 warning 变硬失败
- `ENABLE_TESTS=OFF` — 上游测试需外部 33MB 向量包 + 访问内部私有符号，不适合交叉编译 L1（上游测试在适配期以 native 方式完整真跑，见下节）
- 零第三方依赖（纯 C，仅 libc）

## 上游测试（适配期 native 真跑记录）
上游注册测试口径：**27 个测试可执行**（test/CMakeLists.txt add_executable 计数）。
向量数据：`bcg729-patterns-v1.1.0.zip`（linphone.org/bc-downloads，md5 f223c39eb471350124e56978760858f7，33MB，21 个 bloc 目录 × 173 个 .in 用例）。

native 主机（clang 15 -O2）编译 + perl testCampaign all 实测：
- **158/173 pattern 用例 Pass**
- 15 个 Fail 集中于 3 个 bloc：LP2LSPConversion(7/7)、LSPQuantization(2/7)、encoder(6/7)

### 15 个 Fail 的根因分析（非适配缺陷，上游行为变更）
- 差异首发于 LP2LSPConversion 输出列 1/2（LSP 系数）：差异幅度 ±1~123（Q15 LSB 级）
- 根因：上游 **1.1.0 起 LP2LSPConversion.c 加入 SATURATE/SSHL 溢出修复**（CHANGELOG: "infinite loop in VAD module and overflow in encoder"）——1.0.4 用裸 SHL，1.1.x 用 SSHL+SATURATE(MAXINT17)
- LSB 差异经 LSPQuantization 的量化格点选择放大为 encoder 参数差异
- **对照实验（决定性证据）**：用上游 **1.0.4 源码**编译后跑同一份 patterns → **173/173 全过**。证明 patterns v1.1.0.zip 实际由 1.0.x 代码生成，1.1.x 的差异是上游有意的溢出修复行为变更
- -O0/-O2 复验差异一致（排除编译器优化因素）
- g729FixedPointMathTest（自检数学函数，自带参数空间）：Log2/Exp2/Sqrt/InvSqrt/Cos/Atan/Asin/Acos 全部统计达标，exit 0
- encoderVADTest 复用 encoder 向量运行 176 帧 exit 0（无官方 pattern 比对）；CNGRFC3389decoder/computeNoiseExcitation/decoderMultiChannel/encoderMultiChannel 在公开 zip 中无对应向量目录（上游 1.1.x 新增测试，官方向量缺失）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | linphone.org 403 | 上游下载源限制 | README 中 belledonne-communications.com 镜像 URL 可用（sha 同版本向量） |
| 2 | ENABLE_STRICT -Werror 风险 | 上游默认 strict | OFF |
| 3 | 15/173 pattern 不匹配 | 上游 1.1.0 溢出修复 vs 1.0.x 生成的参考向量 | native 真跑 + 1.0.4 对照实验定性：上游行为变更，如实申报 |
| 4 | 上游测试 33MB 向量不适合交叉 L1 | 向量外置 + 私有符号 | L1 用公开 ABI 消费者测试（round-trip + 并发 channel） |

## test_package
自定义 L1 测试调用真实公开 API：
1. `initBcg729EncoderChannel(0)` → `bcg729Encoder`(静音帧) → 验证 10 字节语音帧输出
2. `initBcg729DecoderChannel()` → `bcg729Decoder` → 验证 80 样本输出合法
3. **并发通道验证**：2 个独立 encoder context 同时编码（bcg729 卖点：并发编解码通道；1.1.1 API 形态=独立 context，显式 *Channels() API 为后续版本新增）
4. `close*` 资源释放

## 依赖版本
无外部依赖（纯 C 库，仅 libc）。

## 交付物
| 文件 | 说明 |
|------|------|
| `libbcg729.so` | 动态库 |
| `bcg729/encoder.h`, `bcg729/decoder.h` | 公开头文件 |
| `libbcg729.pc` | pkg-config 文件 |
| `libbcg729Config.cmake` + `libbcg729Targets.cmake` | CMake config 包 |

---
**编译结束**: 2026-09-23
**最终状态**: built
