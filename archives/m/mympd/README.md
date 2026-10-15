# myMPD

myMPD — MPD 音乐播放器的独立 Web 前端（内嵌 Web UI、HTTP/WebSocket
JSON-RPC API、首启自签 TLS 证书），适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

myMPD 是一个独立运行的 Web 服务器，作为 MPD（Music Player Daemon）的前端：
Web UI 资源内嵌在二进制中，通过 HTTP/WebSocket 提供 JSON-RPC API 与网页界面，
首次启动时用 OpenSSL 生成自签 TLS 证书，支持 Lua 脚本扩展与歌词标签读取
（MP3 经 libid3tag、FLAC 经 libFLAC，UTF-8 规范化经 utf8proc）。

- 上游项目：myMPD 25.3.0（GPL-3.0-or-later，https://github.com/jcorporation/myMPD）
- 产物：`bin/mympd`（独立服务器，`-v` 版本 / `-h` 帮助 / `-d` 打印默认配置 /
  `-c` 引导写出配置目录树与自签证书 / `-w` 工作目录 / `-a` 缓存目录）
- 上游测试：单一 `unit_test` 二进制（`MYMPD_BUILD_TESTING=ON`），ctest 按测试
  类别逐条执行（35 条目：33 个基础类别 + lyrics_id3 + lyrics_flac）

## OpenHarmony Scope

配方构建完整 myMPD（CMake，内嵌 Web UI 资源 + 内嵌 libmpdclient 2.26.0），
集成上游单元测试套件（构建 `unit_test` 并在 `build()` 内全量实跑）、
test_package 消费者 E2E。共 7 枚补丁（逐条见下「OHOS 适配要点」与版本级
`manifest.yaml` 的 `patch_classification`；编号 0002 未使用）：测试临时路径
TMPDIR 贯通（0001）、build.sh 经解释器调用（0003）、测试文件目录真实复制
替代 symlink（0004）、系统 CA 探测表追加 HarmonyOS 路径（0005）、网络测试
改经镜像前缀（0006）、getopt_long 长选项哨兵补全（0007，上游缺陷修复）、
目录组权限 umask 窗口（0008，MYMPD_OHOS 门控）。上游测试用例零增删零改动
（测试侧补丁仅改临时路径构造/清理方式并含 0001 的 sds 内存安全修复，无期望值
改动）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| pcre2 | 10.48 | 上游必需：HTTP 层与搜索的正则引擎 |
| openssl | 3.5.8.1 | 上游必需：TLS 服务面与自签证书（上游编译期检查 OPENSSL_VERSION ≥ 1.1.0） |
| utf8proc | 2.11.3.2 | 可选（默认开）：UTF-8 规范化 |
| libid3tag | 0.16.3 | 可选（默认开）：MP3 歌词标签（经注册表配方传递 zlib） |
| flac | 1.5.0 | 可选（默认开）：FLAC 歌词标签（经注册表配方传递 libogg） |
| lua | 5.4.8.1 | 可选（默认开）：脚本层（Lua ≥ 5.4.0，上游编译期检查） |

构建工具（tool_requires）：jq 1.7.1、perl 5.42.2.3、lua 5.4.8.1（luac）、
pigz 2.8（派生 gzip，见适配要点 2）。

libmpdclient 不入依赖：注册表无 ≥ 2.26.0（上游最低要求）的版本。配方保持
`MYMPD_EMBEDDED_LIBMPDCLIENT` 上游默认（OFF），由 `find_package` 未命中走上游
自带 not-found 回退——该分支同时选中内嵌 `dist/libmpdclient`（2.26.0）并定义
同名 C 宏（`-v` 输出带 `Libmpdclient 2.26.0 (embedded)` 为证；直通 `-DON`
分支上游漏定义宏，勿用）。

## OHOS 适配要点

1. **find_package 变量契约（生成侧，零补丁）**: 上游按精确大小写消费依赖
   （`PCRE2_LIBRARIES` / `OPENSSL_VERSION` / `UTF8PROC_FOUND` / `LIBID3TAG_FOUND` /
   `FLAC_FOUND` / `LUA_FOUND` / `LUA_VERSION_STRING`，含 `PCRE2_INCLUDE_DIRS`
   `OPENSSL_INCLUDE_DIR` 等单复数混用），而 CMakeDeps 默认 config 文件的变量
   前缀跟小写包名走。配方按上游 `find_package` 的精确大小写逐依赖设置
   `cmake_file_name` 并切换 `cmake_find_mode=module`（openssl、lua 另加全大写
   前缀，因其检查 `OPENSSL_VERSION` / `LUA_FOUND`）；生成的 Find 模块对
   file_name 与每个前缀输出 FOUND / VERSION / VERSION_STRING / INCLUDE_DIR(S) /
   LIBRARIES 完整契约，`CMAKE_FIND_PACKAGE_PREFER_CONFIG` 两种取值下解析一致，
   组件与传递目标（flac→libogg、libid3tag→zlib）不受影响。
2. **gzip 由 pigz 派生（构建侧，零补丁）**: `build.sh` 在 configure 期执行
   `createassets`（内嵌 Web UI 资源），硬性 `check_cmd gzip perl` 并以
   `gzip -n -9` 打包资源。注册表无 gzip 包；pigz 是 gzip 官方 drop-in
   （按 argv[0] 选择 gzip 兼容行为）但只提供 `pigz` 命名产物 → 配方在
   `build()` 中把 pigz 二进制复制为 gzip 命名、`generate()` 把该目录前置到
   构建环境 PATH（注册进 conanbuild 环境脚本，configure/build/ctest 全程可见）。
3. **MATH_LIB 空缓存预填（生成侧，零补丁）**: 上游根 `CMakeLists.txt` 以
   `find_library(MATH_LIB m REQUIRED)` 探测 libm；musl 把数学符号并入 libc、
   无独立 libm 可发现 → 查找失败、configure 报错（真机首轮实测即此处失败）。
   配方把 `MATH_LIB` 预填为空串缓存变量：CMake 对已设置的缓存变量跳过查找、
   不额外链接（E376 口径，同类先例 ballerburg/blupimania）。
4. **硬化旗标探针 -Werror 语义对齐（生成侧，零补丁）**: 上游逐个
   `check_c_compiler_flag` 探测硬化旗标并加入通过者，探针不带 `-Werror`；
   x86 专用旗标 `-mshstk`、`-fstack-clash-protection` 在 aarch64 clang-15
   上探针仅告警（"argument unused during compilation"）而通过，真实编译与
   上游自身 `-Werror` 合流后变致命（真机二轮实测死在 `dist/libmpdclient`
   编译）。OHOS 侧令 `CMAKE_C_FLAGS` 携带
   `-Werror=unused-command-line-argument`（仅该诊断组）：探针与真实语义
   对齐 → 上述两枚探针如实失败被排除。真机探针矩阵定性（clang 15.0.4
   aarch64-ohos；conan-create 日志探针失败共 4 枚）：`-fcf-protection=full`
   与 `-ftrivial-auto-var-init=zero` 另两枚为探针本就硬错者（前者报
   "cannot be specified on this target"、后者需 clang 专门 opt-in 旗标才
   启用），与注入无关、历来即被上游探针如实排除；其余旗标不受影响。
5. **FORTIFY 包装 × `-Wstatic-in-inline` 抑制（生成侧，零补丁）**: 上游在
   未开 sanitizer 时加 `-D_FORTIFY_SOURCE=2`；OHOS libc 的 FORTIFY `memcpy`
   为 static-inline 包装（`string.h` 的 `pass_object_size` 版本），clang 的
   `-Wstatic-in-inline` 在 `mpack.h` 的 C99 外链 `inline` 助手中触发，
   经上游 `-Werror` 变致命（真机三轮实测死在 `dist/mpack/mpack.c`）。
   该诊断为 libc-fortify 头文件产物、非源码可修；OHOS 侧加
   `-Wno-static-in-inline`（真机探针矩阵实证：仅 `-D_FORTIFY_SOURCE=2`
   存在时触发；`-Wno-` 的忽略态不被其后通用 `-Werror` 覆写）。
6. **测试临时路径 TMPDIR 贯通（patch 0001，测试侧）**: OHOS `/tmp` 只读挂载。
   上游套件把测试临时目录/工作目录写死在 `/tmp/mympd-test`（`test/` 下
   8 个文件）→ 统一经新增的 TMPDIR 感知助手构造（`TMPDIR` 未设置时回落上游
   `/tmp/mympd-test`，他平台行为等价）；目录清理由 `system("rm -rf")` 改为
   进程内 `nftw()` 递归删除（同一原因：目标目录运行期可写但 shell 工具链
   不可靠）。配方 ctest 运行时将 TMPDIR 指到构建目录内。
7. **build.sh 经解释器调用（patch 0003，构建侧）**: 无 `binfmt_script` 的平台
   不能直接执行脚本文件，而上游在根 `CMakeLists.txt` 三处经 `execute_process`
   直接执行 `build.sh`（createassets / copyassets / 文档）。补丁在 configure
   期 `find_program` 定位 bash/sh 解释器并改为 `<解释器> build.sh ...` 调用
   （配方另优先注入 CONFIG_SHELL / 环境 bash 路径）；他平台行为等价。
8. **测试文件目录真实复制（patch 0004，测试侧）**: `test/CMakeLists.txt` 在
   `unit_test` 构建前用 `cmake -E create_symlink` 把 `test/testfiles` 链接到
   构建目录；平台对 symlink 全盘 EPERM → 改为 `cmake -E rm -r -f` +
   `copy_directory` 真实复制（内容一致，无 symlink）。
9. **内嵌 libmpdclient 选路（生成侧，零补丁）**: 见「依赖」。libmpdclient 源码随
   上游 tarball 提供（`dist/libmpdclient`），无需网络、无需额外依赖。选路走上游
   not-found 回退而非 `-DON` 直通：直通分支上游漏 `add_compile_definitions`，
   CMake 侧内嵌而 C 侧按共享模式编译——`unit_test` 与 `cli_tools/mympd-script`
   会因找不到 `<mpd/client.h>` 编译失败（真机四轮实测），版本行也缺
   `(embedded)` 标记。
10. **安装面收敛**: `MYMPD_STARTUP_SCRIPT=OFF`（否则上游向
   `/usr/lib/systemd/system`、`/etc/init.d`、`/usr/local/etc/rc.d` 等绝对系统
   路径安装初始化脚本，落在包外）；`CMAKE_INSTALL_PREFIX` 钉到包目录（上游用
   绝对 `CMAKE_INSTALL_FULL_*` 目标并在 configure 期把工作/缓存/文档根路径
   固化进二进制）；`MYMPD_DOC_HTML` 保持上游默认 OFF（html 文档链需
   sphinx/sphinx-lint 的 venv 与网络，manpage 安装不受影响）。
11. **构建**: CMake（`cmake_layout`，默认 Unix Makefiles 生成器），
    `MYMPD_BUILD_TESTING=ON` 构建 `unit_test`；`build()` 内跑完整 ctest 套件
    并用 JUnit 汇总出 `HMBS_UPSTREAM_TEST_RESULT` 结构化标注。

## 上游测试

**构建期网络前置**：`build()` 内全量 ctest 含真实网络用例（`test_http_client`
经 gh-proxy.com 前缀镜像抓取字节同一文件，patch 0006），构建机需可访问外网
（至少可达该镜像）；无外网时该用例失败、`conan create` 不通过（不设跳过
开关，失败如实呈现，无静默豁免）。

上游套件为单一 `unit_test` 二进制，ctest 逐类别执行
（`unit_test --filter=<类别>.*`）：

| 数量 | 说明 |
|------|------|
| 35 个 ctest 条目 | 33 个基础类别 + lyrics_id3 + lyrics_flac（可选依赖启用时） |
| 201 个 UTEST 用例 | 分布在 34 个套件（源码内 UTEST 宏计数） |
| 1 个空条目 | `m3u` 条目在上游 `test/` 内无对应用例定义（运行 0 个用例、退出码 0，如实记录） |

上游测试用例零增删零改动（测试侧补丁仅涉及临时路径构造与清理方式，另含
0001 的 sds 句柄重赋值内存安全修复——均不涉用例增删与期望值改动）。

本版本实测：见版本级 `notes.md`。

### 包内测试（test_package）

| 用例 | 类型 | 说明 |
|------|------|------|
| 版本输出 | 消费者契约 | `-v` 输出 `myMPD 25.3.0` 与 `Libmpdclient 2.26.0 (embedded)`（内嵌库证明） |
| 帮助输出 | 消费者契约 | `-h` 正常输出用法（含 `Usage:`） |
| 默认配置 dump | 消费者契约 | `-d` 输出默认配置（含 `http_port: 8080`） |
| 引导配置与证书 | E2E | `-c -w <work> -a <cache>` 写出逐项配置文件与自签 TLS 证书（config/http_port、ssl/ca.pem、ssl/server.pem 非空） |
| 反例对照 | 消费者契约 | 未知选项必须以非零退出 |

逐例 TEST PASS/FAIL + TEST SUMMARY，任一失败退出码非零。

本版本实测：见版本级 `notes.md`。

## 使用

```bash
conan install --requires=mympd/25.3.0 -pr:h=<ohos-aarch64 profile>
```

```bash
# 版本
mympd -v
# 查看默认配置
mympd -d
# 初始化工作目录（写配置 + 自签证书）
mympd -c -w /data/.../work -a /data/.../cache
# 运行（配置就绪后前台启动）
mympd -w /data/.../work -a /data/.../cache
```

## 参考

- [官方文档](https://jcorporation.github.io/myMPD/)
- [源码仓库](https://github.com/jcorporation/myMPD)
