# LIVE555 2026.08.14 适配笔记（OHOS PC / aarch64 / musl）

## 结论

- 状态：**built**（`conan create` 全链路通过，含消费者测试）
- 源：**换源**后取 Fedora lookaside 的 pristine 上游 tarball（sha512 与 Fedora 记录逐字一致）
  `live.2026.08.14.tar.gz`，sha256 `85848fb28df98a77a6e745959cc3ecf5f541f34c8ffef9021b9f1c2e682edee0`
- 构建系统：**私有流程**——`./genMakefiles <platform>`（把 `$subdir/Makefile.head` + `config.<platform>`
  + `$subdir/Makefile.tail` 拼成各子目录 Makefile）+ `make`
- 构建范围：`liveMedia / groupsock / UsageEnvironment / BasicUsageEnvironment` 四个子目录
  （消费者 MPlayer `--enable-live` 只需要这些）；`testProgs / mediaServer / proxyServer / hlsProxy` 不构建
- 消费者测试：C++ 程序包含 `<liveMedia.hh>` 并构造 `BasicTaskScheduler` / `BasicUsageEnvironment`
  （真实构造函数与虚表调用，无网络），随后 `reclaim` + 析构

## 换源（本沙箱实测）

| 端点 | 结果 |
|---|---|
| `http://download.live555.com/<file>` | `301` 且 `Location` **畸形**：`https://download.live555.comlive.<date>.tar.gz`（域名与文件名之间缺 `/`） |
| `https://www.live555.com/...` | TLS `wrong version number`（协议不兼容） |
| `http://www.live555.com/liveMedia/public/` | `404`（目录列表不可用） |
| Fedora lookaside `src.fedoraproject.org/repo/pkgs/live555/` | **可用**：含多个上游 `live.<date>.tar.gz`，且每个文件页给出 sha512 |

→ 采用 Fedora 官方 lookaside 缓存中的 pristine 上游 tarball，并以 Fedora 记录的 sha512
逐字核验（本包已核验一致），sha256 同时写入 `conandata.yml`。这与 libcddb（sourceforge 不可达 →
改用 Debian pristine orig）构成**同一模式的两个样本**：*官方发布位不可用时，用官方发行版缓存的
pristine 上游产物换源，并用该缓存记录的强哈希核验*。

## 构建接线要点

1. **构建期生成平台配置** `config.ohos-aarch64`：live555 没有任何自动探测，编译器/归档器与目标
   三元组都要写进配置。取值来自 profile 的 `tools.build:compiler_executables`（`clang`/`clang++`），
   归档器取同目录 `llvm-ar`，并加 `--target=aarch64-linux`、`-fPIC`、`-DNO_OPENSSL=1`
   （不引入 OpenSSL，RTSP 明文/RTSP-over-TCP 已够 MPlayer 使用）。
2. **只驱动需要的子目录**：`genMakefiles` 会给 8 个子目录都生成 Makefile，但只需对 4 个执行 `make`，
   避免 testProgs/mediaServer 等无关成本。
3. **不走上游 install**：上游顶层 `Makefile.tail` 的 `install:` 会遍历全部 8 个子目录执行各自 install，
   未构建者会报错；因此由 recipe 显式收集产物——4 个静态库 → `lib/`，各子目录
   `include/*.hh|*.h` → `include/<subdir>/`（与上游 install 的布局一致，消费者 `#include <liveMedia.hh>`
   与 `-lliveMedia -lgroupsock -lUsageEnvironment -lBasicUsageEnvironment` 均可直接使用）。

## 路径评估（按仓内口径）

- **路径 A（基础适配）**：已完成 —— 构建 + 消费者测试通过。
- **路径 B（知识库扩展）**：**可申报（候选）** —— ① 私有构建流程（genMakefiles + 子目录 Makefile 拼接）
  在 OHOS 上的接线法与"不走上游 install、recipe 侧收集产物"的处置；② 官方发布位不可用时的换源判据
  （Fedora lookaside pristine + 强哈希核验）。
- **路径 C（高难度挑战）**：**不主张** —— 单体库 + 私有 makefile 流程，无 bundled 依赖自举与回归矩阵。

## 路径 B 材料

- 草稿：`knowledge/drafts/DRAFT-ohos-private-build-flow-genmakefiles-wiring.{kv,md}`（查重 verdict=`create`；载体 PR #15531 live555 新适配）
