# asterisk-odbc 22.10.1 适配笔记

## 状态

- 分支: `feat/asterisk-odbc-22.10.1`
- issue: `TBD`。已在项目文件和本轮会话上下文中搜索 `asterisk-odbc`、`22.10.1`，未找到明确 issue 编号。
- 当前结论: 适配已收口到可交付状态：当前工作树的 OHOS recursive-mutex 初始化、`ld.lld` 入口选择、构建期 LLVM 运行库路径、menuselect ELF 签名和原子打包签名已完成真机 package build（recipe rrev `a744e096929b9b22842d211bdaa90fc1`、package revision `16c0f27d84febbcce59e43a387cdf1a7`）及正式 `conan test`；官方 shadow CI `#42701` 也已验证先前签名/链接器配方，issue 继续待补。

## W0 依赖检查

| 依赖 | 检查结果 | 说明 |
|---|---|---|
| `unixodbc/2.3.12` | 通过 | `conan list "unixodbc/2.3.12:*" -r=ohpcd` 可查到 recipe revision `6878d8258773e5a57d6526e9b29cc5b1`；OHOS armv8 Release shared 包 `01d92cf349a0dd98ff915f4bd99a04430171517f` 可下载，package revision `f1e49e3a9f40307c94ed94d5647d8b3d`。 |
| `libedit/20240808` | 通过 | `conan download -r=ohpcd --only-recipe` 可下载。 |
| `uuid/2.40.1` | 通过 | `conan download -r=ohpcd --only-recipe` 可下载。 |
| `jansson/2.15.1` | 通过 | `conan download -r=ohpcd --only-recipe` 可下载。 |
| `libxml2/2.15.3` | 通过 | 本机缓存已有 ohpcd recipe revision。 |
| `sqlite3/3.49.1` | 通过 | `conan download -r=ohpcd --only-recipe` 可下载。 |

依赖处理原则：`unixodbc` 是硬依赖，现已发布到 `ohpcd`，本 PR 继续只消费该依赖，不混入 `unixodbc` 适配。

## 源码与构建系统分析

- 上游源码: `https://github.com/asterisk/asterisk/archive/refs/tags/22.10.1.tar.gz`
- sha256: `373c98f4d4a1b923b42def0aee03f4e36aca9d1c244a8eeda646da8a97f89663`
- 构建系统: Autotools (`configure` + `make` + `menuselect`)
- ODBC 探测: `configure.ac` 中 `AST_EXT_LIB_CHECK([UNIXODBC], [odbc], [SQLConnect], [sql.h])`，并优先使用 UnixODBC；iODBC 仅作为 fallback，configure 还会提示建议切换到 unixODBC。
- 上游测试 inventory: `tests/` 目录的 Asterisk 内部单元测试共 `724` 条。它们通过完整 `asterisk` PBX 测试运行器加载核心和非 ODBC 模块；本配方按交付范围只构建 7 个 ODBC 模块，未构建该运行器，因此不将 `test_package` 误报为上游测试执行结果。
- 交付模块:
  - `res_odbc_transaction.so`
  - `res_odbc.so`
  - `res_config_odbc.so`
  - `func_odbc.so`
  - `cdr_odbc.so`
  - `cdr_adaptive_odbc.so`
  - `cel_odbc.so`
- 配置样例:
  - `res_odbc.conf.sample`
  - `res_config_odbc.conf.sample`
  - `func_odbc.conf.sample`
  - `cdr_odbc.conf.sample`
  - `cdr_adaptive_odbc.conf.sample`
  - `cel_odbc.conf.sample`

## 配方策略

1. 使用 Asterisk 22.10.1 源码做 in-source 构建，避免 Asterisk 构建系统对源码内相对路径的依赖被破坏。
2. 通过 `--with-unixodbc=<package_folder>` 显式启用 UnixODBC，关闭 `iodbc/pjproject/x11/gtk2`。
3. 复用 Asterisk 适配中已验证的轻量运行时修正：`TMPDIR`、`umask 077 -> 022`、禁用 clang BlocksRuntime 硬失败、menuselect 的 libxml2 include 注入；构建期生成的 menuselect ELF 在执行前完成 OHOS 签名并恢复执行位。
4. 只执行 ODBC 模块目标构建并只打包 ODBC `.so` 与 sample config，不安装完整 PBX。

## 本机验证结果

已完成：

- `git worktree` 独立分支创建，未切换主仓库 Apache Arrow 分支。
- 源码 tarball 下载与 sha256 校验通过。
- 上游 ODBC 模块与配置样例清单确认。
- `conanfile.py`、`conandata.yml`、`manifest.yaml`、`test_package` 已准备。
- `python -m py_compile conanfile.py test_package\conanfile.py test_package\test_asterisk_odbc.py` 通过。
- `conan inspect .` / `conan export .` 通过，远端 build 使用的 recipe revision 为 `1d63b276b5e883ef6d6fca286f7b44ca`。
- `conan list "unixodbc/2.3.12:*" -r=ohpcd` 通过，确认 `unixodbc/2.3.12` OHOS armv8 Release shared 二进制可达。
- `conan graph info .` 与 `conan install . --build=never` 在 OHOS profile 下通过，依赖可正常解析和下载。
- 远端 OHOS 主机 `conan create` 通过，package id 为 `74010f9f2b36ca0ffa1c38a1eee5383f6885ed38`，package revision 为 `2f7d2a2fb6cbd73cffd5e9dd9aee2a07`。
- 远端 OHOS 主机 `conan test` 通过，复核了 7 个模块 `.so` 与 6 个 sample config。
- `test_package/test_asterisk_odbc.py` 的直接 consumer probe 通过，确认 7 个模块 `.so` 和 6 个 sample config 都已打进包。
- `test_package` 的符号检查已从 `nm -D` 改为全符号表 `llvm-nm`，因为 OHOS 构建里这些 Asterisk module entrypoints 以 local symbol 形态出现，动态表检查会误报。
- 当前设备没有 `llvm-readelf/readelf`，但有 `llvm-readobj`、`llvm-objdump` 和 `llvm-nm`；consumer probe 从执行它的 Python 同目录定位 LLVM 工具，并以 `llvm-readobj --file-headers` 的 `Type: SharedObject` 校验 ELF DSO。真机 package build 完成后，最初自动 test 仅暴露这项工具发现假设；更新 probe 后，独立 `conan test` 复核 7 个 ODBC 模块与 6 个 sample config 通过。
- 上游 `724` 条内部测试以人工检视给出的库存为准。完整 Asterisk 测试运行树在当前设备配置中登记了 599 条；其中 3 条 `/DO_NOT_RUN/` 危险自测和 2 条刻意 PASS/FAIL 的框架自测不进入正常执行，剩余 594 条以 80 个无父类别的根类别在独立 Asterisk 进程中执行。结果为 559 PASS、26 FAIL、9 NOT RUN。按上游库存表示为 `559/724`（77.21%）：26 FAIL、14 SKIP（9 NOT RUN + 5 受保护框架自测）、125 未注册/未执行。`test execute category` 会匹配子类别，汇总只使用根类别，避免重复计入 DNS、astobj2 和 stasis 子树。package consumer probe 仍不计入上游分母。

### 官方 CI #36868 根因

官方 `#36868` 的依赖解析、质量门禁和 configure 均通过，失败点是顶层 `make menuselect.makeopts`：

```text
chmod 755 menuselect/menuselect
menuselect/menuselect --check-deps menuselect.makeopts
/data/service/hnp/bin/bash: line 1: menuselect/menuselect: Permission denied
make: *** [Makefile:379: menuselect.makeopts] Error 126
```

这个 `menuselect` 是递归 make 刚生成的 OHOS ELF。HMDFS 的执行策略要求 ELF 带有效 `.codesign`，`chmod 755` 只能恢复 mode 位，不能替代代码签名，因此官方旧提交即使 chmod 成功仍被内核拒绝。修复是在 `menuselect/menuselect` 生成后，用 `llvm-objcopy` 移除旧 `.codesign`，用 `binary-sign-tool sign -selfSign 1` 输出签名临时文件，恢复执行位后 `os.replace`，再执行顶层 `make menuselect.makeopts`。最终打包的 7 个模块也使用同一原子签名流程。

本次重跑日志确认签名工具输出 `add codesign section success` / `write code sign data success`，随后两次 `--check-deps`、7 个模块编译、7 个模块签名及 `conan test` 均成功。

### 官方 CI #37218 根因与本次修复

官方最新可见任务 `#37218` 基于旧提交 `a6ceb013`，在第一个 ODBC 模块链接时失败：

```text
BUILD_LDFLAGS="-fuse-ld=/data/service/hnp/bin/ld"
Error loading shared library libxml2.so.16: (needed by .../ohos/native/llvm/bin/lld)
Error relocating .../llvm/bin/lld: xmlNewNs: symbol not found
clang-15: error: unable to execute command: No such file or directory
```

根因不是源码或 `unixodbc` 缺失，而是 `/data/service/hnp/bin/ld` 在该 worker 上仍会间接调用 SDK `lld`；该 `lld` 的运行时库搜索路径没有覆盖匹配的 `libxml2.so.16`。仅检查 HNP `ld` 文件是否存在不能区分真实 GNU ld 与该别名/包装入口。

本次修复：

- 优先使用设备用户工具链中的 `ld.lld` 入口，避免将 generic `lld` 文件作为 clang 的绝对 `-fuse-ld` 参数。
- 在 Conan build scope 内动态加入 SDK LLVM `lib`、用户 `usr/local/lib` 和继承路径，再加入 Conan 依赖库目录；不修改 consumer 的运行环境。
- 保留 `-fuse-ld=lld` 作为没有绝对 `ld.lld` 时的回退。

2026-09-09 真机复跑确认：顶层 configure、menuselect configure、menuselect 链接与签名、两次 `--check-deps`、7 个 ODBC 模块链接/打包及 `conan test` 全部通过；日志中 `libxml2.so.16`、`xml* symbol not found`、generic driver 和 `C compiler cannot create executables` 均为 0 次。

### 官方 CI #42701 结果

基于最新提交 `a23d26ee` 触发的官方任务 `#42701` 已通过，Worker 为 `OpenHarmonyPCDeveloper-CI-011`，耗时 `707s`。官方机器人确认：

- `Conan test_package`: 通过
- `L0` 门禁（结构完整性）: 通过
- `L1` 门禁（测试执行验证）: 通过
- `conan-build-test`、`cleanup` 及其余流水线步骤: 全部通过

这次结果验证了此前 `#37218` 的失败确实来自旧提交中的链接器选择：新配方的 `ld.lld` 入口和构建期 LLVM 运行库路径修复已在官方 worker 生效。

待补事项：

- issue 编号: 仍是 `TBD`。

## 下一步命令

shadow CI / 本地批跑：

```sh
CI_PACKAGES="archives/a/asterisk-odbc/22.10.1" zsh ci/conan/build_and_test.sh
```

远端 OHOS 复跑：

```sh
ssh -T -p 56267 -i "%USERPROFILE%\\.ssh\\ohos_pc_codex_ed25519" currentUser@frp-tip.com "cd /storage/Users/currentUser/ohos-users/codex-asterisk-odbc/asterisk-odbc-22.10.1-20260831-105021 && ./run-build.sh"
```

经验点：

- Asterisk 的 ODBC module 在 OHOS 下能正常编出 `.so`，但模块入口符号不一定出现在动态符号表。
- `test_package` 更适合做“包内容与模块入口存在性”检查，而不是强依赖 `nm -D`。
- 官方 CI #36563 已确认 shell 修复生效；#37218 进一步确认 HNP `ld` 文件存在不能证明其实际为 GNU ld，不能以文件存在性选择链接器。
- 官方 CI #36644 已确认 C compiler link probe 通过，但同构建/主机 triplet 下的 conftest 无法运行；顶层和 menuselect configure 改用 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`，让 Autoconf 跳过目标程序执行检测。
- 官方 CI #36686 已确认交叉配置继续生效，但 Asterisk 顶层 `MAKE_MENUSELECT` 从生成的 `makeopts` 重新注入 `BUILD_CC=cc`、`BUILD_LDFLAGS=`；配方对递归 make 显式传入 OHOS `BUILD_CC` 和按环境选择的 `BUILD_LDFLAGS`，修复 menuselect 链接回退到 `cc`/SDK lld 的问题。
- 官方 CI #36765 已确认上述工具链修复生效，但 HMDFS 上重建的 `menuselect/menuselect` 在实际执行时出现错误 126；#36868 进一步证明仅在顶层规则前 `chmod 755` 仍无效，根因是 ELF 未签名。当前配方在递归 make 生成后完成签名，再进入 `menuselect.makeopts`。
- 官方 CI #36814 证明 lld-only 修复仍会使顶层 C compiler link probe 失败；当前链接器环境选择已消除该回归。
- 本次 HarmonyOS 真机复跑（2026-09-02 22:01-22:10）确认：lld fallback 使顶层和 menuselect configure 通过，menuselect 生成后完成 ELF 签名并成功完成两次 `--check-deps`，7 个 ODBC 模块和 6 个 sample 配置均通过 `conan create`/`conan test`；package revision 为 `2f7d2a2fb6cbd73cffd5e9dd9aee2a07`。
- 官方 `conan test` 现在已可直接复用同一包缓存，作为交接前的最终消费验证。
- 本次修复后的真机验证使用 `/storage/Users/currentUser/usr/local/bin/ld.lld`，Conan 包已登记到专用缓存，7 个模块和 6 个 sample config 的 consumer probe 通过。
---

**编译结束**: 2026-09-09 09:45
**最终状态**: built

## 上游测试逐例分析

### 口径与范围

以下记录来自 2026-09-10 在 HarmonyOS 真机上独立构建、运行的完整
Asterisk 测试树，不是本配方 `test_package` 的结果，也不代表七个 ODBC
模块与完整 PBX 模块图共同加载后的包级验证。上游库存为 724 条；该
runner 登记 599 条，去重后的正常结果为 559 PASS、26 FAIL、9 NOT RUN。
另有 3 条危险 `DO_NOT_RUN` 及 2 条刻意 PASS/FAIL 的框架自测受保护未运行，
以及 125 条未被此 runner 配置登记。按上游库存计为 `559/724`（77.21%）：
26 FAIL、14 SKIP（9 NOT RUN + 5 受保护自测）和 125 未登记/未执行。

原始分类记录有 620 次执行，因为父分类会匹配子分类；去掉 27 条重复 PASS
后为 559 PASS、25 FAIL、9 NOT RUN。另行显式执行的 WebSocket 用例补足第
26 个 FAIL。原始文件为设备目录
`/storage/Users/currentUser/ohos-users/codex-asterisk-odbc-upstream/asterisk-22.10.1-20260909-162000/artifacts/category-isolation-20260910.tsv`，
SHA-256 为
`671d2c1378a28246d16d43fb84c04d7c749cb454eb296e6c9aab60217a2b2889`。

分类含义：

- **Runner fixture**：补齐运行器配置、声音文件、可写临时目录或本地测试服务。
  此类修复不属于 `asterisk-odbc` 配方。
- **Full-PBX core/runtime**：需要独立的 Asterisk core/full-PBX HarmonyOS
  适配任务来修复或复测，不是 ODBC 包缺陷。
- **待最小复现**（本表已无此类）：第 7、16–19 条最初因 XML 未保留判定根因所需的
  实际输出而暂列此类；这 5 条现均已完成真机最小探针并给出确定原因，分类见对应行。

没有任何一条被判定为天然不可修复。即便不属于 ODBC 包范围，也应在对应的
测试运行器或 full-PBX 适配任务中闭环。

### 26 个 FAIL

| # | 上游用例 | 首个真机证据 | 归类与修复边界 |
|---:|---|---|---|
| 1 | `/apps/app_voicemail/` `test_voicemail_load_config` | XML 为 `NA`；分类控制台记录 `app_voicemail.c: actual_load_config: Failed to load configuration file`。runner 未部署 `voicemail.conf`。产物：`single-_apps_app_voicemail_-category-results.xml`。 | **Runner fixture。** 部署上游 voicemail 测试配置后重跑；不改 ODBC 模块。 |
| 2 | `/apps/app_voicemail/` `vmsayname_exec` | 播放分机问候音时失败；同一 runner 缺少 `voicemail.conf`，且部署的声音树没有 `beep.gsm`。产物同第 1 条。 | **Runner fixture。** 补齐 voicemail 配置与声音文件。 |
| 3 | `/config/` `config_options_test` | `Could not parse config`；用例声明的 `config_test.conf` 未在部署配置目录中。产物：`single-_config_-category-results.xml`。 | **Runner fixture。** 部署上游 `config_test.conf`。 |
| 4 | `/funcs/func_env/` `func_file` | `Cannot create temporary directory: Read-only file system`；源码对 `/tmp/test_func_file.XXXXXX` 调用 `mkdtemp`。产物：`single-_funcs_func_env_-category-results.xml`。 | **Runner fixture。** 重定向或挂载到 runner 的可写 `TMPDIR`，或在独立的测试移植 PR 修改上游测试。 |
| 5 | `/funcs/func_sayfiles/` `test_SAYFILES_function` | 所有 `SAYFILES()` 替换结果为空；full runner 禁用了 core/MOH/extra sounds，`beep.gsm` 不存在。产物：`single-_funcs_func_sayfiles_-category-results.xml`。 | **Runner fixture。** 安装该 full-PBX 用例所需声音文件。 |
| 6 | `/main/file/` `read_dir_test` | `Failed to create directory: /tmp/tmpdir.XXXXXX`。产物：`single-_main_file_-category-results.xml`。 | **Runner fixture。** 同第 4 条，提供可写临时目录。 |
| 7 | `/main/json/` `type_timeval` | 设备 `TZ=America/Chicago date --date=@1360251154` 可生成期望的 `2013-02-07T09:32:34.000000-0600`，但 Asterisk 内置加载器在 `main/stdtime/tzfile.h` 固定 `TZDIR=/usr/share/zoneinfo`，该目录不存在；`ast_tzset()` 加载失败后回退 GMT。原 XML 未保留生成值：`single-_main_json_-category-results.xml`。 | **Full-PBX core/runtime。** 可修复：让内置 TZ loader 使用 HarmonyOS 可用的时区数据，或在独立 full-PBX runner 中部署兼容 tzfile 数据；不属于 ODBC 包。 |
| 8 | `/main/json/` `dump_load_null` | 文件创建返回 `NULL`；源码使用 `/tmp/ast_json.XXXXXX`。产物：`single-_main_json_-category-results.xml`。 | **Runner fixture。** 为用例提供可写临时路径。 |
| 9 | `/main/json/` `dump_load_new_file` | 文件创建返回 `NULL`；源码使用 `/tmp/ast_json.XXXXXX`。产物同第 8 条。 | **Runner fixture。** 同第 8 条。 |
| 10 | `/main/json/` `dump_load_file` | 文件创建返回 `NULL`；源码使用 `/tmp/ast_json.XXXXXX`。产物同第 8 条。 | **Runner fixture。** 同第 8 条。 |
| 11 | `/main/media_cache/` `create_update_off_nominal` | `Failed to create first tmp file: /tmp/test-media-cache-XXXXXX`。产物：`single-_main_media_cache_-category-results.xml`。 | **Runner fixture。** 重定向该测试的硬编码临时路径。 |
| 12 | `/main/media_cache/` `create_update_metadata` | `Failed to create first tmp file: /tmp/test-media-cache-XXXXXX`。产物同第 11 条。 | **Runner fixture。** 同第 11 条。 |
| 13 | `/main/media_cache/` `create_update_nominal` | `Failed to create first tmp file: /tmp/test-media-cache-XXXXXX`。产物同第 11 条。 | **Runner fixture。** 同第 11 条。 |
| 14 | `/main/message/` `test_message_queue_both_nominal` | 等待 4 个预期 user event 超时，实际收到 0 个；runner 仅部署空 `[default]` dialplan，而用例需要专用 message dialplan。产物：`single-_main_message_-category-results.xml`。 | **Runner fixture。** 部署上游 message 测试 dialplan/config 后重跑。custom-handler-only 用例已通过，范围收敛到 dialplan event 路径。 |
| 15 | `/main/message/` `test_message_queue_dialplan_nominal` | 等待 4 个预期 user event 超时，实际收到 0 个。产物同第 14 条。 | **Runner fixture。** 同第 14 条。 |
| 16 | `/main/poll/` `poll_test` | 最小探针的三个 fd 为 `/dev/null` `POLLOUT`、`/dev/zero` `POLLIN`、空 pipe `POLLIN`；真机 `poll(0)` 只返回 `/dev/zero` 的 `POLLIN`。`ast_poll` 和 `ast_poll2` 在此构建中直接调用系统 `poll`/`ppoll`，与 XML 的返回 1 一致。产物：`single-_main_poll_-category-results.xml`。 | **Full-PBX test portability。** 可修复：将该 Linux 特化测试改为使用可写 pipe/socket，或由 HarmonyOS POSIX 层改变 `/dev/null` 的 poll 行为。不是 ODBC 或 Asterisk wrapper 缺陷。 |
| 17 | `/main/test_capture/` `test_capture_stdout_stderr` | runner 环境中 `/bin/sh` 的 stdout 为 `zzz`、stderr 为 `foobar`，字节完全符合断言。`ast_test_capture_command()` 对子进程 `waitpid(..., WNOHANG)` 成功后立即关闭 stdout/stderr pipe，未先 drain 已缓冲数据；快速退出会丢失输出。产物：`single-_main_test_capture_-category-results.xml`。 | **Full-PBX test framework。** 可修复：子进程退出后继续读取两个 pipe 直到 EOF，再关闭/完成 `open_memstream`。不改 ODBC 包。 |
| 18 | `/main/test_capture/` `test_capture_with_dynamic` | runner 的 GNU `date --date=@<epoch>` 返回成功；本地时间和格式与同一用例通过 `localtime()` 计算的契约一致。该用例与第 17 条共用同一提前关闭 pipe 的 `ast_test_capture_command()` 路径。产物同第 17 条。 | **Full-PBX test framework。** 可修复：同第 17 条 pipe-drain 修复；不是 `date` 参数兼容性或 ODBC 问题。 |
| 19 | `/main/test_capture/` `test_capture_with_stdin` | runner 的 `base64` 对 `Mary had a little lamb.` 输出 `TWFyeSBoYWQgYSBsaXR0bGUgbGFtYi4=\\n`，与断言逐字节相同。失败同样发生在共用的 capture helper 读取前关闭 pipe。产物同第 17 条。 | **Full-PBX test framework。** 可修复：同第 17 条 pipe-drain 修复；不是 `base64` 或 ODBC 问题。 |
| 20 | `/main/voicemail_api/` `nominal_msg_playback` | 建立元数据后 nominal playback 失败；源码注明缺少真实声音文件时 voicemail 操作可静默失败，runner 同时缺 `beep.gsm` 和 `app_voicemail` 配置。产物：`single-_main_voicemail_api_-category-results.xml`。 | **Runner fixture。** 安装 voicemail 配置和 core sound 后重跑该组。 |
| 21 | `/main/voicemail_api/` `nominal_forward` | 在测试邮箱间转发消息失败。产物同第 20 条。 | **Runner fixture。** 同第 20 条。 |
| 22 | `/main/voicemail_api/` `nominal_remove` | 删除测试邮箱消息失败。产物同第 20 条。 | **Runner fixture。** 同第 20 条。 |
| 23 | `/main/voicemail_api/` `nominal_move` | 将消息从 `INBOX` 移到 `Family` 失败。产物同第 20 条。 | **Runner fixture。** 同第 20 条。 |
| 24 | `/main/voicemail_api/` `nominal_snapshot` | 建立后期望 1 条消息，实际为 0。产物同第 20 条。 | **Runner fixture。** 同第 20 条。 |
| 25 | `/res/websocket/` `websocket_client_multiple_protocols` | 无法连接 `ws://127.0.0.1:8088/ws`；分类控制台显示 `chan_websocket.so` 因 `ast_websocket_client_retrieve_by_id` 未解析而加载失败。产物：`single-_res_websocket_-category-results.xml`。 | **Full-PBX core/runtime。** 在独立 Asterisk core 任务修复 full runner 的模块依赖/链接图并提供本地 echo endpoint。 |
| 26 | `/res/websocket/` `websocket_client_create_and_connect`（显式单独执行） | 无法创建到同一 `/ws` endpoint 的 client。产物：`single-_res_websocket_-websocket_client_create_and_connect-results.xml`。 | **Full-PBX core/runtime。** 同第 25 条；这是分类 TSV 外、单独执行补足的第 26 个 FAIL。 |

### 9 个 NOT RUN

这些是跳过而非失败。runner 仅记录 `NOT RUN`，没有保存跳过原因；因此下列每一项
在独立 full-PBX 测试适配开始前均须先检查模块和配置前置条件，不能将它们写成
已解释的 ODBC 或系统缺陷：

| # | 分类 | 用例 | 当前可证实的状态与后续动作 |
|---:|---|---|---|
| 1 | `/main/sorcery/` | `configuration_file_wizard_retrieve_multiple_all` | **NOT RUN。** 无详细 skip 日志；检查 sorcery configuration-file wizard 的模块和配置前置条件。 |
| 2 | `/main/sorcery/` | `configuration_file_wizard_retrieve_multiple` | **NOT RUN。** 无详细 skip 日志；同第 1 条。 |
| 3 | `/main/sorcery/` | `configuration_file_wizard_retrieve_field` | **NOT RUN。** 无详细 skip 日志；同第 1 条。 |
| 4 | `/main/sorcery/` | `configuration_file_wizard_with_criteria` | **NOT RUN。** 无详细 skip 日志；同第 1 条。 |
| 5 | `/main/sorcery/` | `configuration_file_wizard_with_file_integrity` | **NOT RUN。** 无详细 skip 日志；同第 1 条。 |
| 6 | `/main/sorcery/` | `configuration_file_wizard` | **NOT RUN。** 无详细 skip 日志；同第 1 条。 |
| 7 | `/main/sorcery/` | `caching_wizard_behavior` | **NOT RUN。** 无详细 skip 日志；检查 caching wizard 的模块、配置及本地缓存目录。 |
| 8 | `/main/sorcery/` | `apply_config` | **NOT RUN。** 无详细 skip 日志；检查 sorcery 配置应用路径和注册模块。 |
| 9 | `/main/stdtime/` | `timezone_watch` | **NOT RUN。** 无详细 skip 日志；结合第 7 条已确认的 tzfile 路径问题，先修复时区数据发现后再检查 watcher 前置条件。 |

受保护的 5 个框架条目（3 个危险 `DO_NOT_RUN`，2 个刻意 PASS/FAIL 自测）维持
不运行，不应混入失败统计。

### 结论与后续动作

19 个 FAIL 已由缺失的 test-runner fixture 解释，2 个属于 full-PBX WebSocket
模块图，4 个是已取证的 full-PBX/runtime 或测试移植问题，另 1 个是
HarmonyOS `/dev/null` 的 `poll` 语义与 Linux 特化测试不一致。所有 FAIL 均已逐例
给出原因、修复边界和可行动作；没有一条将问题指向 `asterisk-odbc` 包。已安装包
consumer probe 已验证 7 个模块和 6 个 sample 配置。

后续 full-PBX 调查必须另起 issue、分支和 PR，先补齐 runner 专用 fixture
（`TMPDIR` 映射、配置、声音、message dialplan），再处理本文已确认的时区、pipe
drain 和 poll 测试移植动作，并检查 9 项 `NOT RUN` 的前置条件。本
`asterisk-odbc` PR 不应合并该 runner 变更。
