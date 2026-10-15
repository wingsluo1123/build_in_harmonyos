# yutu 0.10.9 适配笔记

## 编译环境

- 构建系统: Go modules（conan2 配方驱动；上游另有可选的 Bazel 构建，本适配不用）
- 编译日期: 2026-10-11
- Go 工具链: **1.26.5**（OHOS 镜像不自带 Go；按知识 `E250` 在 `build()` 内联下载，见下）
- 编译器: clang 15.0.4（`tools.build:compiler_executables` 指向 `/data/service/hnp/bin/clang`）
- 目标: OHOS 6.0 / armv8（conan profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built（conan create 与 conan-verify 8 门禁全通过；制品尚未 upload）

## 编译步骤

```bash
# 1. 归档骨架
python3 scripts/ohc-run.py init-build yutu 0.10.9 \
  --url=https://github.com/eat-pray-ai/yutu/archive/refs/tags/v0.10.9.tar.gz --auto

# 2. 真实构建（不使用 --build=missing）
conan create archives/y/yutu/0.10.9 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=yutu/*
# → CONAN_CREATE_EXIT=0

# 3. 配方 8 道门禁
python3 scripts/ohc-run.py conan-verify yutu 0.10.9
# → CONAN_VERIFY_EXIT=0（G1/G0/G2/G3/G4/L2/L4/L5 全 PASS）

# 4. 收尾
python3 scripts/ohc-run.py finish yutu 0.10.9 built
```

`conanfile.py` 的 `build()` 实际执行：

```bash
<go> mod download
<go> build -trimpath -tags netgo -ldflags "-s -w \
    -X github.com/eat-pray-ai/yutu/cmd.Version=v0.10.9 \
    -X .../cmd.Commit=99b3443 -X .../cmd.CommitDate=2026-06-21T10:38:47Z \
    -X .../cmd.Os=linux -X .../cmd.Arch=arm64 \
    -X .../cmd.Builder=OpenHarmonyPCDeveloper" -o <link-out>/yutu .
```

产物：`bin/yutu`（29.5 MB，静态 ELF64 AArch64，带 `.codesign` section）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 镜像没有 Go 工具链（`which go` 为空） | 系统未预装，且制品仓无 `go/`、`golang/` 配方（`conan download` exit=1，HTTP 404） | 按知识 E250（`rec_approach: download-go-sdk`，`rec_impl: inline-build-method`）在 `build()` 内联下载 Go SDK；**不**声明 conan requires（与仓内 57 个 Go 配方口径一致） |
| 2 | Go 链接器在 HMDFS 上写输出失败 | `mapping output file failed: permission denied`（E051/E046，mmap 受限） | 链接输出改写到 `/data/storage/el2/base/haps/entry/files` 下的 ext2 类可写工作区 |
| 3 | 未签名 ELF 在 OHOS 上无法 execve | OHOS 要求 `.codesign` section（E128） | 产物 `yutu` 与 Go SDK 的 `pkg/tool/linux_arm64/*` 全部用 `binary-sign-tool` 自签名 |
| 4 | **上游测试无法直接 `go test ./...`** | `go test` 会链接测试二进制并立即 `execve`，未签名 → OHOS 拒绝执行（E128） | 逐包 `go test -c` → 签名 → 执行测试二进制（同 `kor/0.6.8` 策略），并逐项统计 |
| 5 | **`conan-verify` G1 失败**（首个门禁错误） | G1 硬性要求 `conanfile.py` 出现 `apply_conandata_patches` 字面调用；初版只有 `export_conandata_patches` | 引入 `apply_conandata_patches` 并在 `build()` 首行调用（`patches: {}` 为空集，行为不变）；重跑 G1 PASS → 8 门禁 exit=0 |
| 6 | `finish` W3 的 JC 门禁报 3 类错误 | 本地无 `pr.diff` 且 `git diff origin/main...HEAD` 为空 → `junk_check.sh` 回退**全仓** 31584 文件模式，扫出**他人留存的 5 个 `.staging-verified`**（JC1/JC5）与 2136 个包（JC6）——均非本适配引入 | 按 `junk_check.sh` 的权威输入约定提供真实 `pr.diff`（仅含本 PR 的 10 个文件）：`JUNK_PR_DIFF=<path> bash ci/scripts/junk_check.sh .` → `JC_ERRORS=0`、`涉及软件数: 1（合规）` |
| 7 | **CI #91930 `conan-build-test` 失败（PR head `15a6e881`）** —— `go build` 期间几十个包同时报 `.../pkg/tool/linux_arm64/compile: fork/exec ...: resource temporarily unavailable`，随后 `Error in build() method, line 172` / `ConanException: Error 1` | `go build` 默认按 GOMAXPROCS(=nproc) 并行，**每个包一个 `compile` 进程且各自多线程**；CI worker 的进程/线程槽位被瞬时打满 → `fork/exec` 返回 **EAGAIN**。属"worker 侧资源耗尽"类失败（仓内同类先例：`libcom_err/1.47.4`、`tinyarray/1.2.5`、`wchartype/0.1` 的 CI `resource temporarily unavailable (exit 127)`）。本地未复现的原因：本机 `RLIMIT_NPROC` 为 **unlimited**（`python resource.getrlimit` 实测 soft=hard=-1）且第二次起复用已有 `GOCACHE`（890 MB），编译面远小于 CI 的**冷缓存全量编译** | ①`generate()` 与 `_go_env_dict()` 固定 `GOMAXPROCS=1`（子编译器继承，压平线程数）；②`go build` 加 `-p 1`，`go test -c` 加 `-p 1`（同一时刻仅 1 个编译进程）；③新增 `_run_go()`：命中 `_INFRA_MARKERS`（`resource temporarily unavailable` / `out of memory` / `fork failed`…）时按 30s×N 退避重试至多 3 次，非资源类失败立即带原始输出报错，并把 `go_build.log` / `go_mod_download.log` 落到构建目录便于 CI 取证 |
| 8 | CI #91930 修复后的复现验证 | 需在**与 CI 等价的冷缓存全量编译**路径上验证，而非复用本地热缓存 | 清除 `<workspace>/go-build-cache`（890 MB）与 conan 包后重跑 `conan create --build=yutu/*`：**exit 0**，`packages=28 executed=597 passed=597 failed=0 skipped=0`，test_package `9/9`，**全程无 EAGAIN、未触发任何重试**；随后 `conan-verify` **exit 0**（G1/G2/G3 PASS） |
| 9 | **CI #92484 `conan-build-test` 失败（PR head `99eb3aed`）**——`go mod download` 报 `Get "https://proxy.golang.org/cloud.google.com/go/@v/v0.123.0.mod": dial tcp 142.250.198.81:443: i/o timeout`，`Error in build() method, line 176` | **第 8 项修复引入的回归**：`go mod download` / `go build` 从 `self.run(env=["yutu_go_env"])` 改走 `_run_go()` → `_go_env_dict()`，而 `_go_env_dict()` 只搬了 `GOMAXPROCS` 等变量，**漏搬了 `generate()` 里的 `GOPROXY`/`GOSUMDB`**；Go 因此静默回落到内建默认值 `https://proxy.golang.org,direct`，而 worker 到 Google 域名连接超时。上轮本地验证之所以没抓到：只清了 `go-build-cache`，**没清 `go-mod-cache`**，`go mod download` 无网络调用即返回。次要隐患：原 `GOPROXY` 用 `,` 分隔，Go 语义下**只在 404/410 时回退**，遇连接超时会整条命令失败 | ①抽出 `_go_env_overrides()` 作为**单一事实源**，`generate()` 与 `_go_env_dict()` 共用（消除该类分叉）；②代理列表改为 `|` 分隔（任一错误即回退）：`mirrors.aliyun.com/goproxy/｜goproxy.cn｜proxy.golang.org｜direct`，顺序依 CI 实测可达性（同轮 Go SDK 下载即回退 aliyun 成功）；③`generate()` 打印生效的 `GOPROXY`/`GOSUMDB` 到 conan 日志（一眼可诊断）；④`_run_go()` 重试条件扩入 `_NETWORK_MARKERS`（对齐 SKILL v12.18 H2） |
| 10 | CI #92484 修复后的复现验证（补上第 8 项漏掉的网络路径） | 必须清空 `GOMODCACHE` 才能让 `go mod download` 真正走网络 | `chmod -R u+w` 后删净 `go-mod-cache`/`go-build-cache`（残留 0 文件）并重跑 `conan create --build=yutu/*`：**exit 0**，日志打印 `Go module proxy (GOPROXY): https://mirrors.aliyun.com/goproxy/｜…`，`go mod download: ok` / `go build: ok`，`packages=28 executed=597 passed=597 failed=0 skipped=0`，`9/9`，**0 次网络/资源类重试**，模块缓存从 0 重新长回 **651 MB**（证明确为走网络下载）；随后 `conan-verify` **exit 0**（G1/G2/G3 PASS） |

## 源码修改

无补丁。`conandata.yml` 的 `patches: {}` 为空：上游以 `CGO_ENABLED=0` + `-tags=netgo`
构建，交叉编译到 OHOS aarch64 不需要改动源码或 `go.mod`（`go 1.26.0` 由 1.26.5 满足）。

## 依赖版本

| 依赖 | 版本 | 类型 | 消费方式 |
|---|---|---|---|
| Go 工具链 | 1.26.5 | 构建工具链 | `build()` 内联下载（golang.google.cn / mirrors.aliyun.com / dl.google.com，sha256 校验） |
| Go 模块（直接 13 + 传递 55，共 68） | 见 `go.sum` | 源码级 | `GOPROXY`（`https://goproxy.cn,https://proxy.golang.org,direct`） |
| C/C++ 第三方库 | — | — | **无**：源码 0 个 `.c/.h`、0 处 `import "C"`、0 处 cgo |
| ca-certificates | 系统提供 | 运行期数据 | 上游 `Dockerfile` 从 alpine 拷 `ca-certificates.crt`，OHOS 由系统提供 |

## 验证结果

```bash
$ conan create archives/y/yutu/0.10.9 -pr:h=... -pr:b=... --build=yutu/*
CONAN_CREATE_EXIT=0

$ /data/service/hnp/bin/llvm-readelf -d <pkg>/bin/yutu | grep NEEDED
（无输出 → 静态链接）
$ /data/service/hnp/bin/llvm-readelf -h <pkg>/bin/yutu | grep Machine
  Machine:                           AArch64
$ /data/service/hnp/bin/llvm-readelf -S <pkg>/bin/yutu | grep codesign
  [16] .codesign         PROGBITS        0000000000000000 1c31000 001000 00      0   0 4096

$ <pkg>/bin/yutu version
🐰yutu v0.10.9 linux/arm64
📦build OpenHarmonyPCDeveloper-2026-06-21T10:38:47Z
🌟Star: Github/eat-pray-ai/yutu (https://github.com/eat-pray-ai/yutu)

test_package：9/9 断言通过（ELF magic / version / help / video --help / 静态链接）
conan-verify：verdict=PASS（G1 G0 G2 G3 G4 L2 L4 L5）
```

## CI 验证记录

### 第 1 轮：PR #15399 / 构建 #91930（head `15a6e881`）— ❌ 失败

```
--- conan-build-test ---
oyutu/0.10.9: RUN: ".../go/bin/go" build -trimpath -tags netgo -ldflags "..." -o ".../link-out/yutu" .
ointernal/godebugs: .../pkg/tool/linux_arm64/compile: fork/exec .../compile: resource temporarily unavailable
o...(同样报错数十个包，含 compile 与 asm)...
oyutu/0.10.9: ERROR: Package '6b129b06...' build failed
oERROR: yutu/0.10.9: Error in build() method, line 172
o	ConanException: Error 1 while executing
oL1_RESULT=fail: conan create failed   （L2/L4/L5 skip）
```

- 前置门禁全部通过：`G0`（546 条知识）✅ `L0j/L0k/L0m/L0n` ✅ `KC`（0 错误）✅ `JC`（prdiff 10 文件、涉及软件数 1）✅
- 源码与 Go SDK 下载均正常（`Sources correctly downloaded from https://github.com/...` / `golang.google.cn/dl/go1.26.5.linux-arm64.tar.gz`），Go SDK 签名成功
- **失败仅发生在 `go build`**：Go 工具链自身的 `compile`/`asm` 进程 `fork/exec` 返回 EAGAIN

### 第 2 轮：修复后本地冷缓存复现 — ✅ 通过

```bash
# 复现 CI 的冷缓存全量编译（清空 890 MB GOCACHE 与 conan 包）
rm -rf /data/storage/el2/base/haps/entry/files/yutu-0.10.9-go/go-build-cache
conan remove "yutu/*" -c
conan create archives/y/yutu/0.10.9 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=yutu/*
# → CONAN_CREATE_EXIT=0
# → yutu upstream `go test -c` + sign + run: packages=28 executed=597 passed=597 failed=0 skipped=0
# → [ok] All 9 consumer smoke assertions passed.
# → 全程 0 次 "resource temporarily unavailable"、0 次重试触发
```

随后 `python3 scripts/ohc-run.py conan-verify yutu 0.10.9` → **exit 0**（G1/G2/G3 PASS）。

### 第 3 轮：构建 #92484（head `99eb3aed`）— ❌ 失败（上轮修复引入的回归）

CI bot 归类为「网络问题」并指向 `gh-proxy.com/...yutu...`，**该归类是误判**（日志里出现该 URL 只是因为 CI 自身在 pre-download 阶段注入了 gh-proxy 镜像前缀）。真实失败在 `go mod download`：

```
oyutu/0.10.9: Calling build()
oyutu/0.10.9: WARN: go mod download: attempt 1/3 failed (rc=1)
ogo: cloud.google.com/go@v0.123.0: Get "https://proxy.golang.org/cloud.google.com/go/@v/v0.123.0.mod":
   dial tcp 142.250.198.81:443: i/o timeout
oERROR: yutu/0.10.9: Error in build() method, line 176
o	self._run_go(go, ["mod", "download"], "go mod download", timeout=3600)
o	ConanException: go mod download failed (rc=1)
oL1_RESULT=fail: conan create failed
```

- 前置门禁仍全绿：`G0`（547 条）✅ `L0j/L0k/L0m/L0n` ✅ `KC`（0 错误）✅ `JC`（prdiff 10 文件 / 涉及软件数 1）✅
- 同轮 Go SDK 下载也遇到 Google 域名超时，**回退 `mirrors.aliyun.com` 后成功** —— 说明该 worker 出网受限，只有国内镜像可达
- 根因：`_go_env_dict()` 漏搬 `GOPROXY`，Go 静默回落到内建默认 `https://proxy.golang.org`（见上表第 9 项）

### 第 4 轮：修复后本地**真网络**复现 — ✅ 通过

```bash
# 上轮漏了这一步：必须清空 GOMODCACHE，否则 go mod download 不发任何网络请求
chmod -R u+w "$WS/go-mod-cache" "$WS/go-build-cache"
rm -rf "$WS/go-mod-cache" "$WS/go-build-cache" "$WS/link-out" "$WS/upstream-tests"
conan remove "yutu/*" -c
conan create archives/y/yutu/0.10.9 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=yutu/*
# → yutu/0.10.9: Go module proxy (GOPROXY): https://mirrors.aliyun.com/goproxy/|https://goproxy.cn|https://proxy.golang.org|direct
# → yutu/0.10.9: Go checksum DB (GOSUMDB): sum.golang.google.cn
# → yutu/0.10.9: go mod download: ok
# → yutu/0.10.9: go build: ok
# → CONAN_CREATE_EXIT=0
# → packages=28 executed=597 passed=597 failed=0 skipped=0 ; [ok] All 9 consumer smoke assertions passed.
# → 0 次网络/资源类重试；go-mod-cache 由 0 重新长回 651 MB（证明模块确为走网络下载）
```

随后 `conan-verify` → **exit 0**（G1/G2/G3 PASS，0 次重试）。

> 教训（已写入 manifest 知识条目）：把命令从 `self.run(env=[...])` 改到直接 `subprocess` 时，必须把 conan 环境脚本里的全部变量一起搬过去；验证时也必须覆盖该命令的真实依赖路径（这里是网络），否则热缓存会掩盖回归。

## 上游测试（实际执行，非 test_package 冒烟）

上游 0.10.9 有完整自动化测试：30 个 `*_test.go`、177 个顶层 Test 函数、
CI（`.github/workflows/test.yml`）跑 `go test ./... -coverprofile=... -coverpkg=./pkg/...`
外加 `scripts/command-test.sh`。

OHOS 上按 §问题 4 的策略逐包执行：

```bash
go list -f '{{.ImportPath}}|{{len .TestGoFiles}}|{{len .XTestGoFiles}}' ./...   # 枚举测试包
go test -c -count=1 -timeout 1200s -o <ext2>/<pkg>.test <pkg>                    # 编译
llvm-objcopy --remove-section .codesign … && binary-sign-tool sign -selfSign 1 …  # 签名
<ext2>/<pkg>.test -test.v -test.timeout 1200s                                    # 执行
```

**结果：28 个测试包，597 个用例全部通过（通过 597 / 失败 0 / 跳过 0）**

| 测试包 | 通过 | 失败 | 跳过 |
|---|---|---|---|
| cmd | 10 | 0 | 0 |
| pkg | 13 | 0 | 0 |
| pkg/activity | 22 | 0 | 0 |
| pkg/auth | 22 | 0 | 0 |
| pkg/caption | 39 | 0 | 0 |
| pkg/channel | 27 | 0 | 0 |
| pkg/channelBanner | 14 | 0 | 0 |
| pkg/channelSection | 20 | 0 | 0 |
| pkg/comment | 31 | 0 | 0 |
| pkg/commentThread | 21 | 0 | 0 |
| pkg/common | 33 | 0 | 0 |
| pkg/i18nLanguage | 10 | 0 | 0 |
| pkg/i18nRegion | 10 | 0 | 0 |
| pkg/member | 16 | 0 | 0 |
| pkg/membershipsLevel | 8 | 0 | 0 |
| pkg/playlist | 29 | 0 | 0 |
| pkg/playlistImage | 29 | 0 | 0 |
| pkg/playlistItem | 32 | 0 | 0 |
| pkg/search | 21 | 0 | 0 |
| pkg/subscription | 25 | 0 | 0 |
| pkg/superChatEvent | 14 | 0 | 0 |
| pkg/thirdPartyLink | 18 | 0 | 0 |
| pkg/thumbnail | 9 | 0 | 0 |
| pkg/utils | 38 | 0 | 0 |
| pkg/video | 50 | 0 | 0 |
| pkg/videoAbuseReportReason | 11 | 0 | 0 |
| pkg/videoCategory | 13 | 0 | 0 |
| pkg/watermark | 12 | 0 | 0 |
| **合计** | **597** | **0** | **0** |

- 原始日志: `<build_folder>/upstream-tests.log`（1340 行，66306 字节，见 conan create 日志）
- 结构化证据: 包内 `share/yutu/upstream-test-result.json`（含 597 条逐项用例名）
- 逐项用例名格式: `<PASS|FAIL|SKIP> <import_path>::<TestName>[/<subtest>]`

> `test_package` 的 9 项冒烟断言是**消费者视角**附加测试，不冒充上游覆盖；上游测试统计
> 全部来自上述 `go test -c` 逐包执行。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/yutu` | 29.5 MB | 静态 ELF64 AArch64，已 `.codesign` 签名 |
| `licenses/LICENSE` | 11 KB | Apache-2.0 |
| `share/yutu/upstream-test-result.json` | — | 上游测试结构化证据（HMBS 门禁读取） |

## 注意事项

1. **零 conan 依赖**：本配方没有 `requires()` / `tool_requires()`，因此 W0/R36 依赖
   链为空，不存在需要先发布的上游依赖。
2. Go SDK 下载需要外网可达 `golang.google.cn` / `mirrors.aliyun.com`；`GOTOOLCHAIN=local`
   已固定，避免工具链在构建期自行下载别的 Go 版本。
3. `GOPROXY` 默认 `https://goproxy.cn,https://proxy.golang.org,direct`，可用环境变量
   `GOPROXY` 覆盖。
4. 本地跑 `finish` 时，若工作区 HEAD 与 `origin/main` 相同且无 `pr.diff`，`junk_check.sh`
   会回退全仓模式并因**仓库既有**的 `.staging-verified` 报 JC 失败；应提供 `pr.diff`
   （或 `JUNK_PR_DIFF=<path>`）复现 CI 的 prdiff 模式。
---

**编译结束**: 2026-10-12 11:20
**最终状态**: built
