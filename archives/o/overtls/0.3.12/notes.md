# overtls 0.3.12 适配笔记

> 归档位置：`archives/o/overtls/0.3.12/` ｜ 分支：`feat/overtls-0.3.12`
> 设备：OpenHarmony PC aarch64（`uname -s`=HarmonyOS）｜ 基线：`upstream/main`

---

## 1. 源与版本（W0 · 源解三路）

| 项 | 值 | 取数命令 / 证据 |
|---|---|---|
| 权威上游 | `ShadowsocksR-Live/overtls`（默认分支 `master`，language=Rust） | GitHub API `repos/ShadowsocksR-Live/overtls` |
| 版本 | `0.3.12` | `Cargo.toml` `[package] version = "0.3.12"`（归档内逐字） |
| tag | `v0.3.12` → `59eba9b327e1a256712cc7ac426d2d084d825a0d` | `git ls-remote --tags https://github.com/ShadowsocksR-Live/overtls`（全 tag 形态核对，`v0.3.0`–`v0.3.15` 连续，`0.3.12` 在列） |
| 源 sha256 | `d0ed3ae88721e8ae2a525059a81ce29991af29de920bf580cb0999d0a7ac288b` | 见下表三路互证 |

**sha256 三路互证（2026-10-06 设备实测，三条独立下载路径逐字节一致）**

| 路 | URL | HTTP | sha256 |
|---|---|---|---|
| 1 | `https://github.com/.../archive/refs/tags/v0.3.12.tar.gz` | 200 | `d0ed3ae8…ac288b` |
| 2 | `https://codeload.github.com/.../tar.gz/refs/tags/v0.3.12` | 200 | `d0ed3ae8…ac288b` |
| 3 | 权威镜像 `gh-proxy.com` 同 URL（**仅用于校验**，未写入 conandata——PF7 镜像域名黑名单） | 200 | `d0ed3ae8…ac288b` |
| C | conan-center-index `recipes/overtls/all/conandata.yml` | **404** | 该包未进 CCI，无权威 sha 可抄——已按上游 + 双下载路径互证，如实记录 |

**先例纠偏**：任务卡写的知识域是「C++ TLS/WebSocket 隧道代理」，实测上游
`language=Rust`、纯 Cargo 工程（`lang-preflight --lang rust` → `detected=rust`，
rc=0）。选点知识域与实际语言不一致，按实测走 Rust 配方，未硬套 C++ 流程。

---

## 2. 依赖（W0 · 双源实证 + 平台可得性）

### 2.1 Conan 依赖

| 依赖 | 类型 | 实测 |
|---|---|---|
| `rust-toolchain/1.97.1` | `tool_requires`（Rust 工具链，宿主+目标 `aarch64-unknown-linux-ohos`） | ① `conan list -r=ohpcd 'rust*'` → `rust-toolchain/1.97.1` 命中；② `conan download 'rust-toolchain/1.97.1' -r=ohpcd --only-recipe` → **rc=0**（`874ec05d07ae08465bb25281d1d9a543`，已入本地缓存）；③ 包二进制 `6b129b068851896169fae42d399fa922d239ce8a` 在缓存内，`lib/rustlib/aarch64-unknown-linux-ohos` 标准库齐备（889MB） |
| 其它 `self.requires(...)` | — | **无**（Rust 侧依赖由 crates.io 解析，不进 Conan 图） |

### 2.2 TLS 面（openssl/mbedtls 类）—— 组件裁剪标注

**结论：不需要任何系统 TLS 库参与编译，无裁剪动作。**

上游 `Cargo.toml`（归档逐字）：

```toml
reqwest = { version = "0.13.4", default-features = false, features = ["rustls", "json"] }
rustls  = { version = "0.23.42", default-features = false, features = ["std","tls12","logging","ring"] }
tokio-rustls = { version = "0.26.4", default-features = false, features = ["logging","tls12","ring"] }
tokio-tungstenite = { version = "0.30.0", features = ["rustls-tls-webpki-roots"] }
webpki-roots = "1.0.8"
```

- **不需要任何系统 TLS 库参与编译**；`openssl-sys` / `native-tls` / `mbedtls`
  全树 0 命中（`grep -n 'openssl\|mbedtls' Cargo.toml` 无命中）。
- **但「只开 ring」对 `reqwest` 不成立，需一处补丁**（2026-10-06 实测纠偏）：
  `reqwest` 0.13.x 的 `rustls` feature 定义是
  `rustls = ["__rustls-aws-lc-rs", "dep:rustls-platform-verifier", "__rustls"]`，
  而 `__rustls-aws-lc-rs = ["hyper-rustls?/aws-lc-rs", "tokio-rustls?/aws-lc-rs",
  "rustls?/aws-lc-rs", ...]` —— **硬编码 aws-lc-rs**，与 overtls 自己在
  `rustls`/`tokio-rustls` 上声明的 `ring` 无关（Cargo feature 是并集）。
  首轮 `conan create` 因此把 `aws-lc-sys 0.45.0` 拖进构建并**链接失败**：
  - aws-lc-sys 走 CMake 路径，日志逐字
    `Neither OHOS_NDK_HOME nor OHOS_SDK_NATIVE are set! No toolchain found.`；
    `CMAKE_ASM_COMPILER` 已识别为 clang，但 `Building ASM object` **计数 = 0**，
    产物 `libaws_lc_0_45_0_crypto.a` 257 个成员中 0 个 aarch64 perlasm 目标
    （`llvm-ar t … | grep -iE 'armv8|neon|vpaes|aesv8'` 无命中）；
  - C 代码仍按「有汇编」编译 → 链接期 200+ 个 `aws_lc_0_45_0_*` 未定义
    （`ChaCha20_ctr32_neon`、`aes_hw_*`、`vpaes_*`、`bn_add_words`、`bn_mul_mont` …），
    原始日志 `$TASK_DIR/conan-create-1.log`（`ld.lld: error: undefined symbol`）。
- **处置：`patches/0001-Cargo.toml-reqwest-rustls-no-provider.patch`** 把 `reqwest`
  的 `"rustls"` 换成 `"rustls-no-provider"`（= `dep:rustls-platform-verifier` +
  `__rustls`，不启用任何 provider）。与上游设计一致、无功能损失，因为：
  - `src/lib.rs:36 ensure_rustls_crypto_provider()` 安装
    `rustls::crypto::ring::default_provider()`；`src/tls.rs:30/46` 显式用
    `rustls::crypto::ring::*` 密码套件建 `ClientConfig`（不依赖全局默认 provider）；
  - 唯一的全局默认 provider 消费者是 server 侧的 `reqwest::Client`
    （`src/panel_sync.rs:32`），而它在 `run_server` 里紧跟 `src/server.rs:42`
    的 provider 安装之后创建（`src/server.rs:93`）；
  - WS 握手自实现（`src/client.rs:577` 的 `tokio_tungstenite::client_async`
    已注释），`tokio-tungstenite` 只用到 `tungstenite::{handshake,error}` 子模块，
    其 TLS connector 不在调用路径上；且 `tokio-tungstenite 0.30` 的
    `__rustls-tls` 对 `tokio-rustls` 声明为 `default-features = false`，
    本身不引 aws-lc-rs。
  - 修后 `cargo tree -i aws-lc-rs` 逐字报
    `error: package ID specification 'aws-lc-rs' did not match any packages`，
    `cargo tree | grep -c aws-lc` = 0，全树只剩 `ring 0.17.14`。
- 双源实证：①归档 `Cargo.toml` 逐字；②`grep -rn 'openssl\|mbedtls' src/ Cargo.toml` = 0 命中。
- 与 README 的「TLS 面」小节同源；配方 docstring 亦记录该纠偏结论。

**唯一用到 OpenSSL 的是 cargo 自身的运行期动态库**（`libssl.so`/`libcrypto.so`/
`libz.so`，`rust-toolchain` 的 cargo `NEEDED`），由 Harmonybrew bottle 提供
（`conandata.yml` 的 `runtime_libs` 段，三个 URL **2026-10-14** 设备实测 **HTTP 200**
且下载 sha256 与 harmonybrew formula 索引 `/api/formula.jws.json` 逐字一致；
2026-10-06 首测时用的是旧 URL，旧文件其后被 rebuild 替换下架，见 §6-10；
`rust-1.97.1` bottle 实测 **404**，正是改用仓库内 `rust-toolchain` 包的原因）。

### 2.3 crate 下载面

`rsproxy.cn` sparse 镜像实测 **HTTP 200**（`https://rsproxy.cn/index/config.json`）。
配方在源码树 `.cargo/config.toml` **追加**（不覆盖上游 mips/ios 段）替换配置 +
`retry=10 / timeout=600 / low-speed-limit=1`。

---

## 3. 平台可移植性（W0-3）

| 判据 | 取数 | 结果 |
|---|---|---|
| ISA 专属头（`altivec.h`/`mmx.h`/`3dnow`/`emmintrin`/`immintrin`/`nmmintrin`） | `grep -rn --include='*.rs' --include='*.c' --include='*.h' -E 'altivec\.h\|mmx\.h\|3dnow\|emmintrin\|immintrin\|nmmintrin' . \| wc -l` | **0** |
| glibc printf 钩子（`printf.h` / `register_printf_`） | 同上正则 `printf\.h\|register_printf_` | **0** |
| 非 aarch64 架构硬路径 | `grep -rn --include='*.rs' 'target_arch' src \| wc -l` | **0**（无 `target_arch` 条件分支） |
| 内联 `asm!` | `grep -rn --include='*.rs' 'asm!' src \| wc -l` | **0**（asm 只存在于 `ring` crate 内，由 `cc` 按目标编译） |

架构档：`arch=armv8`（aarch64），Rust 目标三元组 `aarch64-unknown-linux-ohos`
（`rust-toolchain` 包 `lib/rustlib/` 下该目标 std 齐备）。

---

## 4. 网络 API 可用性（W0 · 一手探针，miniupnpd 先例）

overtls 的核心面是套接字（TCP/UDP/域名解析）。真机一手探针
`$HOME/tmp/overtls-0.3.12/probe/netprobe.c`（设备 clang 15 现编现跑）：

```
COMPILE_RC=0
PASS tcp loopback bind/listen/connect/accept/echo
PASS udp loopback sendto/recvfrom
PASS getaddrinfo numeric
PASS ephemeral bind x200/200
RUN_RC=0
```

四类 API 全部可用：`socket/bind/listen/connect/accept`（TCP 回环收发 8 字节一致）、
`socket/sendto/recvfrom`（UDP 回环）、`getaddrinfo`（数值主机）、临时端口
`SO_REUSEADDR` 连续 200 次 bind 全成功（共享设备端口面无压力）。

另：上游唯一注册测试 `test_config` 会对 `www.gov.cn:443` 发起真实 TCP 连接
（`src/tcp_stream.rs::std_create`，超时 10s），真机实测
`PASS connect www.gov.cn:443 in 0.05s`（DNS 解析到 `183.201.202.135`），
故该外网依赖在本环境可满足、按原样执行不改写。

---

## 5. 适配要点（配方实现）

1. **补丁（唯一源改动）**：`patches/0001-Cargo.toml-reqwest-rustls-no-provider.patch`
   —— `reqwest` 的 `"rustls"` → `"rustls-no-provider"`，去掉 OHOS 上无法链接的
   aws-lc-sys（详见 §2.2）。以 `conandata.yml` 的 `patches:` 段声明
   （`patch_type: portability`、`strip: 1`），由 `apply_conandata_patches()` 在
   `build()` 首步施加；`export_conandata_patches()` 已把 `patches/` 纳入导出。
2. **工具链供给**：`tool_requires("rust-toolchain/1.97.1")` → 若系统无可执行
   cargo/rustc，从工具包 `bin/` 复制 `cargo`/`rustc` 与 `lib/librustc_driver-*.so`
   到构建目录，用 `binary-sign-tool -selfSign 1` 逐个自签名（OHOS 对无签名二进制
   直接 `Permission denied`），并以 `RUSTFLAGS=--sysroot=<工具包目录>` 固定 sysroot
   （搬离包目录会 `E0463 can't find crate for std`）。**用「真能跑」判定可用性，
   不用 `os.access`**（权限位与可 exec 不等价）。
3. **cargo 运行期库**：`_fetch_runtime_libs()` 从 conandata `runtime_libs` 下载
   openssl@3 / zlib-ng-compat / ca-certificates bottle，解包后注入
   `LD_LIBRARY_PATH` 与 `SSL_CERT_FILE`；候选集失败自动切 `runtime_libs_fallback`。
4. **crates 镜像**：源码树 `.cargo/config.toml` **追加**（幂等标记
   `# overtls-recipe: crates mirror`）rsproxy sparse 替换段 + 网络容错参数，
   不覆盖上游文件（上游含 mips/ios 链接器段）。
5. **构建环境**：`CC/CXX=/data/service/hnp/bin/clang[++]`、
   `RUSTFLAGS=--sysroot=… -C linker=clang`、`AR=llvm-ar`、`CARGO_BUILD_JOBS=1`、
   `TMPDIR/TMP/TEMP=<build>/tmp`（OHOS `/tmp` 只读）。
6. **构建与上游测试**：`cargo build --release`（**无 `--locked`**，见 §6-1），
   随后 `cargo test --release --lib`，解析框架 `test result:` 行输出
   `HMBS_UPSTREAM_TEST_RESULT` marker；任一项 `failed>0` 或 `executed==0` 即判失败。
7. **打包**：`bin/overtls-bin` + `licenses/LICENSE` + `share/overtls/config.json`
   （上游默认配置样例）；`package_type="application"`、`cpp_info.bindirs=["bin"]`。
8. **profile**：`-pr:h` 与 `-pr:b` **都用 `ci/conan/profiles/ohos-aarch64`**
   （与 `ci/conan/build_and_test.sh:316` 一致）。用 `-pr:b=default` 会因
   `default` profile 缺 `os.version` 报
   `rust-toolchain/1.97.1: Invalid: 'settings.os.version' value not defined`（rc=6）。

---

## 6. 已知问题 / 限制

1. **无 `Cargo.lock`**：上游 `.gitignore` 忽略 lock 文件，tag 归档内也没有 →
   不能用 `cargo --locked`，依赖解析由 rsproxy 在构建时完成。跨时间重建可能解析到
   不同的 semver 兼容小版本，可复现性弱于带 lock 的 Rust 包。
2. **doc-test 不可执行**：工具链 `bin/` 内无 `rustdoc`。v0.3.12 `src/` 内
   `grep -rn '```' src | wc -l` = **0**、`#[cfg(test)]` = 0，不存在被跳过的真实
   doctest；用 `--lib` 目标运行单元测试。
3. **上游唯一测试依赖外网**：`test_config` 连 `www.gov.cn:443`（见 §4），离线环境会
   失败；本环境实测可达。
4. **`--version` 含构建时刻**：上游 `build.rs` 把 `BUILD_TIME` 编进版本串
   （`<crate_version> (<GIT_HASH> <BUILD_TIME>)`），产物不可逐字节复现属上游设计，
   非适配缺陷；`test_package` 因此只断言版本号子串、不锚定整串。
5. **上游 tag 与 HEAD 的测试数差**：见 §7。
6. **服务端对隧道目标有 SSRF 防护，代理不到内网/回环目标**（上游设计，非适配缺陷）：
   `src/server.rs:664 tcp_stream_from_s5_address()` 对每个候选地址无条件判
   `addr_is_private()`（private / loopback / link-local / benchmarking）并 `continue` 跳过，
   `server_settings` 里**没有任何开关**可以放开（`Server` 只有
   `disable_tls/panel_sync/certfile/keyfile/forward_addr/listen_host/listen_port`）。
   实测（2026-10-06）以 127.0.0.1 为隧道目标时服务端逐字打
   `[WARN] … destination address is private, skipping` +
   `[ERROR] … All addresses failed to connect`，随后回 `End session`，客户端随即断开
   SOCKS5 连接（探针侧表现为 `Connection reset by peer`）。
   影响：`test_package` 的 D 组数据面断言因此**不能**用 127.0.0.1 作目标，改用
   `0.0.0.0`（不在上述四类内，而 Linux/OHOS 内核对 `connect(0.0.0.0:port)` 按回环处理，
   仍真实落到本机回显目标）；用户侧若确需代理内网目标，上游需自行放开该检查。
7. **`reqwest` 的 `rustls` feature 会拖进 aws-lc-sys，必须打补丁**：见 §2.2 与
   `patches/0001-Cargo.toml-reqwest-rustls-no-provider.patch`；同时沉淀为图谱草稿
   `knowledge/drafts/E754-draft-49EF.kv`（引擎对该错误 Phase B 未命中）。
8. **CI 的 L0g「硬编码 remote」检查对 conanfile docstring 误报（已按包侧改写规避）**：
   `ci/conan/build_and_test.sh` 的 L0g 判据是**整文件** grep
   `conan\s+(install|download|create|upload|export).*\s-r[= ]`，不剥 docstring/注释。
   本配方 v3.0 docstring 为披露 `rust-toolchain/1.97.1` 的平台可得性证据，逐字写了取数
   命令，因而被判 `L0 gate: hardcoded_remote`（2026-10-06 首次 `finish` Step 5 = W3
   阻塞；同轮其余 L0——L0i/L0j/L0k/L0m——全部 pass）。
   **配方运行期从未绑定 remote**：`requirements()/tool_requires` 与全部 `self.run`
   均无 `-r`/remote 参数，remote 由 CI 的 `setup.sh` 注入（W3 日志第 6 行
   `remote 已就绪: ohpcd`）。处置：docstring 改为陈述同一事实但不含 `-r=` 字面量的写法
   （remote 名 `ohpcd`、`conan list` 与 `conan download --only-recipe` 双证结论、
   "运行期不绑定 remote" 均保留，证据未丢失）。**原始取数命令逐字留痕**（供审方复核）：
   `conan list -r=ohpcd "rust-toolchain/1.97.1:*"` 与
   `conan download -r=ohpcd --only-recipe rust-toolchain/1.97.1`。
   工具缺陷（L0g grep 不剥注释/docstring，与 pre-push H4 闸同类）已登记
   `$WORKSPACE_ROOT/feedback/pending/2026-10-06-overtls-0.3.12.md`。
9. **CI 预下载器改写的 `file://` 路径与 conan 的百分号解码不一致（配方侧已加兼容）**：
   `ci/conan/build_and_test.sh` 的 pre-download 段把 `conandata.yml` 里的 URL 原地改写成
   `file://<predl_dir>/<md5(url)[:8]>_<URL 末段>`，**末段保留百分号编码**；而 conan 打开
   `file://` 时对路径做**百分号解码**。本包 `runtime_libs` 的 openssl bottle 末段是
   `openssl%403-3.6.5_1.arm64_ohos.bottle.1.tar.gz`（`%40` = `@`，**服务器只认编码形**：
   实测裸 `@` 形态 HTTP 404、`%40` 形态 HTTP 200 且 sha256 与声明一致 `ae1d5bf9…`；
   2026-10-06 的原始证据用的是旧 URL `openssl%403-3.6.4_1…` + sha `29caefb9…`，
   其后旧文件被 rebuild 替换下架，见 §6-10；机制结论不变），
   于是预下载写出的字面文件 `12efbf34_openssl%403-…` 存在、conan 要找的解码名
   `12efbf34_openssl@3-…` 不存在 ⇒ `_fetch_runtime_libs()` 内 `get()` 抛
   `FileNotFoundError: [Errno 2] No such file or directory: '…/predl_cache/12efbf34_openssl@3-…tar.gz'`
   （2026-10-06 W3/`build_and_test.sh` 实测阻塞；`conan-verify` 直连 HTTPS 路径不复现，
   故本地 G2 全绿而 W3/CI 红，属跨门禁不一致）。
   处置（**配方侧兼容，不动 `ci/**`**）：`conanfile.py` 新增
   `_materialize_predl_alias(url)`——仅当 URL 是 `file://`、字面路径存在且其 `unquote()`
   解码名缺失时，按解码名补一份硬链接（失败退回拷贝），使 conan 能按其自身口径找到
   文件；**文件内容与 sha256 仍由 `get()` 亲自校验**，完整性判据不降级；非 `file://`
   与无 `%XX` 的 URL 一律原样放行（设备直连路径上是空操作）。
   端到端预演（真实 pre-download 段 + 本函数）：改写出的 8 个 `file://` URL 全部可解析，
   其中仅 openssl 一条 `needs_alias=True`，其余原生直达；解码名 sha256 与声明值一致。
   工具缺陷与「引擎误命 E333（同签名家族、但根因是连字符截断且已修）」见
   `$WORKSPACE_ROOT/feedback/pending/2026-10-06-overtls-0.3.12.md` F6。
10. **Harmonybrew bottle 是滚动替换制：rebuild/revision 换发后旧文件即 404**
    （本包 CI build#89760 `conan-build-test` 步确定性红的根因，2026-10-14 修复）。
    实测时间 **2026-10-14 14:26–14:36 CST**（06:26–06:36 UTC）：
    - `openssl%403-3.6.4_1.arm64_ohos.bottle.tar.gz` → **HTTP 404**（配方钉的
      3.6.4_1 已被 3.6.5_1 取代下架——CI 日志两候选均死在这一条）；
    - `zlib-ng-compat-2.3.3_2.arm64_ohos.bottle.tar.gz` → **HTTP 404**（版本号
      **没变**，harmonybrew 以 rebuild 1 重发为 `…bottle.1.tar.gz`，无 `.1` 的旧
      文件被替换掉；编排方按纯版本号逐个探测全部 404 即此因）；
    - `ca-certificates-2026-09-25.arm64_ohos.bottle.tar.gz` → 仍 **200**，但索引
      已指 revision 1 的 `…2026-09-25_1…`；
    - 权威在架清单取数：`https://harmonybrew.atomgit.com/api/formula.jws.json`
      （4775 个 formula，`bottle.stable.files.arm64_ohos.{url,sha256}` 字段即
      bottle URL 与 sha256，比逐版本号探测可靠）；三条新 URL 实测 **HTTP 200**、
      真实下载 sha256 与索引逐字节一致：openssl@3 `ae1d5bf9…`、
      zlib-ng-compat `7092bfe7…`、ca-certificates `1219809a…`。
    影响面：**其他包钉的旧 bottle URL 同样是地雷**（本包只修自己；发现已登记
    `$WORKSPACE_ROOT/feedback/pending/2026-10-14-overtls-0.3.12-ci-fix.md`
    供维护方全局处理）。配方 `runtime_libs` 与 `runtime_libs_fallback` 两段同步
    换新；新 openssl URL 末段仍含 `%40`，§6-9 的预下载别名机制继续生效，
    zlib/ca 两条无 `%XX`、该函数按设计空操作。

---

## 7. 上游测试清点（R51 三步法 · 第 1 步）

统计单位统一为「源码 `#[test]` / `#[x::test]` 注册数」（源码宏口径），不与
assertion 数、消费者断言数混用。

**（a）被适配 tag v0.3.12**（= conandata 下载并校验 sha256 的归档）

```sh
grep -rn --include='*.rs' -E '#\[test\]|#\[[a-z_]+::test\]' src | wc -l   # → 1
grep -rn --include='*.rs' 'cfg(test)' src | wc -l                          # → 0
ls -d tests benches examples                                               # → 均不存在
grep -rn --include='*.rs' '```' src | wc -l                                # → 0
# src/config.rs:577:#[test]   fn test_config()
```

**（b）上游当前 HEAD `3829e3c0c3b1a53a79c06d4693b6369964882879`（2026-10-05）**

```sh
git clone --depth 1 --sparse https://github.com/ShadowsocksR-Live/overtls && \
  git sparse-checkout set src
grep -rn --include='*.rs' -E '#\[test\]|#\[[a-z_]+::test\]' src | wc -l   # → 4
# src/config.rs:543:#[test]   fn test_client_listen_url_deserialization()
# src/config.rs:573:#[test]   fn test_config()
# src/server.rs:826:#[test]   fn ignores_read_access_to_tls_files()
# src/server.rs:835:#[test]   fn accepts_modifications_to_tls_files()
```

**N = 候选数法最大值 = max(1, 4) = 4**（§3.5：声明 N 的下界 = 上游当前 HEAD 的
注册项数）。差额 3 项逐项归因：`config.rs:543`、`server.rs:826`、`server.rs:835`
三个 `#[test]` 都在 tag v0.3.12 **之后**由上游新增（HEAD 提交 `3829e3c` 及其前序），
**v0.3.12 源码树中不存在这三个注册项** → 本版本可运行分母 N′ = 1，
既不是「运行失败」也不是「跳过」。

---

## 8. 测试执行结果

> 本节与 `reports/test-report.md`、PR 正文统计表同源，全部由真实设备日志复算；
> 数值以采信轮（清缓存 `conan create`）日志为准，见 `reports/conan-create.log`。

### 8.1 上游测试（源码宏口径）

| 指标 | 数值 | 取数命令 / 证据 |
|---|---|---|
| 声明 N（候选数法最大值） | **4** | 上游当前 HEAD `3829e3c0c3b1a53a79c06d4693b6369964882879` 的 `#[test]` 注册数 |
| 本版本可运行 N′ | **1** | tag v0.3.12 源码树内注册数（`src/config.rs:577`） |
| PASS | **1** | 框架输出 `test result: ok. 1 passed; 0 failed; 0 ignored; ...` |
| FAIL | **0** | 同上 |
| SKIP | **0** | 同上（`0 ignored`） |
| NOT_RUN | **3** | tag 之后上游新增，本版本源码树内不存在（逐项归因见 §7） |

`TOTAL = PASS + FAIL + SKIP + NOT_RUN = 1 + 0 + 0 + 3 = 4`（与声明 N 一致）。
配方采集 marker 逐字：
`HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"cargo-test","command":"cargo test --release --lib","discovered":1,"executed":1,"passed":1,"failed":0,"skipped":0}`

### 8.2 消费者端到端（鸿蒙特有分栏，`test_package`，不计入上游分母）

| 指标 | 数值 |
|---|---|
| 断言总数（discovered = executed） | **14** |
| PASS | **14** |
| FAIL | **0** |
| SKIP | **0** |

marker 逐字：
`HMBS_TEST_PACKAGE_RESULT={"status":"passed","framework":"test_overtls.sh","discovered":14,"executed":14,"passed":14,"failed":0,"skipped":0}`

分栏明细：A 组 CLI 契约 3、B 组配置校验负向 1、C 组服务发现 4、D 组数据面 4（含
SOCKS5 → WS 隧道 → 服务端出站 TCP → 回显目标的 41 字节真实往返）、E 组打包产物 2。

### 8.3 采信轮记录

| 轮次 | 被审 SHA | rc | 结论 |
|---|---|---|---|
| 1 | `164974f34f90b04c6d12b37ae1896b3c47e5369f` | 1 | **非干净轮，非配方缺陷**：`conan create` 在设备内存耗尽窗口被 OOM 打断（`Caused by: Out of memory (os error 12)`，cargo 起 `rustc` 失败），日志见 `$TASK_DIR/iter/round1.log`。按纪律未进 `finish`，待健康窗口重跑 |
| 2 | `ba955b3276bca3e314981e566808113e6686134b` | 0 | 干净轮（`{run_make:1, calling_build:1, apply_patch:1}`，实跑 G4/L2/L4/L5 = 4/4）。`finish` 被 CI 的 `L0g` 硬编码 remote **误报**阻塞（判据整文件 grep，命中 docstring 里的取数命令 `conan … -r=ohpcd`）→ 包侧改写 docstring 后重跑（见 §6.8） |
| 3 | `e85c726110fef4e30561d992c072252ea3549a44` | 0 | 干净轮。`finish` 被 CI 预下载器的 `file://` 百分号解码不一致阻塞（`predl_cache/12efbf34_openssl@3-…tar.gz` 不存在；`%40` 编码名才是盘上文件）→ 配方加 `_materialize_predl_alias()` 兼容后重跑（见 §6.9） |
| 4 | `d09c902fec595261bd6e9c2df583271a7760086b` | 0 | 干净轮：`{run_make:1, calling_build:1, apply_patch:1}`，实跑 G4/L2/L4/L5 = 4/4，证据副本与快照齐备。`finish` **rc=0**：W3 本地 CI 模拟 **1/1（100%）**，`L0_RESULT=pass` / `L1_RESULT=pass`（含 L1e 反向 sabotage）/ `L2_RESULT=pass` / `L4_RESULT=pass` / `L5_RESULT=pass`；`capture_evidence --verify` rc=0。ℹ️ 本 SHA 首发轮（同为干净轮候选）被**监控通道中断**（`SIGTERM`，rc 缺失、日志无结论行），按 `notes/device-facts.md §二.21` 判为伪影：清缓存四步重做并确认 DB 两表为空后**同参原样重挂**，即本行读数 |
| 5 | `1cece6599cfb083d154ccf28df5b43559c9d3f8b` | 0 | **终态干净轮**：`{run_make:1, calling_build:1, apply_patch:1}`，实跑 G4/L2/L4/L5 = 4/4；`capture_evidence --verify` rc=0（索引 sha 与本 SHA 一致）。本 SHA 系**推送前重定基线**后的分支 HEAD：`git push` 先扫后推发现 `origin/main..HEAD` 含 1 个 >10 MiB 对象（`archives/c/clownresampler/3.24/tests-ref/test1.b64`，11290188 B，上游 `80c0555` 引入），会触发 fork pre-receive 的单文件 10 MiB 上限，故按处置口径 `git rebase --onto 80c0555^ upstream/main` 重定基线（**只换父提交**）；重扫 `origin/main..HEAD` 的 >10 MiB = **0**。**交付面逐字节未变的证明**：13 文件 blob SHA 全同、`git diff 52075a062b 1cece6599c -- <13 文件>` 为空、三点 diff 仍 **13 文件 / +1952 −0**、`pr.diff` sha256 `9fb39dedc931d751…` 与重定前相同。ℹ️ `reports/w3-local-ci.log`（W3 1/1 pass）由第 4 轮 `finish` 产出，因两轮树逐字节相同而对本 SHA 继续有效；重定基线后未重跑 `finish`（其判据为内容级） |
