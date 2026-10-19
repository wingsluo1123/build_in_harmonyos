## 三方库信息

- **三方库名称**：LIVE555 Streaming Media（live555）
- **上游版本**：2026.08.14（上游采用日期版本号）
- **上游仓库地址**：http://www.live555.com/liveMedia/（官方发布位；本沙箱不可用，见「换源」）
- **适配路径**：路径 A（基础适配）+ 路径 B（知识库扩展，候选）
- **使用知识库**：openharmony-compile-agent

## 为什么需要新增

MPlayer（PR #15441）的 `--enable-live` 选项需要 LIVE555 头/库（RTSP/RTP 客户端能力）。
此前仓内**没有任何 live555 相关文件**，本 PR 从零新增该依赖包。

## 换源（上游发布位实测不可用）

| 端点 | 结果 |
|---|---|
| `http://download.live555.com/<file>` | `301`，且 `Location` **畸形**：`https://download.live555.comlive.<date>.tar.gz`（域名与文件名之间缺 `/`） |
| `https://www.live555.com/...` | TLS `wrong version number`（协议不兼容） |
| `http://www.live555.com/liveMedia/public/` | `404` |

改用 **Fedora 官方 lookaside 缓存**中的 pristine 上游 tarball：

```
url:    https://src.fedoraproject.org/repo/pkgs/live555/live.2026.08.14.tar.gz/sha512/<sha512>/live.2026.08.14.tar.gz
sha256: 85848fb28df98a77a6e745959cc3ecf5f541f34c8ffef9021b9f1c2e682edee0
sha512: 1fc21b675b128dae47713b59b81ab2845f416f30a2dfa46efe60d966fb6fff22433aad14a90e46cd7b020abf595c3242358bbf6344c66729d3eb69760c9ed897（Fedora 记录值，本包已逐字核验一致）
```

这与 libcddb（sourceforge 不可达 → Debian pristine orig）构成**同一换源模式的两个样本**：官方发布位不可用时，
用官方发行版缓存的 pristine 上游产物换源，并以该缓存记录的强哈希核验。

## 适配要点（私有构建流程）

live555 不使用 autotools/cmake，而是 `./genMakefiles <platform>`（把各子目录 `Makefile.head` +
`config.<platform>` + `Makefile.tail` 拼成 Makefile）再 `make`。本配方的接线：

1. **构建期生成 `config.ohos-aarch64`**：编译器/归档器取自 profile 的 `tools.build:compiler_executables`
   （`clang`/`clang++` + 同目录 `llvm-ar`），目标三元组用 **`--target=aarch64-linux-ohos`**
   （实测：写成 `aarch64-linux` 会因找不到 OHOS sysroot 而报 `'sys/types.h' file not found`），
   并加 `-fPIC`、`-DNO_OPENSSL=1`（不引入 OpenSSL）。
2. **只构建消费者需要的四个子目录**：`liveMedia / groupsock / UsageEnvironment / BasicUsageEnvironment`；
   `testProgs / mediaServer / proxyServer / hlsProxy` 不构建，避免无关成本。
3. **不走上游 `make install`**：上游顶层 `install:` 会遍历 8 个子目录执行各自 install，未构建者会报错；
   改由 recipe 显式收集产物——4 个静态库 → `lib/`，各子目录 `include/*.hh|*.h` → `include/<subdir>/`
   （与上游 install 布局一致，MPlayer 的 `liveMedia/liveMedia.hh` 探测可直接命中）。
4. **导出 `NO_OPENSSL=1` 定义**：打包头 `liveMedia.hh`/`TLSState.hh` 用 `#ifndef NO_OPENSSL` 守卫
   `<openssl/ssl.h>`，消费者编译期必须带同一宏（否则包含即失败）→ 经 `cpp_info.defines` 自动导出。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无单元测试框架（live555 以示例程序承载能力验证） |
| 集成测试 | 35 | 来源：上游 `testProgs/`（**35 个独立测试程序**；另有 `playCommon.cpp`、`announceURL.cpp` 两个共享辅助源文件，目录共 37 个 `.cpp`） |
| 其他测试 | 0 | — |
| **合计** | **35** | 声明值取评审实测口径，避免少报 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 集成测试（上游端点端到端） | 2 | -33 | **真实执行**：构建并运行上游 `testProgs/testOnDemandRTSPServer`（服务端，TCP 8554）与 `testProgs/openRTSP`（客户端），完成一整套 RTSP 会话（OPTIONS→DESCRIBE→SETUP→PLAY）并**实收 854 字节**媒体数据（落盘 `outvideo-MP4V-ES-1`）。其余 33 个示例需外部媒体/网络环境且非本包消费者所需，逐类列明见下 |
| 单元测试 | 0 | 不变 | 上游无单元测试框架 |
| 鸿蒙特有测试 | 1 | 新增 | 消费者用例（`test_package`）：离线构造 `BasicTaskScheduler`/`BasicUsageEnvironment` 并调用真实 API（含聚合头包含性检查） |
| **合计** | **3** | **-32** | 减少的 32 例均为**具体原因**：需外部媒体文件/真实网络或 UDP 组播环境，且非本包消费者（MPlayer `--enable-live`）所需 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

说明（补充上下文，供人工确认）：**未修改、未删除**任何上游测试源码。本包按消费者需要只构建 4 个库子目录
（`liveMedia`/`groupsock`/`UsageEnvironment`/`BasicUsageEnvironment`）；另在 `build()` 中额外构建 **2 个上游端点程序**
（`testProgs/testOnDemandRTSPServer`、`testProgs/openRTSP`）**仅用于端到端验证、不打包**，其源码取自上游原始文件。
未执行的上游示例逐类说明：各类编码示例（AMR/DV/GSM/H.264/H.265/MPEG-1,2/MP3/WAV/AC3/Opus…）需对应外部媒体文件；
`mediaServer`/`proxyServer`/`hlsProxy` 需外部媒体库与真实网络；SIP/组播（`playSIP`/`sapWatch`/`registerRTSPStream` 等）需 UDP 组播或 SIP 服务器环境。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

说明（补充上下文，供人工确认）：上游 `testProgs/` 自带 **35 个**测试程序（评审实测口径 N=35，声明一致）；
本包另外补充了 1 个**消费者用例**（`test_package`：离线构造 `BasicTaskScheduler`/`BasicUsageEnvironment` 并调用真实 API），
属于消费者视角验证，而非"上游无测试的补全"。

## 验证结果

- 编译状态：**通过** —— `conan create archives/l/live555/2026.08.14 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing` → rc=0
- 上游测试用例通过率：**2/2（100%）** —— 上游端点程序**真实端到端执行**（本机回环，OHOS 原生运行）：
```
RTSP 端到端：openRTSP 实收 854 字节，落盘 outvideo-MP4V-ES-1:854B
```
  服务端 `testOnDemandRTSPServer` 先就绪，客户端 `openRTSP` 完成 RTSP 会话并把真实媒体字节落盘；
  两端均以本包构建出的四个静态库链接，媒体样本以**文本常量内联**（无二进制资产入库）。
- 新增测试用例通过率：**1/1（100%）** —— `test_package` 消费者用例：
```
live555 basic usage environment ok
live555 liveMedia/BasicUsageEnvironment 可用性检查通过
```
- 端到端实现要点（可迁移）：`-F <prefix>` 才是 openRTSP 的输出文件名前缀（`-b` 是 FileSink 缓冲字节数，
  用错会直接打印 usage）；断言以**落盘文件的实际字节数**为准，而不是客户端日志。

## 路径评估（按仓内口径）

- **路径 A（基础适配）**：已完成 —— 构建 + 消费者测试全绿。
- **路径 B（知识库扩展）**：**可申报（候选）** —— 两条可迁移经验：
  1. **私有构建流程**（genMakefiles + 子目录 Makefile 拼接）在 OHOS 上的接线法：构建期生成
     `config.<platform>`、按需裁剪子目录、因上游 install 遍历全部子目录而改为 recipe 侧收集产物、
     并把打包头所依赖的宏（`NO_OPENSSL`）经 `cpp_info.defines` 导出给消费者；
  2. **换源判据**（与 libcddb 同模式）：官方发布位 301 畸形/TLS 失败时改用 Fedora lookaside 的
     pristine 上游 tarball，并用其记录的 sha512 逐字核验。
- **路径 C（高难度挑战）**：**不主张** —— 单体库 + 私有 makefile 流程，无 bundled 依赖自举与大规模回归矩阵。
