# snort

Snort 3 — 网络入侵检测与防御系统（NIDS/NIPS），适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

Snort 3 是 Cisco 开源的网络入侵检测/防御系统：加载规则集，对实时抓包或 pcap
回放流量做协议解析与规则匹配，输出告警（alert_fast / alert_json 等格式）或
执行 IPS 动作。主程序 `bin/snort` 附带四个工具（`snort2lua` 规则转换、
`u2boat` / `u2spewfoo` 告警转换、`show_flows`）。

- 上游项目：snort3 3.12.2.0（GPL-2.0-only，https://github.com/snort3/snort3）
- 产物：`bin/snort` + 工具四件、`lib/` 共享库、`lib/daqs/` 数据采集模块
- 本配方启用 `ENABLE_UNIT_TESTS=ON`：Catch2 套件内嵌进 `snort` 二进制
  （`snort --catch-test all` 可直接运行），CppUTest 套件经 CTest 注册
- 内置 `libdaq` 3.0.27（上游无发行 tarball、Conan 源无包 → 第二源码自举构建）

## OpenHarmony Scope

配方构建完整 snort 主程序与全部安装面（snort/check/all 三段构建链），真机
`conan create` 干净构建 + 上游 CTest 全量实跑 + test_package 消费者 E2E。
平台差异全部收敛在可移植性补丁与配方生成期变量（见下「OHOS 适配要点」），
上游测试用例零增删零改动（仅 patch 0002 的 tmpfile 平台回退与 patch 0004
的时钟粒度适配，均为测试侧）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libpcap | 1.10.6 | 抓包（含 libdaq 模块检测） |
| pcre2 | 10.45 | 正则 |
| hwloc | 2.14.0 | 线程亲和（**唯一共享库依赖**，运行期经包内 RUNPATH 定位） |
| libdnet | 1.12 | 网络地址 |
| openssl | 3.5.6.1 | 哈希/TLS |
| zlib | 1.3.1.1 | 规则压缩 |
| liblzma | 5.8.1 | 规则压缩（可选，本配方启用） |
| luajit-openresty | 2.1-20260311.1 | Lua 配置/规则引擎（静态） |
| cpputest | 4.0_r2 | 单元测试 executable |
| flex / pkgconf / autoconf / automake / libtool | 2.6.4.2 / 3.0.5 / 2.72 / 1.18 / 2.5.4.1 | 构建工具（flex/pkgconf/automake/libtool 为 tool_requires；autoconf/autoheader 取自宿主 hnp 原生二进制，非 tool_require） |

## OHOS 适配要点

1. **系统名固定**：设备 CMake 4.1.2 把宿主自检为 `HarmonyOS`，而平台模块只随
   `OHOS` 名提供 → 该名下 rpath 系列平台标志变量全为空串，CMake 静默丢弃全部
   `-rpath`/`-rpath-link` 标志；配方经 `tc.variables["CMAKE_SYSTEM_NAME"]="OHOS"`
   固定后恢复。
2. **`CMAKE_SKIP_RPATH` 守卫**（patch 0003）：上游 `cmake/platforms.cmake`
   无条件 `set(CMAKE_SKIP_RPATH ON)` → 加 HarmonyOS/OHOS 守卫，否则安装树
   `bin/snort` 无 RUNPATH，空环境冒烟加载 libhwloc 失败。
3. **代码签名与安装期 rpath 重写**：OHOS ELF 的 `.codesign` 段在链接期写入，
   任何后链接改写即失效——CMake 安装期的 rpath 重写（"Set non-toolchain
   portion of runtime path"）会使安装树二进制 exec 返回 EPERM（rc 126）。
   配方设 `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`，链接期即携带最终安装 rpath，
   安装退化为逐字节拷贝（md5 与 build 树一致），签名保持有效（知识库 E631）。
4. **RPC program number database 缺失**（patch 0001 平台分支）：OHOS musl 系
   libc 无 `<rpc/netdb.h>`、无 `getrpcent` 符号、无 `/etc/rpc` 数据文件，上游
   探测两路皆否时 `SEND_ERROR` 硬失败（libtirpc/1.3.7 制品仓可得，本适配
   不引入以控制依赖面）→ HarmonyOS/OHOS 分支改发
   `-DSNORT_NO_RPC_DB`（STATUS 消息记录降级），`service_rpc.cc` 枚举编译排除、
   静态端口模式保留（知识草稿 `DRAFT-snort-3.12.2.0-ohos-no-rpc-program-db-…`）。
5. **HMDFS 约束**：拒绝 execve 脚本文件（有执行位亦 EACCES）→ `lua_wrap.sh`/
   `ffi_wrap.sh`/`plug_gen.sh` 共 5 处调用点经 `sh` 启动；拒绝 mkfifo →
   make 用 `--jobserver-style=pipe`；不支持符号链接 → libdaq `--disable-shared`。
6. **/tmp 只读**：全部构建步骤 `TMPDIR=<build>/tmp`；上游测试的裸 `tmpfile()`
   （硬编码 /tmp）经 patch 0002 在失败时回退到 `$TMPDIR` 下 mkstemp 临时文件
   （创建即 unlink，语义等价；覆盖 csv/json/text 三个 perf formatter 测试）。
7. **libdaq 内置构建**：`autoreconf` 自举（`--build=aarch64-unknown-linux-ohos`
   绕过 config.guess）；install 后补装全部 `modules/*/libdaq_static_*.pc`
   （上游仅在 `BUILD_SHARED_MODULES` 下安装，而 snort 靠 `pkg-config --list-all`
   发现静态模块）。
8. **ALL 目标不可省略**：部分安装构件只由默认 ALL 目标产出（`api_def` 归档、
   `daqs/daq_*.so`、tools 四件、生成头）→ 构建链 = `snort` → `check` → `all`。
9. **CppUTest 发现**：Conan 工具链的 `CMAKE_FIND_PACKAGE_PREFER_CONFIG` 使
   snort 的 pkg-config 形态 `FindCppUTest.cmake` 不执行 → 配方直接锚定
   `CPPUTEST_INCLUDE_DIR`/`CPPUTEST_LIBRARIES`。
10. **时钟粒度（内嵌测试）**：HarmonyOS 上 `SnortClock` 背靠背读取约 70% 返回
   相同值，而 `rule_profiler.cc` / `time_profiler.cc` 各自的时间用例助手
   `avoid_optimization()` 空循环会被优化消除 → 窗口内可零 tick，两处时间
   检查项（`elapsed > 0` / `elapsed < hr_duration::max()`）成竞态；patch 0004
   对两处助手做有界等待跨过一个 tick（生产代码不受影响）。

## 上游测试

CTest 注册 158 个可执行测试，真机全量实跑：

| 套件 | 用例 | 说明 |
|------|------|------|
| CppUTest（CTest） | 130 | ENABLE_UNIT_TESTS=ON 下经 `add_cpputest` 注册，`make check` 构建并运行 |
| Catch2（CTest） | 28 | 经 `add_catch_test` 注册；同一套件亦内嵌进 `snort` 二进制（`snort --catch-test all`） |

上游测试用例零增删零改动（仅 patch 0002 的 tmpfile 平台回退与 patch 0004
的时钟粒度适配，见版本级 notes.md）。

本版本实测：见版本级 `notes.md`。

### 包内测试（test_package）

| 用例 | 类型 | 说明 |
|------|------|------|
| 版本输出 / `--help` | 消费者契约 | `snort -V` 版本串；`--help` 正常输出 |
| `-T` 配置校验 | 消费者契约 | 内联规则 + 最小 conf 在目标机上校验通过 |
| 合成 pcap 正例 | E2E | 回放合成 pcap，命中规则产生告警（校验告警内容） |
| 同 pcap 反例对照 | E2E | 非匹配规则对同 pcap 不产生告警（对照组） |
| 内嵌 Catch2 套件 | 消费者视角 | 执行上游内嵌套件 `snort --catch-test all`，目标机全过 |

逐例 TEST PASS/FAIL + TEST SUMMARY，任一失败退出码非零。

本版本实测：见版本级 `notes.md`。

## 使用

```bash
conan install --requires=snort/3.12.2.0 -pr:h=<ohos-aarch64 profile>
```

```bash
# 版本
snort -V
# 配置校验（内联规则）
snort -c <conf> --warn-all -T
# pcap 回放 + alert_fast 告警输出
snort -c <conf> -R <rules> -r <capture.pcap> -A alert_fast
# 内嵌单元测试
snort --catch-test all
```

## 参考

- [官方文档](https://www.snort.org/documents)
- [源码仓库](https://github.com/snort3/snort3)
