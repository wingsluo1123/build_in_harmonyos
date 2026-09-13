# libosmocore 1.11.0 适配笔记

## 编译环境

| 项 | 值 |
|----|----|
| 平台 | HarmonyOS PC / aarch64（HongMeng Kernel 1.13.0 #1 SMP aarch64 GNU/Linux） |
| 编译器 | clang（OHOS SDK 26.0.0.18，`/data/service/hnp/bin/clang`） |
| libc | musl（OHOS native） |
| 构建系统 | autotools（configure + make，CI/reconf 支持 autoreconf 重生成） |
| Conan | conan 2.29.1（OHOS 适配版，profile `ci/conan/profiles/ohos-aarch64`） |
| 依赖注入 | `PkgConfigDeps`（talloc / libmnl / libusb-1.0 / libpcsclite 的 .pc） |
| 源码 | `https://downloads.osmocom.org/releases/libosmocore/libosmocore-1.11.0.tar.bz2` |
| 源码 sha256 | `8e8dbf5e7d6d705aa34461a4ab3a0bd57f6961582cef95a1aafef3c74604c6dc` |

## 编译步骤

1. `conan create . -pr:a=ci/conan/profiles/ohos-aarch64 --build=missing`
   （配方内部：`apply_conandata_patches` → `configure` → `make` → `make check` → `make install`）
2. 上游测试：`make check`（automake testsuite，90 项）
3. 包级测试：`test_package`（`test.c` 冒烟 + `test_ohos_tls.c` 鸿蒙 TLS 专项）

探索阶段的手动等价命令（用于定位问题，结果与 conan 一致）：

```sh
./configure --prefix=<prefix> --disable-gnutls --disable-libsctp --disable-uring \
    --enable-static --disable-shared \
    CFLAGS="-fPIC -O2 -std=gnu11 -DBUILDING_LIBOSMOCORE -fno-emulated-tls"
make -j2 && make check && make install DESTDIR=<staging>
```

## 遇到的问题与解决方案

| # | 问题 | 现象 | 解决方案 |
|---|------|------|---------|
| 1 | emulated TLS（emutls） | 库内 TLS 变量（`osmo_ctx_`）经 DSO 访问时段错误；`__emutls_v.osmo_ctx_` 未定义符号 | 全量加 `-fno-emulated-tls`（原生 TLS）。已用最小实验对比：原生 TLS 语义正确、emutls 控制块不可跨 DSO（知识库 E026/E104） |
| 2 | 上游发布包缺头文件 | `src/gsm/kdf/crypto.h` 未打入 1.11.0 tarball，`sha1/sha256` 编译失败 | 取上游 1.11.0 tag 原文补齐（校验 blob 一致），以 `/dev/null` 新增补丁 `0012` 交付 |
| 3 | `sockaddr_storage` 重定义 | musl 头与内核 uapi 头同时定义（netdev.c / stats_tcp.c / gprs_ns2_fr.c / mnl.c） | 平台中立宏改名守卫（不引入 `__OHOS__` 平台宏；知识库 E091） |
| 4 | `__always_inline` 未定义 | musl 无该 glibc 宏（`include/osmocom/core/hash.h`） | 平台中立改写为 `__inline__ __attribute__((always_inline))` |
| 5 | config.guess/config.sub | 不识别 `aarch64-linux-ohos` | 补丁 `0001/0002`：接受 linux-ohos 内核↔OS 组合并修脚本 umask 问题（E007/E114） |
| 6 | gnutls 依赖不可用 | 制品仓无 gnutls 二进制 | `--disable-gnutls`（TLS 传输为可选特性，非本包核心） |
| 7 | SCTP 不可用 | `socket(AF_INET, SOCK_STREAM, IPPROTO_SCTP)` → `errno=93 (Protocol not supported)`；链接 `-lsctp` 失败 | `--disable-libsctp`；上游 testsuite 自带 `AT_SKIP_IF` 跳过该用例 |
| 8 | io_uring 不可用 | uring 测试运行 `Signal 31 (core dumped)`（seccomp 拦截 syscall） | `--disable-uring`；上游 testsuite 对 uring 用例自带 `AT_SKIP_IF` |
| 9 | 8 个上游测试用例失败 | 见下节逐项 | 逐项修复（补丁 0007-0010、0013-0016） |

### 上游测试用例失败明细与修复（8 例）

| 用例 | 根因 | 修复 |
|------|------|------|
| 47 utils | `osmo_str_to_int64` 在 musl 下的 errno 映射差异 | `src/core/utils.c`：按 errno 语义返回（补丁 0010） |
| 69 sockaddr_str | 地址串↔sockaddr 转换在 musl/OHOS 下边界不同 | `src/core/sockaddr_str.c`：转换逻辑与期望对齐（补丁 0007） |
| 43 gprs_bssgp | libtool 版本脚本（`*.map`）下 DSO 内符号不能被可执行文件 interpose，测试桩未被调用 | 测试侧接线 BSSGP 回调（补丁 0013）；已用插桩确认原桩未被库调用 |
| 23 lapd | `strerror(0)` 文案与 glibc 期望不同（musl） | 测试期望按 `strerror(0)` 实际文案（补丁 0014） |
| use_count | 同上（libc 文案宏） | 测试侧 libc 文案宏调整（补丁 0016） |
| osmo_io | 测试使用不可写的固定临时路径 | 改可写路径（补丁 0015） |
| 61 socket | musl `getaddrinfo` 对 SCTP 协议提示返回 `EAI_SERVICE`(-8)，重试逻辑过宽 | `src/core/socket.c`：重试收窄到仅 `EAI_SERVICE`（补丁 0008） |
| 86 / 其余 | 随上述修复一并通过 | — |

## 源码修改

全部改动以补丁形式交付（`patches/`，共 16 个，由 `ohc-run.py refresh-patch --auto` 生成）：

- `0001-config.guess.patch`、`0002-config.sub.patch` — 平台识别（linux-ohos）
- `0003-configure.patch` — 生成物同步（随 0001/0002 重生成）
- `0004-include-osmocom-core-hash.h.patch` — `__always_inline` 平台中立写法
- `0005-src-core-mnl.c.patch`、`0006-src-core-netdev.c.patch`、`0009-src-core-stats_tcp.c.patch`、`0011-src-gb-gprs_ns2_fr.c.patch` — `sockaddr_storage` 守卫（E091）
- `0007-src-core-sockaddr_str.c.patch`、`0008-src-core-socket.c.patch`、`0010-src-core-utils.c.patch` — 上游测试 69/61/47
- `0012-src-gsm-kdf-crypto.h.patch` — 补齐上游漏打包头文件
- `0013-tests-gb-gprs_bssgp_test.c.patch`、`0014-tests-lapd-lapd_test.c.patch`、`0015-tests-osmo_io-osmo_io_test.c.patch`、`0016-tests-use_count-use_count_test.c.patch` — 测试侧适配

约定：补丁不含 `__OHOS__` 平台宏（R8），全部为平台中立改法；`conandata.yml` 的 patches 条目**不写 `strip`**（conan 使用 patch_ng，`a/` `b/` 前缀自动剥离，`strip=0` 即正确——实测显式 `strip: 1` 会把新增文件写到上一层目录）。

## 依赖版本

| 依赖 | 版本 | 必要性 | 制品仓 |
|------|------|--------|--------|
| talloc | 2.4.4 | 必需（`PKG_CHECK_MODULES(TALLOC, talloc >= 2.1.0)`） | ✅ 有二进制 |
| libmnl | 1.0.5 | 可选（`with_libmnl` 默认开） | ✅ 有二进制 |
| libusb | 1.0.27 | 可选（`with_libusb` 默认开） | ✅ 有二进制 |
| pcsc-lite | 2.4.0 | 可选（`with_pcsc` 默认开） | ✅ 有二进制 |
| gnutls | — | 可选，平台不可用 | ❌ 制品仓无 → `--disable-gnutls` |
| liblksctp | — | 可选，平台不支持 SCTP | ❌ 制品仓无 → `--disable-libsctp` |

## 验证结果

- 编译：`conan create` 成功（configure/make/make check/make install 全部通过，0 error）
- 上游测试（`make check`，automake testsuite）：**88 passed / 2 skipped / 0 failed（共 90 项）**
  - 跳过项：`61 socket_sctp`（平台无 SCTP）、`87 osmo_io (uring)`（平台 uring 被 seccomp 拦截，配方向上游开关关闭）
  - 日志证据：`88 tests were successful.` / `2 tests were skipped.`
- 包内测试（`test_package`）：
  - `test.c`：冒烟（`osmo_hexdump` / `osmo_str_tolower` / `osmo_bcd2str` / `osmo_sockaddr_str_from_str` / `osmo_ctx_init` / `osmo_cbsp_errstr` / `osmo_amr_s_to_d`）
  - `test_ohos_tls.c`：鸿蒙专项——跨 DSO 访问库内 TLS（`osmo_ctx`）验证原生 TLS 语义（emutls 下该程序链接/运行均失败，作为反向证据）
- 产物：10 个库（libosmocore/libosmocodec/libosmocoding/libosmoctrl/libosmogb/libosmogsm/libosmoisdn/libosmosim/libosmousb/libosmovty）+ 头文件 + 10 个 `.pc`

## 交付物

- `conanfile.py` / `conandata.yml` / `patches/`（16 个）/ `test_package/`（含 `test.c`、`test_ohos_tls.c`、`MANIFEST.yml`）
- `reports/test-report.md`（上游测试与包内测试明细）
- 版本索引：`archives/l/libosmocore/manifest.yaml`

## 注意事项

- `--disable-gnutls/--disable-libsctp/--disable-uring` 为平台能力/依赖所限的默认关闭项；依赖具备后可改用 `with_*` 选项打开（libmnl/libusb/pcsc 已默认打开）。
- PCSC/USB/MNL 依赖在配置期为自动探测；配方已通过 `PkgConfigDeps` 注入 `.pc`，无需手工设置 `PKG_CONFIG_PATH`。
- 本地探索阶段曾遇到 `.la` 级联报错（`libmnl.so` 开发软链缺失）与 `pkg-config` 搜索路径问题，均为本机环境因素，**不属于交付内容**（配方通过 conan 依赖注入解决）。
- musl 与 glibc 的文案/errno/`getaddrinfo` 差异集中在测试期望适配（补丁 0014/0016/0008），不影响库语义。
---

**编译结束**: 2026-09-14 01:46
**最终状态**: published

## W4 独立审计（Pre-PR）

- 审计结论：`pass`（P0=0 / P1=0；P2=3、P3=3 均为非阻塞建议），报告见 `reports/audit-result.json`。
- 审计后按仓库规范（`.gitcode/code-style.md`）落地 3 处行为中立的整改，未重新触发 W3 编译：
  1. `conanfile.py` 方法顺序调整为 `export_sources → requirements → layout → source → generate → build`（§3：`layout()` 与 `requirements()` 对调；Conan 按方法名调用，运行时行为不变）。
  2. `conandata.yml` 中 4 个补丁的 `patch_type` 由 `"bugfix"` 统一为 `"portability"`（§12：`patch_type` 仅为元数据，不参与补丁应用）。
  3. 元数据一致性：版本 `manifest.yaml` 的 `source.tar_format` 由 `tar.gz` 修正为 `tar.bz2`（与 `conandata.yml` 源一致）、`configure_options` 注释修正为 shared 默认动态；软件级 `manifest.yaml` 依赖清单移除未被 `requires` 的 `liburing`；`README.md` 库清单修正为实际产出的 10 个库。
- 第 1/2 项属 CI 输入文件（`conanfile.py` / `conandata.yml`）的行为中立改动，W3 与 CI 均以当前文件重新构建验证。
