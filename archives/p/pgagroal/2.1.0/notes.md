# pgagroal 2.1.0 适配笔记

pgagroal 是 PostgreSQL 的高性能连接池。上游产物为共享库 `libpgagroal.so` 与五个命令行工具
（`pgagroal` 守护进程、`pgagroal-cli`、`pgagroal-admin`、`pgagroal-vault`、`pgagroal-config`），
因此按 R38 在**软件级**目录声明 `commands.json`，并按上游实际形态标注 `package_type = "shared-library"`
（上游 `add_library(pgagroal SHARED ${SOURCES})` 硬编码，配方不声明 `shared` 选项）。

## 编译环境

- 构建系统: cmake（CMakeLists.txt，cmake_minimum_required 3.14；实际用 CMake 4.1.2）
- 编译日期: 2026-10-16
- 编译器: clang 15.0.4（OHOS SDK）
- 状态: built（本地 W3 通过；制品仓发布由 CI release 流水线完成）

## 源码选择

| 候选 | 结果 |
|------|------|
| GitHub tag 归档 `archive/refs/tags/2.1.0.tar.gz` | 含 `test/`（82 个文件），但 GitHub 生成的归档哈希不稳定 |
| 官方 release 资产 `releases/download/2.1.0/pgagroal-2.1.0.tar.gz` | ✅ CPack 源码包，哈希稳定；**按上游 `CPACK_SOURCE_IGNORE_FILES` 有意排除 `test/`** |

`conandata.yml` 采用 release 资产，sha256 = `728b93154092b9961eb1c59012210ad5fdfbe418aabb650221e1b31d355e6c09`。

## 依赖（W0 实测全部有预编译二进制，默认选项即可安装）

| 依赖 | 版本 | 形态 |
|------|------|------|
| zlib | 1.3.2.1 | 静态 `libz.a`（PIC） |
| bzip2 | 1.0.8.2 | 静态 `libbz2.a`（仓内无 shared 变体） |
| zstd | 1.5.6 | 共享 `libzstd.so` |
| lz4 | 1.10.0.3 | 静态 `liblz4.a`（仓内无 shared 变体） |
| openssl | 3.5.8.1 | 静态 `libssl.a`/`libcrypto.a`；选 3.x 线以匹配上游 OpenSSL 3 API |

W0 用 `conan install --build=never` 逐包实测（R35：不用 `conan list` 判断）——五个依赖二进制全部可在
OHOS/aarch64 profile 上直接安装，无需从源码构建。

## 编译步骤

```bash
# 配方阶段（W3/CI 同源）
conan create archives/p/pgagroal/2.1.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fatal error: 'openssl/ssl.h' file not found`（20 个文件全挂） | `src/CMakeLists.txt` 的 include 目录分平台声明：Linux 分支用 `${OPENSSL_INCLUDE_DIR}`，非 Linux（含 OHOS）分支用 `${OPENSSL_INCLUDE_DIRS}`；而 CMake 4.1 的 `FindOpenSSL` **只定义单数** `OPENSSL_INCLUDE_DIR`，复数变量为空 | 配方同时注入单数+复数两个 cache 变量（对旧版 CMake 亦无害） |
| 2 | `fatal error: 'sys/event.h' file not found`（ev.c） | 事件循环用 `#if HAVE_LINUX` 二选一：epoll 族 / BSD kqueue。上游该宏来自 `CMAKE_SYSTEM_NAME STREQUAL "Linux"`，而 Conan 把 OHOS 映射为 `HarmonyOS`，于是走了 kqueue 分支；OHOS sysroot 无 `sys/event.h`（确认 `sys/epoll.h`/`sys/eventfd.h`/`sys/timerfd.h` 均在） | 配方补 `-DHAVE_LINUX=1`（OHOS 本就是 Linux 内核、libc 提供 epoll/eventfd/timerfd，这正是上游该分支的语义）；影响面仅 ev.c 事件循环与 utils.c 进程标题 |
| 3 | `_Atomic(T) arr[N] = {0}` 编译失败（ev.c:144-145） | OHOS clang 15 拒绝该写法（`initializer element is not a compile-time constant` / `incompatible integer to pointer conversion`）；最小复现证实与配方宏无关 | 补丁 0003 去掉显式初始化器——静态存储期对象本就零初始化，语义完全等价 |
| 4 | `call to undeclared function 'secure_getenv'`（utils.c / admin.c） | `secure_getenv()` 是 glibc 扩展，musl 只有 `getenv()` | 补丁 0004 以 **libc 特性宏 `__GLIBC__`** 判别（非平台宏）：glibc 保留上游行为，其他 libc 回退 `getenv` |
| 5 | 上游 `find_package(Rst2man)` 直接 `FATAL_ERROR` | OHOS 无 python3-docutils，而 man 手册只由 rst2man 渲染；`doc/CMakeLists.txt` 每个调用点**本就**有 `if (RST2MAN_FOUND)` 守卫 | 补丁 0001 把顶层判据降级为状态信息——有无 rst2man 时，除 man 手册外行为与上游逐字一致 |
| 6 | `Static library detected ... Shared libraries are required`（预期会发生） | `pgagroal_require_shared_libs()` 拒绝仅提供静态库的依赖；制品仓 zlib/bzip2/lz4/openssl 只有 PIC 静态 `.a` | 补丁 0002 新增**可选**开关 `PGAGROAL_ALLOW_STATIC_DEPS`（默认 OFF = 上游严格行为），配方显式开启 |

> 与兄弟包 pgexporter 0.8.0 的差异：pgexporter 用 `pip3 install docutils` + 自造 rst2man wrapper 绕过
> 问题 5，构建期依赖网络与 pip；本包改为让 man 手册优雅跳过，构建期无外部网络依赖。

## 源码修改

| 文件 | 补丁 | 修改内容 |
|------|------|----------|
| CMakeLists.txt | 0001-CMakeLists.txt.patch | `find_package(Rst2man)` 缺失时由 `FATAL_ERROR` 改为状态信息（man 手册跳过） |
| src/CMakeLists.txt | 0002-src-CMakeLists.txt.patch | 新增 `option(PGAGROAL_ALLOW_STATIC_DEPS ...)`，开启时跳过静态库拒绝检查 |
| src/libpgagroal/ev.c | 0003-src-libpgagroal-ev.c.patch | 去掉两个 `_Atomic` 数组的显式零初始化器（clang 15 拒绝该写法） |
| src/libpgagroal/utils.c、src/admin.c | 0004-src-libpgagroal-utils.c-src-admin.c.patch | `secure_getenv` 按 `__GLIBC__` 判别回退 `getenv` |

补丁均为可移植性修复：无平台宏（`__GLIBC__` 为 libc 特性宏）、无空壳 stub、无业务逻辑改动。

另有一处**仅用于本机执行上游测试**的改动，不进入配方（release 资产不含 `test/`，挂进
`conandata.yml` 必然 apply 失败）：`test/testcases/test_aes.c` 的 `mkdtemp` 模板改为读 `TMPDIR`，
见 `reports/upstream-test-aes-tmpdir.diff` 与 `reports/upstream-test-report.md`。

## 验证结果

### 上游测试（R51 三步法）

**清点**：上游测试套件包含 11 项

1. 10 个 MCTF 套件、**96 个用例**（`test/testcases/`：aes 12、alias 4、art 16、configuration 31、
   connection 2、deque 11、json 6、pgbench_init 2、startup_validation 10、utf8 2），编译进
   `pgagroal_test`（MCTF runner）；
2. `container_test` —— `test/check.sh` 在 **docker/podman 容器**里拉起 PostgreSQL
   （`pgagroal-test-postgresql17-rocky10` 镜像）驱动端到端。

**执行（实测，非申报）**：第 1 项 96 个用例在 HarmonyOS PC / aarch64 上全部真实执行并 100% 通过。

```
=== Test Summary ===
Total tests: 96
Passed: 96
Failed: 0
Skipped: 0
```

- 逐条 `[PASS]` 输出：`reports/upstream-test-run.log`（120 行，含 aes 12 例、art 16 例等全部行）
- 执行报告（环境、三处平台差异、崩溃根因分析、复现步骤）：`reports/upstream-test-report.md`
- 复现脚本：`reports/upstream-test-runner.sh`
- 被测对象与配方产物同源：同一份源码 + 4 枚配方补丁 + 与配方逐项相同的 CMake 参数
  （`-DHAVE_LINUX=1`、单/复数 `OPENSSL_INCLUDE_DIR*`、`PGAGROAL_ALLOW_STATIC_DEPS=ON`、`-j1`），
  并配上真实 PostgreSQL 16.10（本地 initdb）+ 运行中的 pgagroal 连接池
- 其中 10 例（alias 4、connection 2、pgbench_init 2、utf8 2）经真实 PG 与连接池完成
  database 别名路由、建连、UTF-8 用户与 pgbench 初始化，属**运行时行为**证据而非纯断言

**第 2 项（`container_test` / `test/check.sh`）在 CI worker 上不具备执行条件**（代码定位）：

- `test/CMakeLists.txt:141` 把 `add_test(NAME container_test …)` 包在 `if(container)` 内，
  `container` 仅在探测到 docker/podman 时为真 → OHOS 上 CTest 配置期实测输出
  `-- Docker or podman needed. The test suite will be skipped.`，不注册任何用例；
- 该脚本的免容器分支 `check.sh ci`（`check.sh:1250-1253`）实测同样不可用：
  `start_postgresql()`（`check.sh:325-337`）需 root 执行 `cp -R $TEST_PG_DIRECTORY/root /`、
  `mkdir -p /conf /pgconf /pgdata /pgwal /pglog`、`chown -R postgres:postgres …`，并依赖
  `postgres` 系统用户与 `runuser`/`sudo -E -u postgres`；worker 上 uid=20020085、根文件系统为
  只读 `erofs`（`/tmp` 亦为只读挂载），且 `test/postgresql/src/postgresql17` 专用 PG 构建产物不存在；
- 非 `ci` 分支 `check.sh:83-90` 直接 `exit 1`（`Neither Docker nor Podman is installed.`）。

`test_package/MANIFEST.yml` 与 PR 正文均已按上述实测结果申报，不再出现「未跑/不可运行」的口径。

**上游测试文件的唯一改动**（不进配方）：`test/testcases/test_aes.c:84` 的 `mkdtemp` 模板原本写死
`/tmp/pgagroal_test.XXXXXX`，而 HarmonyOS PC 的 `/tmp` 是只读 `erofs` 挂载 → 改为读 `TMPDIR`
（缺省仍回退 `/tmp`），断言与用例逻辑零改动，diff 见 `reports/upstream-test-aes-tmpdir.diff`。
该改动**没有进入配方补丁列表**：release 资产按 `CPACK_SOURCE_IGNORE_FILES` 不含 `test/`，
`conandata.yml` 若挂这枚补丁会 apply 失败。

### 鸿蒙真机消费者用例（test_package，`conan create` 自动执行）

7 项断言全部通过（W3 实测）：

```
OK: linked libpgagroal, pgagroal_version_number() = 20100
OK: pgagroal_version_as_number(2, 1, 0) = 20100
OK: pgagroal --version -> pgagroal 2.1.0
OK: pgagroal-cli --version -> pgagroal-cli 2.1.0
OK: pgagroal-admin --version -> pgagroal-admin 2.1.0
OK: pgagroal-config --version -> pgagroal-config 2.1.0
OK: pgagroal-vault --help -> pgagroal-vault 2.1.0
PASS: pgagroal consumer flow (library API + 5 tools) completed on OHOS
```

前两项是**实质性链接证据**：`pgagroal_version_number()` 由 `libpgagroal.so` 提供，返回值 `20100` 与其
`pgagroal_version_as_number(2,1,0)` 的定义一致——库被真正链接并调用了。

### 两个消费者侧的实测结论（供后续包参考）

1. **CMakeDeps 只遍历「已声明组件」的 requires**：把依赖写在根级 `cpp_info.requires` 会被忽略（生成的
   `pgagroal-release-armv8-data.cmake` 中 `COMPONENT_NAMES` 为空，五个依赖只有 zstd 漏出）。改为显式组件后
   `COMPONENT_NAMES` 正确填充，但 zlib/bzip2/lz4/openssl 仍不生成 config 文件（其 recipes 未声明
   `cmake_find_mode`），消费者拿不到它们的头路径。
2. 因上述 1，`test_pgagroal.c` **不包含** `<utils.h>`（该头会链式引入 `<openssl/ssl.h>`），而是按 utils.h
   的签名就地声明两个版本 API 原型后直接链接调用；测试关注的是交付的库与二进制，不是传递 C 头。
   `test_package/conanfile.py` 的 `test()` 另外显式把**全图依赖**的 libdir 加进 `LD_LIBRARY_PATH`——
   `libpgagroal.so` 把 zstd 作为独立共享库依赖（`libzstd.so.1`），仅靠 pgagroal 自身的 libdir 会
   `Error loading shared library libzstd.so.1`。

### 构建侧加固（吸取 pgqd 的教训）

`generate()` 中 `self.conf.define("tools.build:jobs", 1)` 强制串行：OHOS CI worker 在高负载时会出现
`fork: Resource temporarily unavailable`，并行 make 会放大压力，且 CMake 的特性探针在无法 fork 时会**静默**
回 `no`（实测该坑在 pgqd 上产出过坏 `config.h`）。该 conf 驱动 `cmake --build … -- -j1`；`cmake --install`
本身即为串行调用，无需并行参数。

> 注意 `cli_args=["-j1"]` **不是**正确写法：`cmake --install` 会报 `Unknown argument -j1`；而
> `cmake --build` 虽接受，Conan 仍会追加 `-- -j20` 覆盖掉它。

## 产物

```
bin/pgagroal  bin/pgagroal-cli  bin/pgagroal-admin  bin/pgagroal-vault  bin/pgagroal-config   (ELF 64-bit LSB arm64)
lib/libpgagroal.so
include/*.h (34 个头文件)
licenses/LICENSE
```

## 注意事项

- pgagroal 2.1.0 **不用 libev、不用 libssh**：事件循环是自研的 epoll 实现（`src/libpgagroal/ev.c`），
  因此无需把这两个包列为依赖。
- io_uring / systemd / libatomic 只在 `CMAKE_SYSTEM_NAME == Linux` 分支探测，OHOS 上自动跳过——
  不是缺陷，OHOS 版本不需要这几个后端。
- 测试期产物全部落在 `$TMPDIR`／构建目录，`archives/` 内不产生运行期文件（R9）。
- `Problem parsing /proc/meminfo` 与 `make: jobserver mkfifo ... Operation not permitted` 是 HMDFS
  环境噪声，不影响构建与测试结论。

---
**编译结束**: 2026-10-16
**最终状态**: built
