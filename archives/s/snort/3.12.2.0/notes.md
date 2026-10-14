# snort 3.12.2.0 适配笔记（OHOS / 鸿蒙 PC，aarch64）

## 方案概述

- 上游构建系统: CMake（`configure_cmake.sh` 包装器 → 直接驱动 CMake，本配方等价传递全部 `-D` 缓存项）
- 版本: 3.12.2.0（官方 Git tag 归档 `snort3-3.12.2.0.tar.gz`, sha256 `43000d6b...720b`）
- 额外内置源码: libdaq 3.0.27（无发行 tarball、Conan 源无包 → 第二源码 + autoreconf 自举,
  sha256 `03fac3da...601c`）
- 关键选项: `ENABLE_UNIT_TESTS=ON`（Catch2 内嵌进 snort 二进制 + CppUTest 经 CTest）；
  文档构建 `MAKE_HTML/PDF/TEXT_DOC=OFF`

## 依赖（全部取 ohpcd Conan 源已发布制品）

| 依赖 | 版本 | 角色 |
|---|---|---|
| libpcap | 1.10.6 | 抓包（含 libdaq 模块检测） |
| pcre2 | 10.45 | 正则 |
| hwloc | 2.14.0 | 线程亲和（共享库，运行期经 conanrun LD_LIBRARY_PATH） |
| libdnet | 1.12 | 网络地址 |
| openssl | 3.5.6.1 | 哈希/TLS |
| zlib | 1.3.1.1 | 规则压缩 |
| luajit-openresty | 2.1-20260311.1 | Lua 配置/规则引擎（静态） |
| cpputest | 4.0_r2 | 单元测试 executable |
| flex | 2.6.4.2 | FlexLexer（tool_requires） |
| pkgconf | 3.0.5 | FindDAQ/FindHWLOC/CppUTest（tool_requires） |
| autoconf/automake/libtool | 2.72/1.18/2.5.4.1 | libdaq 自举（automake/libtool 为 tool_requires；autoconf/autoheader 取自宿主 hnp 原生二进制，非 tool_require） |

## 适配要点（与通用坑位）

1. **libdaq 内置**: `autoreconf -ivf`（tool_requires 供 automake/libtool；`--build=aarch64-unknown-linux-ohos`
   绕过 config.guess 不识别 OHOS，zbar E007 同款）→ configure `--disable-shared --enable-static`
   `--with-libpcap-includes/-libraries` → `make --jobserver-style=pipe -j{N} ACLOCAL=true AUTOMAKE=true AUTOHEADER=true`（默认 8，初始迭代曾用 -j1）→ `make install`。
   - **--disable-shared 的原因**: OHOS 文件系统不支持符号链接（libtool 装 .so 依赖 symlink 链）。
   - **静态模块 .pc 补装**: 上游 `pkgconfig_DATA += libdaq_static_*.pc` 仅在 `BUILD_SHARED_MODULES` 下安装，
     但 snort `FindDAQ.cmake` 靠 `pkg-config --list-all | libdaq_static_*` 发现静态模块 →
     make install 后把 build 树生成的全部 `modules/*/libdaq_static_*.pc` 拷进 `prefix/lib/pkgconfig`。
2. **依赖定位**: snort 的 Find* 全部支持 `*_HINT` 变量 → 用 `-DPCAP_INCLUDE_DIR_HINT` 等逐项传
   `dep.package_folder` 下真实路径；`PKG_CONFIG_PATH` 含内置 libdaq + 全部宿主依赖 pc 目录
   （hwloc 无 HINT 变量，必须经 pkg-config 找到；FindDAQ 静态模块发现同理）；`CMAKE_PREFIX_PATH = 所有依赖包目录`。
   - 注意制品内 .pc 含构建机绝对路径（cpputest/libpcap/pcre2/hwloc 的 prefix 是 CI 缓存构建目录）——
     所以 HINT/CMAKE_PREFIX_PATH 是必需的，不能只依赖 pc 内容。
3. **TMPDIR**: OHOS `/tmp` 只读 → 全部构建步骤 `TMPDIR=<build>/tmp`。
4. **umask**: autoreconf 生成的 configure 可能带 `umask 077`（E011）；本包真机构建未复现该问题，配方未含处置步骤（如复现，按 E011 以 `sed` 修正）。
5. **单元测试**: `ENABLE_UNIT_TESTS=ON` 使 `#ifdef UNIT_TEST` 代码编译进二进制；
   `snort --catch-test all` 可直接从发行包跑 Catch2 套件；`make check` 目标经 `add_dependencies(check ...)`
   先构建全部 CppUTest 可执行文件再跑 ctest。
6. **rpath/RUNPATH（patch 0003 + 配方固定系统名）**: 设备 CMake 4.1.2 把宿主系统自检为
   HarmonyOS（`uname`），而平台模块只随 OHOS 名提供（`Platform/OHOS.cmake` = `include(Platform/Linux)`）
   → HarmonyOS 名下 rpath 系列平台标志变量全为空串（Generic 默认），CMake 静默丢弃全部
   -rpath/-rpath-link 标志（与 CMAKE_SKIP_RPATH / CMAKE_INSTALL_RPATH 取值无关）；
   配方经 `tc.variables["CMAKE_SYSTEM_NAME"]="OHOS"` 固定后标志齐全（微型工程 A/B 探针实证：RUNPATH 齐备且运行成功）；
   另 patch 0003 为上游 `cmake/platforms.cmake` 无条件 `set(CMAKE_SKIP_RPATH ON)` 加 HarmonyOS/OHOS 守卫
   （否则安装树 bin/snort 无 RUNPATH，空环境冒烟加载外部依赖 libhwloc 失败）。
7. **代码签名（.codesign）**: OHOS 工具链链接期为每个 ELF 写 `.codesign` 段，任何后链接改写即失效 →
   CMake 安装期 rpath 重写（"Set non-toolchain portion of runtime path"）使安装树二进制 execve EPERM
   （rc 126，Operation not permitted；DRAFT-E703 strip 失效同类）→ 配方设 `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`
   让**链接期即携带最终安装 rpath**，安装退化为逐字节拷贝（md5 一致），签名有效；真机实证安装树原位
   与 `env -i` 均可运行。副作用：build 树二进制同样带安装 rpath（对验证无害）。
8. **默认 ALL 目标不可省略**: 上游 install 规则引用的部分构件只由 ALL 产出（`api_def` 归档、
   `daqs/daq_*.so`、tools 四件、生成头 `api_options.h`/`snort_api.h`）——只定向 build snort+check 时
   `cmake --install` 逐个 "file INSTALL cannot find" 失败；构建链 = snort → check → `all`。
9. **RPC program number database 缺失（知识草稿）**: OHOS musl 系 libc 无 `<rpc/netdb.h>` 头、
   无 `getrpcent` 符号、无 `/etc/rpc` 数据文件 → 上游 CMake 探测两路皆否时 `SEND_ERROR`
   （libtirpc/1.3.7 制品仓可得，本适配不引入以控制依赖面）；
   HarmonyOS/OHOS 平台分支改发 `-DSNORT_NO_RPC_DB`（STATUS 消息记录降级），`service_rpc.cc`
   枚举编译排除、保留静态端口模式；详见 `knowledge/drafts/DRAFT-snort-3.12.2.0-ohos-no-rpc-program-db-configure-gate-static-fallback.md`。
10. **测试侧平台适配（patch 0002 / patch 0004，测试用例零增删零改动）**:
   ① OHOS 裸 `tmpfile()` 恒失败（硬编码 /tmp，只读 FS → NULL/EACCES），perf_monitor 的
   **csv/json/text 三个 formatter 测试**在失败时回退 `$TMPDIR` 下 mkstemp（创建即 unlink，
   语义等价）；其中 text 测试未兜底时把 NULL 直接交给 `FILE*` → 内嵌 Catch2 套件 SIGSEGV
   （真机复现）。② HarmonyOS 的 `SnortClock`（= high_resolution_clock）粒度粗：背靠背读取
   ~70% 同值（50 万次探针零增量 334845–370666），而 `rule_profiler.cc` 与
   `time_profiler.cc` **各自**的 `avoid_optimization()` 空循环会被优化消除 → 窗口内可
   零 tick：「rule profiler time context」`elapsed > 0` 竞态（8/8 过滤运行失败）、
   「time context exclude」`elapsed < hr_duration::max()` 竞态（热身 #6 实测：排除窗口
   0 tick 时哨兵 max 不减）→ patch 0004 对**两处助手**做有界等待跨一个 tick
   （生产代码不受影响）。

## 真机验证（2026-10-04，OHOS aarch64 设备）

- conan create（profile ohos-aarch64）: 干净全构建 rc=0，约 22m（本配方修订
  RREV `c50134101ffc3772c2da73749ee08219`，官方 verify G2 复用后仅重跑 test_package）；
  构建链 snort → check → all（补齐安装面），安装期 rpath 重写行计数 0
  （签名保持有效，安装树 bin/snort 与 build 树 md5 一致；原位与 `env -i` 均可运行、
  携带预期 RUNPATH）
- 八门禁（官方 conan-verify）: **Verdict PASS**（G0–G4 全 PASS），报告
  `reports/conan-verify-report.md`（其引用的 `conan-create.log` 为构建机产物、因
  `.gitignore` 的 `reports/` 规则不随仓——全仓 278 份 verify-report 中 207 份同形态）；
  G2 内 test_package 对打包后二进制重跑 6 用例全过
  （G4 行 "无法找到程序包 ID" 与 L2/L4/L5 "跳过（无 cache 路径）" 为 verifier G4
  解析器与 Conan 2 `conan list` JSON 结构的既有差异——设备存量报告普遍形态，非本包
  产物问题；空环境冒烟意图由 test_package `env="conanrun"` 与安装树 `env -i` 实证独立覆盖）
- CTest（可执行测试级）: **100% tests passed, 0 tests failed out of 158**（零跳过）
- 内嵌 Catch2（`snort --catch-test all`）: **All tests passed (3393 assertions in 378 test cases)**
- test_package E2E（6 用例）: **TEST SUMMARY: 6 passed, 0 failed**
  （version_output / help_output / config_validate / detect_icmp_positive / detect_negative_control /
  catch2_embedded_suite）

## 源码来源（R39/PF7 官方托管例外登记）

- `conandata.yml` 与版本级 `manifest.yaml` 的 source `url` 为有序镜像列表：镜像前缀
  （`gh-proxy.com` / `ghproxy.net`，GitHub 字节透明代理、sha256 与官方一致）优先，
  官方 GitHub URL 保留末位兜底；未使用第三方搬运源。
- 例外依据（实测）：CI 构建机出网无 GitHub 直连——连续三次真实构建（#79295 / #79331 /
  #79472 @CI-037）`source()` 下载 libdaq 全部 `ConnectTimeoutError`；改列表后构建
  #79948@CI-008 中 conan 经镜像成功下载（完整日志实证，详见下节）。
- 机械闸 PF7（源 URL 闸 / R39）命中的条目仅为镜像前缀形态；`gitee.com/mirrors/snort3`
  曾列入但已移除（gitee 按需重新生成 archive、字节与官方不一致，CI 实测
  "sha256 hash failed"）。
- 处理口径：按「官方托管例外」提请放行（官方源兜底保留、镜像仅作 CI 出网回退）；
  本登记节与 PR 讨论区同步留痕。

## CI 镜像源整改与复验（2026-10-10）

- CI 三连真实构建（#79295 / #79331 / #79472 @CI-037）均死于 `source()` 下载 libdaq
  （ConnectTimeoutError：构建 worker 无 GitHub 直连）→ conandata 两处 `url` 改为
  有序镜像列表，官方 GitHub URL 保留末位兜底（R39），manifest 同步。
- 镜像列表收敛为字节透明源（2026-10-10 依构建 #79948@CI-008 日志修订）：
  `gh-proxy.com` / `ghproxy.net` 为 GitHub 代理前缀，与官方 tarball 字节一致
  （sha256 自洽；gh-proxy 条目在 CI 实证下载成功）；`gitee.com/mirrors/snort3` 已移除
  ——gitee 按需重新生成 archive，字节与官方 tarball 不一致（CI 实测
  "sha256 hash failed"，无法命中本 sha256）；`ghfast.top` 已移除（域名实测不可达）。
  平台 pre-download 段因 worker 缺 `curl` 恒失败、回退 conan 下载器兜底，最终由
  conan 按列表完成拉取（#79948 日志实证）。
- 设备两轮全链路复验 0 失败：warmup create（`CONAN_HOME=~/tmp/ch/home-snort`，RREV
  `a93e227ef30332c9aeb87504d2546239`）与官方 conan-verify（默认 `~/.conan2`，RREV
  `2e6ceb9a272c99be583508ffee5bfde2`；两缓存独立导出，RREV 各异属流程特性）均全程通过
  ——设备无 GitHub 直连条件下，source 阶段按列表顺序拉取镜像成功（实证）。
- E2E `help_output` 判定环境无关化：`grep -qi "usage\|snort"` →
  `grep -qi -e usage -e snort`。根因：OHOS 默认 PATH 的 `/system/bin/grep` 是 toybox
  （`\|` 按字面量匹配，恒不命中），而 warmup-snort.sh 的 PATH 经 `/data/service/hnp/bin`
  命中 GNU grep 3.12（`\|` 有效）——同一脚本两环境判定相反。修复后官方 verify 复跑
  **Verdict PASS**，G2 内 test_package 6 用例全过（`TEST SUMMARY: 6 passed, 0 failed`）。
