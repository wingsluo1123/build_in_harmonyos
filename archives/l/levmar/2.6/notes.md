# levmar 2.6 HarmonyOS 适配笔记

## 任务信息

- 任务号：15559（活动「开源鸿蒙PC积分赛-依赖」）
- 分支：`feat/levmar-2.6`
- 上游：`https://www.ics.forth.gr/~lourakis/levmar/`，官方 tarball `levmar-2.6.tgz`
- 包/版本：`levmar/2.6`，归档目录 `archives/l/levmar/2.6/`
- 构建系统：上游同时提供 CMake 与手写 Makefile；本配方采用 CMake

## W0 依赖检查

- `conan download` 逐个探测：上游源码与 CMake 工程没有任何第三方依赖。
- 上游 CMake 默认 `HAVE_LAPACK=1`（并把 `LAPACKBLAS_DIR` 默认成 `/usr/lib`），
  但 README 明确说明关掉 LAPACK 后 levmar「totally self-contained」（用自带 LU 求解器）。
- OHOS sysroot 无 LAPACK/BLAS，制品仓也没有可用的 lapack 包；因此显式
  `HAVE_LAPACK=0`，不引入任何未发布依赖，也不把宿主 `/usr/lib` 带进链接行。

## 源码获取（本包的实际阻塞点）

- 官方源 `https://www.ics.forth.gr/~lourakis/levmar/levmar-2.6.tgz` 服务端**只发送 2 张证书**，
  缺失签发叶证书的中间 CA `GEANT TLS RSA 1`：
  - `openssl s_client -connect www.ics.forth.gr:443 -servername www.ics.forth.gr -showcerts`
    → 只有 2 个 `BEGIN CERTIFICATE`，`Verify return code: 21 (unable to verify the first certificate)`
  - `curl`（未加 `-k`）→ `curl: (60) SSL certificate problem: unable to get local issuer certificate`
  - `conan source` → `ConanException: Error downloading file https://www.ics.forth.gr/...:
    SSLError(... CERTIFICATE_VERIFY_FAILED ... unable to get local issuer certificate)`
- 这不是本机 CA 缺失：同一个 CA bundle 对 `https://curl.se/ca/cacert.pem` 返回 200、
  对 `api.gitcode.com` / `conan.cnb.cool` 均完成 TLS 握手；只有 ics.forth.gr 失败。
- 处置：见下面「返修」一节——**最终采用官方入口主机的 http 直链 + sha256 固定**。
  早期曾只用 `经验库 §12.55` 的共享下载缓存预置（`core.sources:download_cache`，
  条目 `s/<sha256>` + 同 stem 的合法 JSON sidecar，先删 `.dirty` 标记，
  `conan create` 日志出现 `retrieved from local download cache` 即命中），
  该缓存**不随 PR 进 CI**，故 CI build #97837 仍在 `source()` 阶段红——这正是本次返修的起因。
- ⚠ 该域名不在 CI 的镜像映射表（`ci/conan/build_and_test.sh` 的镜像正则只覆盖
  github/gnu/gnome/kernel/sourceforge 等），CI 侧预下载用的 `curl` 环节还缺 `curl` 本体
  （`[Errno 2] No such file or directory: 'curl'`），故预下载兜底在该链路上恒不可用，
  取源完全依赖 conan 自身的下载路径。

## 首条真实错误（未注入策略时的原文）

```
CMake Error at CMakeLists.txt:4 (CMAKE_MINIMUM_REQUIRED):
  Compatibility with CMake < 3.5 has been removed from CMake.

  Update the VERSION argument <min> value.  Or, use the <min>...<max> syntax
  to tell CMake that the project requires at least <min> but has been updated
  to work with policies introduced by <max> or earlier.

  Or, add -DCMAKE_POLICY_VERSION_MINIMUM=3.5 to try configuring anyway.

-- Configuring incomplete, errors occurred!
```

## 上游工程事实（一手，来自解包后的源码）

- `CMakeLists.txt:4`：`CMAKE_MINIMUM_REQUIRED(VERSION 2.6)`。
- `CMakeLists.txt` 内**没有** `install()` 规则：`grep -n "install(" CMakeLists.txt` 无命中，
  只能由配方显式收集制品。
- **没有** `enable_testing()` / `add_test()`：`ctest` 输出 `No tests were found!!!`，
  上游 tarball 顶层也没有 `tests/` 目录（只有 `matlab/` 示例与 `lmdemo.c` 示例程序）。
- `CMakeLists.txt:50`：`CONFIGURE_FILE(${CMAKE_CURRENT_SOURCE_DIR}/levmar.h.in
  ${CMAKE_CURRENT_SOURCE_DIR}/levmar.h)`——生成头写回**源目录**，不在构建目录；
  打包必须从 source 目录取 `levmar.h`（tarball 里那份是 Makefile 用的预生成版本，
  配置阶段会被覆盖）。
- `CMakeLists.txt:63`：`ADD_LIBRARY(levmar STATIC ...)`，上游只产出静态库。
- `levmar.h.in` 用 `#cmakedefine HAVE_LAPACK`：关掉 LAPACK 后公共头不再声明
  `dlevmar_lec/blec/bleic/blic/leic/lic_*` 一族（约束类）符号，消费者测试只能使用
  无 LAPACK 也声明的 `dlevmar_dif` / `dlevmar_bc_dif`。

## 配方要点

- `generate()`：`CMAKE_POLICY_VERSION_MINIMUM=3.5`、`HAVE_LAPACK=0`、`NEED_F2C=0`、
  `BUILD_DEMO=ON`、`user_presets_path=False`。
- `build()`：`apply_conandata_patches()` → `cmake.configure()` → `cmake.build()`；
  `can_run()` 为真时运行上游示例 `lmdemo` 并解析其输出断言收敛
  （Meyer 问题默认解 `(2.4818, 6.1813, 3.50…)`，`reason` 落在 LM 的停止码 1–4）。
- `package()`：显式收集 `liblevmar.a`（构建目录）、`levmar.h`（源目录，生成头）、
  `LICENSE`。不调用 `cmake.install()`（上游没有 `install` 规则，调用只会得到空包）。
- `package_info()`：`libs=["levmar"]`、`cmake_file_name/target_name`、OHOS/Linux 下
  `system_libs=["m"]`；纯库包，无 `bin/` 产物 ⇒ 不提供 `commands.json`。

## 已试过但未采用的路径

1. **直接 `cmake -S . -B build`（不加策略下限）**：CMake 4.1.2 立即报
   `Compatibility with CMake < 3.5 has been removed`，配置不成立。
2. **保留上游默认 `HAVE_LAPACK=1`**：会去链接 `LAPACKBLAS_DIR=/usr/lib` 下的
   `lapack/blas`，而 OHOS sysroot 与制品仓都没有，必然链接失败；且把宿主绝对路径
   带进交叉链接行，属已知反模式。已改 `HAVE_LAPACK=0`。
3. **用 `cmake.install()` 打包**：上游没有任何 `install()` 规则，安装结果为空。
4. **把 `lmdemo` 当上游测试套件申报**：`lmdemo.c` 的 `main()` 只跑一个默认问题且
   恒 `return 0`，没有断言、没有失败退出码，不能当作上游自动化测试；只在
   `build()` 里作示例 smoke test，并在正文按「上游无自动化测试」如实申报 0。

## 测试账本（五维）

| 维度 | 读数 | 说明 |
|---|---|---|
| `N_static` | 0 | tarball 顶层无 `tests/`；`grep -rn "add_test\|enable_testing" CMakeLists.txt matlab/CMakeLists.txt` 无命中 |
| `N_registered` | 0 | 无 CTest/其他测试框架注册；`ctest --test-dir build` → `No tests were found!!!` |
| `N_executed` | 0 | 无上游自动化用例可执行 |
| 未执行分类数 | 0 | 无（不是跳过，而是上游不存在） |
| `N_consumer` | 1 | `test_package/test_levmar.c`，7 条断言，真实编译+链接+运行+断言退出码 |

## 本机验证（B 机构建机，同一台即目标设备）

- 源码：官方 tarball 81143 字节，sha256 `3bf4ef1ea4475ded5315e8d8fc992a725f2e7940a74ca3b0f9029d9e6e94bad7`（与 conandata 一致）。
- 交叉编译探针（`clang --target=aarch64-linux-ohos --sysroot=<OHOS SDK>`）：
  `liblevmar.a` 与 `lmdemo` 均构建成功，只有 `#warning LAPACK not available` 一类提示。
- `lmdemo` 在设备上运行成功：`Levenberg-Marquardt returned 208 in 208 iter, reason 2`，
  解 `2.481778 6.181346 3.502236`，最终残差 `8.79e-05`。
- 消费者测试独立编译运行通过：`TEST PASSED (0 failed assertion(s))`，
  `dlevmar_dif` 21 次迭代收敛到 `(5.000000 0.800000 0.350000)`，
  `dlevmar_bc_dif` 同样到达同一极小点。

## 知识查重（B 判定）

- `B判定=create`：新增草稿 `knowledge/drafts/DRAFT-levmar-2.6-official-source-incomplete-tls-chain.{kv,md}`
  （官方源服务端 TLS 证书链不完整 ⇒ 判别法 + sha256 下载缓存预置处置）。
- 复用既有条目：E187 / E1497（旧版 CMake 策略下限、无 install/无 CTest 的显式制品收集与诚实测试记录）。
- `draft-review` 结果：与 E185 / E604 `score=0.52 (sig=0.9)`、E1594 `0.35`，预审建议
  `review-similar → E185`（灰区，人工裁定）。差异已写进草稿 root_cause / limitations：
  E185/E034 的根因是**客户端信任库缺失**，本条根因是**服务端缺中间 CA**，
  解法是既有条目没有的"判别法 + 内容 sha256 键控下载缓存预置"。

## 返修（2026-10-18 01:2x–01:3x）：把取源换成官方入口的 http 直链

**起因**：PR #16617 / 平台任务 15559 的 CI build #97837 `results=2 failure`，首条真实错误
是下载 `https://www.ics.forth.gr/~lourakis/levmar/levmar-2.6.tgz` 时
`SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
unable to get local issuer certificate'))` ⇒ `conan create failed`。

**一、先取证（全部一手读数，B 机构建机 2026-10-18 01:20–01:22）**

```
# ① 改前 URL（官方 https）——本机同样失败，与 CI 同源，确认不是 CI worker 特有
$ curl -sS -o before-https.tgz -w 'code=%{http_code} size=%{size_download}\n' \
    https://www.ics.forth.gr/~lourakis/levmar/levmar-2.6.tgz
code=000 size=0                     # curl: (60) SSL certificate problem: unable to get local issuer certificate

# ② 同站 http://www.ics.forth.gr/... 会 301 跳到 https ⇒ 不可用
$ curl -sS -o /dev/null -w 'code=%{http_code} redirect=%{redirect_url}\n' \
    http://www.ics.forth.gr/~lourakis/levmar/levmar-2.6.tgz
code=301 size=264 redirect=https://www.ics.forth.gr/~lourakis/levmar/levmar-2.6.tgz

# ③ 作者官方下载页列出的入口主机 users.ics.forth.gr：http 直链 200，且无跳转
$ curl -sS -o after-http.tgz -w 'code=%{http_code} size=%{size_download}\n' \
    http://users.ics.forth.gr/~lourakis/levmar/levmar-2.6.tgz
code=200 size=81143
$ curl -sSI http://users.ics.forth.gr/~lourakis/levmar/levmar-2.6.tgz | head -6
HTTP/1.1 200 OK
Last-Modified: Wed, 30 Nov 2011 08:11:31 GMT      # = 上游 2.6 发布日
Content-Length: 81143
Content-Type: application/x-gzip

# ④ 两次 sha256 读数（逐字节一致）
改前 URL 一侧的记录值（conandata 原值，也是旧 URL 当时下到的文件、仍留在 dlcache 里的那一份）：
  3bf4ef1ea4475ded5315e8d8fc992a725f2e7940a74ca3b0f9029d9e6e94bad7   (81143 字节)
改后 URL 一侧的实测值（python hashlib.sha256 对 after-http.tgz 现算）：
  3bf4ef1ea4475ded5315e8d8fc992a725f2e7940a74ca3b0f9029d9e6e94bad7   (81143 字节)
⇒ 两次读数逐字相同。（本次「改前 URL」无法再下到文件：https 在校验阶段即失败、0 字节，
  故改前一侧只能用 conandata 记录值 + 旧 URL 留下的 dlcache 实体文件作读数。）
```

**二、官方性佐证**：作者官方下载页 `http://users.ics.forth.gr/~lourakis/levmar/`
（`<title>Levenberg-Marquardt in C/C++</title>`）里「Download code / Latest」一项的链接是
**相对链接** `levmar-2.6.tgz`（`<li>Latest: <a href="levmar-2.6.tgz">levmar-2.6</a>`），
即解析到 `http://users.ics.forth.gr/~lourakis/levmar/levmar-2.6.tgz`——这就是作者本人列出的
官方入口，不是第三方镜像/代理/池。`www.ics.forth.gr` 只是同一作者站点的另一主机名。

**三、改动**：`conandata.yml` 的 `sources.url`
- 改前：`https://www.ics.forth.gr/~lourakis/levmar/levmar-2.6.tgz`
- 改后：`http://users.ics.forth.gr/~lourakis/levmar/levmar-2.6.tgz`
- `sources.sha256` **不动**（`3bf4ef1e…bad7`）：完整性由内容哈希固定，不依赖传输层。

**四、PF7/R39 官方托管例外声明（显式、非静默跳过）**
`scripts/ohc/preflight.py` 的 PF7 对明文 http 源的读数（本机实跑）：
`PF7 源URL闸(R39): archives/l/levmar/2.6/conandata.yml:11 明文 http 源（R39 要求 https）`。
该闸自身的处置口径是「确属官方托管例外须 PR 说明并 `--no-preflight` 跳过」；本条正属该例外：
**官方源的 https 在服务端就是坏的**（缺中间 CA，任何标准客户端都无法建立校验连接），
唯一能取到**逐字节相同的官方归档**的入口是该官方站点的 http 直链，故按例外登记：
PR 正文「补充说明」已写明理由 + 两行复现命令 + sha256 读数；
R39 要求的「官方源」性质仍满足（同一作者/同一机构的官方站点）。
⛔ 仍未使用：`-k` / `--no-check-certificate` / `verify=False`、任何第三方代理·镜像·池地址、
把 tarball 塞进仓库、改 CI 脚本。

**五、返修后本地复验（同一 B 机，真下载：先把 dlcache 条目临时移走）**

```
$ sh 经验文档/tools/build-slot.sh --kind short --mem 2000 --wait 900 -- sh run-verify2.sh
SLOT_ACQUIRE: kind=short mem=2000MB jobs=0(预算 BUILD_SLOT_JOBS=20)
SLOT_OK 01:33:01 ... ; SLOT_DONE:ok MemAvailable=4968MB
```

`archives/l/levmar/2.6/reports/conan-create.log` 关键原文：

```
levmar/2.6@ohpcd/stable: WARN: network: Error downloading file
  http://users.ics.forth.gr/~lourakis/levmar/levmar-2.6.tgz: 'HTTPConnectionPool(host='users.ics.forth.gr',
  port=80): Max retries exceeded ... (Caused by ProtocolError('Connection aborted.',
  RemoteDisconnected('Remote end closed connection without response')))'
levmar/2.6@ohpcd/stable: Waiting 5 seconds to retry...
levmar/2.6@ohpcd/stable: Sources correctly downloaded from http://users.ics.forth.gr/~lourakis/levmar/levmar-2.6.tgz
levmar/2.6@ohpcd/stable: Uncompressing levmar-2.6.tgz to .
```

- 结论：**新 URL 经 conan 自身下载器实测可用**（`Sources correctly downloaded`），
  sha256 校验通过（不符会抛 `ConanException`）；dlcache 条目被 conan 重新落盘且
  sidecar `references` 已记为新 URL ⇒ 证据链闭合（不是缓存命中）。
- 首包被服务端掐掉一次（日志原文 `RemoteDisconnected('Remote end closed connection without response')`，
  该站响应带 `Set-Cookie: cookiesession1=…`，首个请求偶发此现象），
  conan 默认 `retry=2 / retry_wait=5s` 已自动重试成功；CI 同参，无需改配方。
- 本地复验 `Verdict: PASS`（G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS），
  test_package：`TEST PASSED (0 failed assertion(s))`。

**六、残余风险（如实记录）**：CI worker 对 `users.ics.forth.gr:80` 的出网可达性、
以及首包被掐后的重试窗口，本机无法替 CI 证明；若 CI 仍红，第一条真实错误将直接判定归属。

## 收尾

**编译结束**: 2026-10-18 00:23
**最终状态**: built —— conan create 通过；静态库 + 生成头 + 许可证齐备；消费者测试 1/1 通过；上游无自动化测试（N_static=0，清点证据见上表）。
