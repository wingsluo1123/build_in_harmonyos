# libkysdk 3.0.1.0 适配笔记

## 基本信息

| 项 | 值 |
|---|---|
| 软件 / 版本 | libkysdk / 3.0.1.0 |
| 构建系统 | CMake（`cmake_minimum_required(VERSION 3.5)`）+ 上游另附 qmake 测试工程 |
| 上游仓库 | https://gitee.com/openkylin/libkysdk-base（tag `debian/3.0.1.0-2` = `e86700f77cf4`） |
| 源码（conandata） | 上游官方归档：`https://gitee.com/openkylin/libkysdk-base/repository/archive/debian/3.0.1.0-2.tar.gz`，sha256 `f03158704b27527f0295fae581a153bdc89bc63d6f8e67cbbe3ff6a28ebb95d5`（配方 source() 强校验，不一致即 raise） |
| 为何用归档 + sha256 而非 git clone | 本机 git 2.49.0 缺 `remote-https` helper（`git ls-remote https://…` 实测报 `git: 'remote-https' is not a git command`，clone 必失败）；同仓 3.0.1.3 适配时该 helper 可用，本次不可用属本机环境变化。归档端点对 conan/urllib 默认 UA 返回 HTML 下载页（content-type=text/html），但 UA=curl/8.5.0 返回 application/x-compressed-tar；同一 URL 两次下载 sha256 逐字节一致（适配当日实测），可复现性由配方内 sha256 强校验锁定（R39 官方源 = gitee openkylin 官方仓） |
| 许可证 | LGPL-3.0-or-later（COPYING） |
| 补丁数 | 11（见 conandata.yml；A 安装路径 / B conan 依赖接入 / C musl 兼容与上游缺陷） |
| 产物 | 8 个共享库（libkyconf/libkyconf2/libkylog/libkytimer/libkyutils/libkydatastruct/libkygsetting/libkydiagnostics）+ 4 个 CLI（kconf2/conf2-compile/conf2-sync-system/conf2-sync-session）+ 头文件 + etc/kysdk/kysdk-base/kylog-rotate-default |
| 依赖 | glib/2.84.0.1、gtk/3.24.43、dbus/1.14.10、sqlite3/3.53.4、openssl/3.5.6.1、yaml-cpp/0.9.0、qtbase-sql-dbus/6.11.1（+ `expat/2.8.2.1` override） |
| 状态 | built（W3 本地 CI 标准流程贯通：`conan create` EXIT=0 + test_package 10/10 断言全过） |

### 与同仓 3.0.1.3 版本的关系

3.0.1.0 与 3.0.1.3 为同一上游仓库的相邻 Debian 版本（均已由本仓适配）。两版差异极小
（`diff -rq` 仅 conf2 三个文件 + tools/health-check 目录重命名 + 顶层 CMakeLists 的
CMAKE_INSTALL_LIBDIR 硬编码分支链），src/tests/ 测试树逐字节一致。故本适配以 3.0.1.3
配方为基线：
- 10 个补丁（0002~0011）对 3.0.1.0 源码逐一 `patch --dry-run` 验证后**原样复用**；
- 补丁 0001 针对 3.0.1.0 的 CMakeLists 形态**重写**：3.0.1.3 版补丁的上下文（已收敛的
  `set (CMAKE_INSTALL_LIBDIR ${CMAKE_INSTALL_LIBDIR})`）在 3.0.1.0 中不存在——3.0.1.0
  是 `if(CMAKE_HOST_SYSTEM_PROCESSOR MATCHES …)` 硬编码 `/usr/lib/<triplet>/` 分支链，
  新补丁把分支链整体收敛为保持外部传入值，并把 HEADER_DIR 改为 prefix 相对。
- 依赖决策（libsystemd 移除 / qtbase-sql-dbus / expat override / 三个 .pc 缺口）
  与 3.0.1.3 完全一致，见下节。

### 依赖决策要点（与 3.0.1.3 相同）

- **libsystemd 被移除**：全库对 systemd 的唯一用法是 `src/log/write.c` 的
  `sd_journal_send()`。OHOS 无 systemd 运行时、无 journald。改为
  CMake 能力探测（`check_include_file("systemd/sd-journal.h")`）+ POSIX `syslog(3)` 回退。
- **Qt6 用 `qtbase-sql-dbus/6.11.1`**：ohpcd 的 `qtbase/6.11.x` 硬编码 `FEATURE_sql=OFF`，
  而 `conf2-compile` 需要 `Qt6::Sql`。先例：archives/a/akonadi、actiona、alkimia。
- **`expat/2.8.2.1` override 必需**：`dbus/1.14.10` 精确 pin `expat/2.8.2`，gtk→fontconfig 链
  pin `expat/2.8.2.1`，否则 `conan graph` 直接报 Version conflict。
- **三个 pkg-config 缺口在 generate() 中补齐**：`gio-unix-2.0.pc`（glib 配方无该组件）、
  `dbus-1.pc`（dbus 未设 pkg_config_name，先例 at-spi2-core）、`openssl.pc`（openssl 只有
  组件级 .pc，先例 asterisk-srtp）。

## 适配过程与踩坑记录（真实命令 / 退出码 / 日志）

日志根目录：`/storage/Users/currentUser/rjj/kysdk-base-3.0.1.0/logs/`（`conan-create.log`、
`upstream_tests/`、`gtest/` 全量留档）

| # | 首个错误（原文） | 根因 | 修复 | 重新验证 |
|---|---|---|---|---|
| 1 | `conan create` → `unrecognized arguments: libkysdk/3.0.1.0@` | Conan 2.x 不接受 `name/version@` 位置参数（那是 Conan 1.x 语法） | 改 `conan create . --name=libkysdk --version=3.0.1.0 …` | 进入正常流程 |
| 2 | `conan create` → `Failed to parse patch: …/0001-CMakeLists.txt.patch`（`extra lines for hunk no.1 at 26`） | worker 手写的 0001 补丁 hunk 头 `@@ -20,17 +20,12 @@` 与实际行数不符（上下文行数数错） | 用 `diff -u` 重新生成补丁（hunk 头由工具自动计算） | 11 个补丁全部 `Apply patch` 成功（conan-create.log） |
| 3 | `CMake Error: The CMAKE_C_COMPILER "/data/service/hnp/bin/clang" is not a full path to an existing compiler tool` | 仓库 CI profile `ohos-aarch64` 硬编码 `/data/service/hnp/bin/` 编译器路径，本机该路径不存在/无权限（`ls` 报 Permission denied） | 本机用覆盖 profile `profile-local`（`include` 仓库 profile + `tools.build:compiler_executables` 指向 `/storage/Users/currentUser/usr/local/bin/clang{++,}`） | configure 进入编译阶段 |
| 4 | `CMake Error: Could NOT find PkgConfig (missing: PKG_CONFIG_EXECUTABLE)` | 本机无 pkg-config/pkgconf | `sh $HOME/tmp/cmd-pkgs-install.sh pkg-config 0.29.2` 安装（cmd-pkgs 预编译包，R18 先查预编译） | `pkg-config --version` → 0.29.2 |
| 5 | `fatal error: 'string' file not found`（C++ 编译） | 本机 clang 的 libc++ 头不在默认搜索路径（`-print-search-dirs` 无 c++ 头目录） | profile-local 加 `tools.build:cxxflags=["-nostdinc++", "-isystem", "/storage/Users/currentUser/ohos-sdk/include/libcxx-ohos/include/c++/v1"]`（`__config_site` 实测在该目录下） | 编译通过 |
| 6 | `make: *** [all] Error 2` → `ld.lld: unable to find -lglib-2.0`（补丁链 OK 后首报） | 与 3.0.1.3 踩坑表 #9 同因：`pkg_check_modules` 的 `-L` 在 `*_LIBRARY_DIRS` | 复用 0002 补丁（`link_directories(${GLIB_LIBRARY_DIRS})` 等），3.0.1.0 源码的 conf2 CMakeLists 与 3.0.1.3 相同，补丁原样生效 | `cmake.build()` EXIT=0 |
| 7 | 测试二进制 `rc=127`：`Error loading shared library libkyutils.so.1 … symbol not found` | 与 3.0.1.3 踩坑表 #10 同因：上游 install 把 `.so`/`.so.1` 产出为**符号链接**，OHOS 加载器按 SONAME 打开软链即失败 | 配方 `_materialize_soname_aliases()` 在 `package()` 末尾把软链实体化（知识 E316/E492，先例 gnustep-gui） | test_package 10/10 断言通过；包内 lib/ 软链计数 = 0 |
| 8 | test-kygsetting / kyconf2-test 运行 `rc=127`（上游 CMake 内建测试） | 测试二进制运行时需要 glib/gtk/dbus 等依赖 .so，LD_LIBRARY_PATH 未注入 conan 依赖包 lib 目录 | 构建目录（`conan install` 后依赖包的 `p/lib`）全量拼入 LD_LIBRARY_PATH 重跑 | 12/12 全部 rc=0 |

> 说明：本次未遇到 3.0.1.3 踩坑表 #13/#14 的 safe-delete 垫片与 SELinux 域问题——
> 本机当前环境 BASH_ENV/CODEBUDDY 干净、`symlink` 实测可用（`os.symlink` 测试通过），
> 属环境变化；如 CI worker 复现，以 3.0.1.3 notes.md 对应条目为准。

## 上游测试（R51 三步法）

1. **清点**：上游测试入口两个 —— ① CMake 模块内建测试目标 12 个（随 `cmake.build()` 编译）；
   ② `src/tests/*.pro` qmake + gtest/gmock 套件 7 个（`src/tests/auto-test.sh` 驱动）。
   用例口径：gtest 7 套件共 84 个 TEST/TEST_F（kyconf2 7、kyconfig 8、kydiagnostics 1、
   kygsettings 23、kylog 9、kyprocess 1、kyskiplist 3、kytimer 1、kyutils 33——其中
   kydiagnostics/kyprocess 无 .pro 不在 tests.pro SUBDIRS 中），上游声明总数
   = CMake 12 + gtest 84 = 96。
2. **实际运行**（日志：`logs/upstream_tests/`、`logs/gtest/`，均本机 OHOS 6.0/armv8/clang 15 实测）：
   - 入口① **12/12 通过**（rc=0）：test-utils、test-delete、test-insert、test-search、
     test-kytimer、kylog-testlog、kylog-testsetdir、kylog-testautowrap、kylog-testpressure、
     test-kygsetting、kyconf2-test、kyconf-test-struct（后者需 cwd 含 `struct.conf`）。
   - 入口② **6/7 套件可构建运行**：
     - kyskiplist-gtest 3/3 通过；kyconfig-gtest 8/8 通过（需 cwd 可解析
       `../src/tests/kyconfig-gtest/struct.conf`，本机 cwd=源码目录 src/ 下运行）；kytimer-gtest 1/1 通过；
     - kygsettings-gtest 23 用例中 5 失败 —— 需要 Kylin 桌面 GSettings schema 数据
       （本环境无，GLib 报 schema lookup 失败）；18/23 通过；
     - kylog-gtest 首个用例 `kdk_logger_init("logtest.conf")` 断言失败（rc=134）——
       需要可写 `/var/log` 与 `/etc/kysdk` 配置；
     - kyconf2-gtest 无输出超时（rc=124，依赖 D-Bus/conf2 服务端）；
     - kyutils-gtest **无法编译**：用例调用 `strisletter()`，上游实现里函数名是
       `strisalpha()`（`src/utils/cstring-extension.h:424`）——**上游用例缺陷**，
       未修改上游测试文件（与 3.0.1.3 完全一致）。
   - gtest 套件的本地构建需要三处覆盖（均为上游测试工程自身问题，不影响产品库）：
     gtest/gmock 的 `.pc` 重建（conan 包内 `.pc` 的 prefix 指向已失效的构建路径）、
     上游 `.pro` 的 `-fno-exceptions` 与 `-lgcov`（clang 无 libgcov）。本机直接以
     clang/clang++ 手动编译 7 套件（qmake 的 Qt 模块 pri 解析在本机指向失效 build
     路径，改用显式编译命令等价实现同一 .pro 语义，见 `logs/gtest/`）。
3. **如实回填**：见 `test_package/MANIFEST.yml` 与 `reports/test-report.md`。

## 已知限制 / 平台说明

- O-1：**无 journald**。`write.c` 的 journald 直写路径在无 `systemd/sd-journal.h` 时降级为
  POSIX `syslog(3)`；该分支为构建期能力探测（`KYLOG_HAVE_SD_JOURNAL`），非平台宏，
  未使用 `__OHOS__`（R8/PF5）。
- O-2：**musl 无 pthread 取消**。`kytimer` 核心线程与 `klog` 异步刷新线程改为协作式退出
  （`g_coreThreadStop`/`g_mqThreadStop` + `pthread_join`），`epoll_wait` 由无限阻塞改为
  200ms 超时以观察退出标志。
- O-3：`conf2-compile` 依赖 Qt6::Sql，故 Qt 依赖选用 `qtbase-sql-dbus` 变体而非 `qtbase`。
- O-4：运行期 Python 组件（conf2 的 service/tools 脚本）属打包/运行期依赖，不在 conan
  编译链内。

## 本机执行环境说明（排错要点，均已在环境层解决，配方本身保持可移植）

> 与 3.0.1.3 不同，本机当前 git 无 remote-https helper、`/data/service/hnp/bin` 无权限、
> libc++ 头在 ohos-sdk 目录。这些均为**本机环境状态**，CI worker 以仓库标准
> `ci/conan/profiles/ohos-aarch64` profile 构建时不受影响；配方不引用任何本机绝对路径
> （仅 conandata.yml 的官方源 URL 与 sha256，R39/PF7 合规）。

1. 源码拉取：见「源码（conandata）」行——归档 + sha256 强校验，不依赖 git helper。
2. 编译器：profile-local 覆盖 `tools.build:compiler_executables`（本机 clang 15.0.4
   Target aarch64-unknown-linux-ohos）。
3. libc++ 头：profile-local 注入 `-nostdinc++ -isystem …/ohos-sdk/include/libcxx-ohos/include/c++/v1`。
4. pkg-config：cmd-pkgs 预编译包 pkg-config/0.29.2 安装到 `/storage/Users/currentUser/usr/local/bin`。

**最终验证结果**（本机 OHOS 6.0 / armv8 / clang 15.0.4，标准 `conan create` 流程）：

| 环节 | 结果 | 证据 |
|---|---|---|
| `conan create` | ✅ EXIT=0，产出包 `71ff29ebc4…` | `logs/conan-create.log` |
| test_package | ✅ 10/10 断言，`total failures = 0` | `logs/conan-create.log` 尾部 |
| 上游 CMake 内建测试 | ✅ 12/12 rc=0 | `logs/upstream_tests/*.log` |
| 上游 gtest 套件 | ✅ 6/7 可构建运行；3 套件全过（12/12），1 套件 18/23（缺 schema），2 套件运行期缺环境中止；1 套件上游缺陷无法编译 | `logs/gtest/*.log` |
| 包内 lib/ 软链 | ✅ 0 软链（全实体） | `logs/conan-create.log` |

---

**编译结束**: 2026-10-01
**最终状态**: built
