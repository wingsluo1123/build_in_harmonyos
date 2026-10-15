# mympd 25.3.0 适配笔记

myMPD —— MPD（Music Player Daemon）的独立 Web 前端（C 实现）：Web UI 资源
内嵌二进制、HTTP/WebSocket JSON-RPC API、首启用 OpenSSL 生成自签 TLS 证书，
支持 Lua 脚本与歌词标签读取（MP3 经 libid3tag、FLAC 经 libFLAC）。上游
CMake 工程（C23，`build.sh` 辅助生成内嵌资源）。本仓首适配：官方 main 与
Conan 制品仓均无 mympd，版本保持 25.3.0（R37 双查不动）。

## 编译环境

- 构建系统: CMake（`cmake_layout`，默认 Unix Makefiles 生成器；上游 `build.sh`
  经解释器调用，patch 0003）
- 上游版本: 25.3.0（GPL-3.0-or-later；tag v25.3.0 archive tarball，
  sha256 `d21170635f5caf7650860bcab23560ec0691acd0102a89a281bbb72ab31a7d01`）
- 编译日期: 2026-10-11（真机 conan create 验证运行）
- 编译器: clang 15.0.4（aarch64-linux-ohos，真机 /data/service/hnp/bin/clang）
- 依赖: pcre2/10.48、openssl/3.5.8.1、utf8proc/2.11.3.2、libid3tag/0.16.3、
  flac/1.5.0、lua/5.4.8.1（均 transitive_headers/libs=True）；构建工具
  jq/1.7.1、perl/5.42.2.3、lua/5.4.8.1（luac）、pigz/2.8（派生 gzip）
- 验证: conan-verify Verdict PASS（2026-10-11T11:49:55）——实质 PASS 5 门
  （G0/G1/G2/G3/G4）+ N/A 跳过 3 门（L2/L4/L5 无 cache 路径，检查对象不存在，
  非实测通过）；G4「无法找到程序包 ID」计 PASS 的判定依据＝纯可执行包
  （无 lib/，G3 同证）下无包 ID 可解析、无系统同名库冲突面。G2 干净构建 +
  上游 ctest 35 条目全过（100%，Total Test time 9.32s）+ test_package 5/5。
- 构建期网络: 必需——`build()` 内全量 ctest 含真实网络用例（`test_http_client`
  经 gh-proxy.com 前缀镜像抓取字节同一文件，patch 0006），构建机需可访问外网
  （至少可达该镜像）；无外网时该用例失败、`conan create` 不通过（不设跳过
  开关，失败如实呈现）

## 产物

| 项 | 值 |
|---|---|
| 可执行 | `bin/mympd` 6,735,552 B（+ `bin/mympd-config`、`bin/mympd-script`）|
| 内嵌 | Web UI 资源（`build.sh createassets` 打包进二进制；jq/perl/luac + gzip 生成）+ 内嵌 libmpdclient 2.26.0（上游 not-found 回退选路）|
| 文档 | `share/man/man1/` 三枚 gzip 手册页（mympd.1.gz、mympd-config.1.gz、mympd-script.1.gz）+ `share/doc/mympd/` 五份 md 文档 + `licenses/LICENSE.md` |
| DT_NEEDED | 仅 `libc.so`（真机 readelf -d 实录；其余依赖与内嵌 libmpdclient 均静态并入）|

## 关键适配决策

### 1. E017：GitHub 源镜像列表（无补丁）

平台 E017 会把 GitHub URL 注入 `ghfast.top`（已死域）；守卫为「文中不含
ghfast.top 字样」。conandata 源为有序镜像列表：gh-proxy.com 前缀 →
ghproxy.net 前缀 → 官方 GitHub URL 末位兜底（R39），三路 sha256 一致。
真机实测源获取与 7 枚补丁应用成功（conan-create.log 实录：逐条 `Apply patch`
成功，L150-156；该日志未单列下载来源行）。

### 2. CMakeDeps 变量契约（无补丁）

上游按精确大小写消费依赖（`PCRE2_LIBRARIES`/`OPENSSL_VERSION`/`LUA_FOUND`/
`FLAC_FOUND` 等），CMakeDeps 默认 config 文件的变量前缀跟小写包名走 →
逐依赖设 `cmake_file_name`（上游精确大小写）+ `cmake_find_mode=module`，
openssl/lua 另加全大写附加前缀；生成的 Find 模块对 file_name 与每个前缀
输出 FOUND/VERSION/VERSION_STRING/INCLUDE_DIR(S)/LIBRARIES 完整契约，
`CMAKE_FIND_PACKAGE_PREFER_CONFIG` 两种取值下解析一致。

### 3. gzip 由 pigz 派生（无补丁）

`build.sh createassets` 硬性 `check_cmd gzip perl` 并以 `gzip -n -9` 打包
资源；注册表无 gzip 包。pigz 是 gzip 官方 drop-in（按 argv[0] 选择 gzip
兼容行为）但只有 `pigz` 命名产物 → `build()` 复制为 gzip 命名副本，
`generate()` 经 `Environment.save_script` 把派生目录前置进 conanbuild
聚合环境脚本（configure/build/ctest 全程可见）。

### 4. MATH_LIB 空缓存预填（无补丁，E376）

真机首轮 G2 实测：上游根 `CMakeLists.txt` `find_library(MATH_LIB m REQUIRED)`
报 `Could not find MATH_LIB using the following names: m`——musl 把数学符号
并入 libc、无独立 libm 可发现。配方把 `MATH_LIB` 预填为空串缓存变量
（CMake 对已设置的缓存变量跳过查找、不额外链接；E376
target-evidence-bound-empty-library-cache，同 ballerburg/blupimania 先例）。
说明：该 find_library 位于所有 find_package 之前（补丁树上 L101，Threads/
PCRE2/OpenSSL 在 L102-104），首轮真机在走到依赖解析前即止步于此处。

### 5. 硬化旗标探针 -Werror 语义对齐（无补丁）

上游用 `check_c_compiler_flag` 逐个探测 `C_OPTS` 硬化旗标（根 CMakeLists
L330-360 附近逐旗标 `unset(COMPILER_SUPPORTS_FLAG CACHE)` 后探测），加入
通过者；探针不携带 `-Werror` → x86 专用旗标 `-mshstk`、
`-fstack-clash-protection` 在 aarch64 clang-15 上探针通过，真实编译与上游
自身的 `-Werror` 合流后 `argument unused during compilation` 变致命。
真机二轮实测：configure 全过、构建推进到编译 `dist/libmpdclient` 时全部
.obj 报此错（make Error 2）。处方：OHOS 侧 `CMAKE_C_FLAGS` 携带
`-Werror=unused-command-line-argument`（仅该诊断组）→ 探针与真实编译语义
对齐，`-mshstk` 与 `-fstack-clash-protection` 两枚探针如实失败、被上游逻辑
自然排除（真机最小矩阵定性：两枚无注入时为警告级 "argument unused"、注入后
转错误）。真机 conan-create 日志探针失败共 4 枚：另两枚 `-fcf-protection=full`
（aarch64 target 硬错 "cannot be specified on this target"）与
`-ftrivial-auto-var-init=zero`（clang 15 需专门 opt-in 旗标才启用，否则硬错）
与注入无关、探针历来即如实排除。其余旗标不受影响（同族诊断先例 E580 draft
`-Qunused-arguments` 对冲；同效先例 liboprf `_patch_stack_clash` 剥旗标——
本方案零补丁达成同一结果）。

### 6. FORTIFY 包装 × -Wstatic-in-inline 抑制（无补丁）

上游在未开 sanitizer 时加 `-D_FORTIFY_SOURCE=2`；OHOS libc 的 FORTIFY
`memcpy` 是 static-inline 包装（`string.h` 的 `pass_object_size` 版本），
clang 的 `-Wstatic-in-inline` 在 `mpack.h` 的 C99 外链 `inline` 助手中触发
（"static function 'memcpy' is used in an inline function with external
linkage"），经上游 `-Werror` 变致命。真机三轮实测：configure 与全部依赖
find_package 通过、`dist/libmpdclient` 全量编译通过，死在 `dist/mpack/
mpack.c` 的 mpack.h 行 2695+ 全部命中。处方：OHOS 侧 `CMAKE_C_FLAGS` 加
`-Wno-static-in-inline`。真机最小探针矩阵实证：①无 FORTIFY 不触发、仅
`-D_FORTIFY_SOURCE=2` 存在时触发；②`-Wno-static-in-inline`（或
`-Wno-error=`）的抑制/降级态不被其后出现的通用 `-Werror` 覆写。
该诊断为 libc-fortify 头文件产物，非源码可修（同族先例：rpmalloc/1.4.5
自用旗标表含 `-Wno-static-in-inline`）。

### 7. 脚本经解释器调用（补丁 0003）

无 `binfmt_script` 的平台不能直接执行脚本文件；上游根 `CMakeLists.txt` 三处
`execute_process` 直接执行 `build.sh`（createassets / copyassets / 文档）→
configure 期 `find_program(MYMPD_SHELL_EXECUTABLE NAMES bash sh)` 定位解释器
后以 `<解释器> build.sh` 调用（未定位到则 FATAL_ERROR 显式报错；配方另优先
注入 `CONFIG_SHELL`/路径 bash，双保险）。他平台行为等价（有解释器时）。

### 8. 测试临时路径 TMPDIR 贯通（补丁 0001，测试侧）

OHOS `/tmp` 只读；上游套件把测试临时目录/工作目录写死 `/tmp/mympd-test`
（test/ 下 8 文件）→ 统一经新增 TMPDIR 感知助手 `test_tmpdir()`/
`test_tmpfile()` 构造（`TMPDIR` 未设置时回落上游路径，他平台行为等价）；
目录清理由 `system("rm -rf")` 改为进程内 `nftw()` 递归删除。配方 ctest
运行期将 `TMPDIR` 指到构建目录内（`_test_tmp`）。用例数量、校验点与判定
逻辑零改动。

同一补丁还修复测试辅助路径构造中的 sds 句柄重赋值缺陷：`sdscatfmt(sdsempty(),
...)` 增长后返回的新句柄被丢弃、旧句柄被复用释放——平台加固 jemalloc 将其
判为致命断言（SIGTRAP），真机套件运行期命中（首轮定案）。修复＝把返回值
重赋值回句柄变量；纯内存安全修复，零期望值改动。

### 9. 测试文件目录真实复制（补丁 0004，测试构建侧）

`test/CMakeLists.txt` 在 `unit_test` 构建前用 `cmake -E create_symlink` 把
`test/testfiles` 链接到构建目录；平台对 symlink 全盘 EPERM → 改为
`cmake -E rm -r -f` + `copy_directory` 真实复制（内容一致、无 symlink）。

### 10. 内嵌 libmpdclient 选路与安装面收敛（无补丁）

注册表无 ≥ 2.26.0（上游最低要求）→ 不设 `MYMPD_EMBEDDED_LIBMPDCLIENT`（保持
上游默认 OFF），`find_package(LIBMPDCLIENT)` 未命中后走上游自带 not-found
回退：该分支同时 `set` 变量 + `add_compile_definitions` 定义 C 宏，内嵌随
tarball 提供的 `dist/libmpdclient`（2.26.0）。⚠ 上游 `-DON` 直通分支只有
message、漏定义宏：CMake 侧已内嵌（src 目标挂 dist include、unit_test 链接
mpdclient、dist 子目录启用），C 侧却按共享模式 `#include <mpd/client.h>`
（上游假定系统头路径存在——正常 Linux 有 `/usr/include/mpd`）——真机四轮实测
`mympd` 主目标借自身 include 目录编译通过，`unit_test` 与
`cli_tools/mympd-script` 双双 fatal error（9 处），且版本行缺 `(embedded)`
标记。故以回退路径为准（`-v` 输出 `Libmpdclient 2.26.0 (embedded)` 为证）。
`MYMPD_STARTUP_SCRIPT=OFF`
（否则向 /usr/lib/systemd/system、/etc/init.d 等绝对系统路径装初始化脚本）；
`CMAKE_INSTALL_PREFIX` 钉到包目录（上游用绝对 `CMAKE_INSTALL_FULL_*` 目标并
在 configure 期把工作/缓存/文档根路径固化进二进制）；`MYMPD_DOC_HTML` 保持
上游默认 OFF（html 文档链需 sphinx venv 与网络，manpage 不受影响）。

### 11. getopt_long 哨兵缺失修复（补丁 0007，上游正确性）

`handle_options.c` 的 `long_options[]` 在 8 个条目后没有 getopt(3) 契约要求的
全零终止项。精确匹配（`--dump`/`-h` 等）与短选项在扫描早期即被服务、缺陷被
掩盖；未匹配长选项（`--foo`）与无歧义缩写（`--dum`）必须扫完数组做歧义
判定 → 越界读表外内存。真机实测：`--foo`、`--dum` 确定性 SIGSEGV（退出码
139；重定向文件里只有 shell 写的 "Signal 11" 行、进程零输出——崩溃发生在
错误消息打印之前），`--dump`/`-Z` 正常。修复＝补一行 `{NULL, 0, 0, 0}`；
对所有 libc 语义正确，无平台条件编译、非门控。test_package 反例用例同步
收紧为"优雅非零退出"（≥128 的信号退出不再计通过）。

### 12. OHOS 目录组权限语义与 umask 窗口（补丁 0008）

HarmonyOS PC 用户存储（FUSE 层）的目录语义（真机探针矩阵定案）：①其下一切
访问经**目录组权限位**判定——`umask(0077)` 下 `mkdir(0770)` 落为
`drwx--S---`(2700) 后，对**包括属主在内**的一切进程拒绝进入（EACCES）；
②事后 `chmod()` 被忽略不落盘（shell 的 chmod 与 python3 直调 `os.chmod`
均 no-op）；③创建时请求的 mode 被尊重（`umask≤0002` 或 `umask(0)` +
`mkdir(0770)` → `drwxrws--x`(2771) 组 rwx 完全可用，其内可建子目录与文件）。
`main.c` 的 `umask(0077)`（上游意图＝仅属主可读写）使全树目录创建唯一漏斗
`testdir()` 的 `mkdir(0770)` 落为 2700 → 引导自 `work/config` 起全线 EACCES
（run-2 G2 失败根因）。修复＝`testdir()` 内 `umask(0000)` 窗口包裹 mkdir
并即刻恢复（`MYMPD_OHOS` 门控，配方为 OHOS 构建注入该宏；窗口仅包裹创建
调用）。端到端实证：按 mympde 期望结构全树预建 0770 组目录后跑真二进制
`-c`，RC=0、目录树/证书/逐项配置全数生成、优雅退出。

## 上游测试（build() 内真实执行）

上游为单一 `unit_test` 二进制（`MYMPD_BUILD_TESTING=ON`），ctest 按测试
类别逐条执行（`unit_test --filter=<类别>.*`）：35 条 ctest 条目 = 33 个
基础类别 + lyrics_id3 + lyrics_flac（可选依赖启用时）；源码内 UTEST 宏计
201 例、分布在 34 个含用例套件；`m3u` 条目在上游 `test/` 内无对应用例
定义（运行 0 例、退出码 0，如实记录，非本配方裁剪）。

真机实测（conan create，JUnit 汇总经 `HMBS_UPSTREAM_TEST_RESULT`）：

- ctest: `100% tests passed, 0 tests failed out of 35`（`Total Test time (real) = 9.32 sec`）
- `HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "discovered": 35, "executed": 35, "passed": 35, "failed": 0, "skipped": 0}`
- 35 条目逐条 Passed（1/35 … 35/35 全绿）；`m3u` 条目运行 0 例、退出 0
  （上游自身空条目，如实记录）

## test_package（消费者视角）

| 用例 | 结果 | 覆盖 |
|---|---|---|
| 版本输出 | ✅ PASS（真机） | `-v` 输出 `myMPD 25.3.0` 与 `Libmpdclient 2.26.0 (embedded)`（内嵌库证明）|
| 帮助输出 | ✅ PASS（真机） | `-h` 正常输出用法（含 `Usage:`）|
| 默认配置 dump | ✅ PASS（真机） | `-d` 输出默认配置（含 `http_port: 8080`）|
| 引导配置与证书 | ✅ PASS（真机） | `-c -w <work> -a <cache>` 写出逐项配置文件与自签 TLS 证书（config/http_port、ssl/ca.pem、ssl/server.pem 非空）|
| 反例对照 | ✅ PASS（真机） | 未知选项必须优雅非零退出（信号崩溃/退出码 ≥128 不计通过）|

逐例 TEST PASS/FAIL + TEST SUMMARY，任一失败退出码非零。

## 补丁清单

| 补丁 | 内容 | 规模 |
|---|---|---|
| 0001 | 测试临时路径 TMPDIR 贯通 + `nftw()` 进程内清理 + sds 句柄重赋值修复（SIGTRAP 定案，测试侧语义等价）| 8 文件 +100/-32 |
| 0003 | `build.sh` 经解释器调用（find_program + 配方注入双保险）| 1 文件 +10/-3 |
| 0004 | `test/testfiles` 物化改真实复制（symlink EPERM）| 1 文件 +6/-1 |
| 0005 | 系统 CA 探测表追加 HarmonyOS 路径（/etc/ssl/certs/cacert.pem）| 1 文件 +1/-0 |
| 0006 | 网络测试改经 gh-proxy.com 前缀镜像（字节同一文件）| 1 文件 +3/-1 |
| 0007 | getopt_long 长选项表补全零终止哨兵（上游 UB 正确性修复，无门控）| 1 文件 +2/-1 |
| 0008 | testdir() umask(0000) 窗口保目录组权限（MYMPD_OHOS 门控，OHOS 专用）| 1 文件 +15/-1 |

七枚补丁中六枚为 platform_only（守卫见版本级 manifest
`patch_classification`）；0007 为上游正确性修复（bugfix，全平台语义正确）。
用例数量/校验点/判定逻辑零改动（0001 的 sds 重赋值修复为内存安全修复，
不改任何期望值）。

## 复现（真机 OHOS aarch64）

```sh
# 真机（HarmonyOS PC aarch64）
python3 scripts/ohc-run.py conan-verify mympd 25.3.0
# 结果：Verdict: PASS（2026-10-11T11:49:55.610233）
#   实质 PASS 5 门（G0/G1/G2/G3/G4）+ N/A 跳过 3 门（L2/L4/L5，无 cache 路径）
#   ctest 35/35；test_package 5/5
# 报告与日志随档 reports/conan-verify-report.md、reports/conan-create.log
```
