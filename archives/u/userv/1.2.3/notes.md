# userv 1.2.3 适配笔记（A 类：前置适配）

> 本轮定位：完成前置适配（W0 依赖检查 + 源码/构建系统分析 + Conan 配方与 test_package
> + 可行的本机验证 + 真机命令清单）。**尚未在真机编译**，因此状态是 `pending` 而不是 `built`。
> 归档时间：2026-10-14（本机时间为准）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | userv（user services client and daemon） |
| 版本 | 1.2.3 |
| 上游主页 | https://www.chiark.greenend.org.uk/~ian/userv/ |
| 许可证 | GPL-3.0-or-later |
| 构建系统 | 自带 `configure`（autoconf 生成）+ 手写 `Makefile.in`（不是 automake 工程） |
| 产物 | `bin/userv`（客户端，上游 setuid root 装到 /usr/bin）、`bin/uservd`（守护进程，上游装到 /usr/sbin）、`res/userv/`（配置骨架） |
| 依赖 | 无库依赖；构建期需要 `md5sum`（见 §四.5） |
| 分支 | `feat/userv-1.2.3`（worktree：`D:\harmonyos\worktrees\userv`） |

## 二、W0 依赖检查（已完成）

| 检查 | 命令 | 结果 |
|------|------|------|
| 制品仓是否已有 userv | `conan list "userv/*" -r=ohpcd` | `Found 0 pkg/version recipes matching userv/* in ohpcd` → **首次适配，无 R37 版本冲突** |
| 同版本是否已发布 | `conan download userv/1.2.3 -r=ohpcd --only-recipe` | 远端无该 recipe（返回 ohpcd 的 `system acceleration policy not enabled`，即"不存在"，与 `conan list` 结论一致） |
| 构建期工具依赖 coreutils | `conan list "coreutils/9.10:*" -r=ohpcd` | 已发布，且存在与本 profile **完全匹配**的二进制：`arch=armv8 / os=OHOS / compiler=clang 15 / libcxx=libc++ / cppstd=17 / build_type=Release`，package_id `6b129b068851896169fae42d399fa922d239ce8a` |
| md5sum 是否真的在 coreutils 包里 | `conan download coreutils/9.10:6b129b…` + 列目录 | `bin/md5sum`（80320 字节）存在 ✔ |

结论：**无缺失依赖，可以继续本库适配**；不需要拆依赖库 PR。
（附带证据：`D:\harmonyos\适配建议汇总\...避坑指南.md` T11 记录真机需 `sha256sum`；
`archives/u/unpaper/7.0.0` 注释也说明"真机 worker 的 PATH 上本来就有 GNU coreutils"，
因此 `tool_requires("coreutils/9.10")` 既是兜底也是可复现的显式声明。）

## 三、源码与构建系统分析

### 3.1 源码来源（含等价性核验）

| 候选 | 结果 |
|------|------|
| 官网 `https://www.chiark.greenend.org.uk/~ian/userv/` | 可访问，但页面上 "current version" 的 `userv.tar.gz` 实测解包后 `debian/changelog` 首条为 **`userv (1.2.0)`** → 不是 1.2.3 |
| `http://ftp.chiark.greenend.org.uk/users/ian/userv/userv-1.2.3.tar.gz` | 连接超时（本机网络不可达） |
| **`https://deb.debian.org/debian/pool/main/u/userv/userv_1.2.3.tar.gz`（采用）** | 202235 字节，sha256 `259431d0033efa109d21ceec818e119c10342cb23e16185c6bd76c035ec646db` |

采纳理由与证据（R39 / T11「镜像等价」要求）：

1. `userv_1.2.3.dsc`（Debian 已签名，`Hash: SHA512`，维护者即上游作者 Ian Jackson）中
   `Checksums-Sha256: 259431d0033efa109d21ceec818e119c10342cb23e16185c6bd76c035ec646db 202235 userv_1.2.3.tar.gz`
   与本仓库 `conandata.yml` 的 sha256、文件大小逐字节一致。
2. `.dsc` 声明 `Format: 1.0`（Debian **native** 包）→ 该 tarball 就是上游源码包本身，
   不含 Debian 补丁，只多带 upstream 自己的 `debian/` 打包目录。
3. 解包后 `debian/changelog` 首条为 `userv (1.2.3) unstable` → 版本正确。
4. 顶层只有单一目录 `work/` → 配方的 `get(strip_root=True)` 语义成立。

### 3.2 构建流程（逐条对照上游文件）

```
configure（AC_INIT(language.i4) / AC_CONFIG_HEADER(config.h) / AC_OUTPUT(Makefile)）
  ├─ 从 debian/changelog 首条取 VERSION=1.2.3；Makefile 里 VEREXT=std
  ├─ AC_CHECK_PROGS(MD5SUM_SIMPLE, md5sum md5 gmd5sum)   ← 构建期工具依赖
  ├─ CFLAGS="$CFLAGS -D_GNU_SOURCE"；探测 EPROTO / LOG_AUTHPRIV / WCOREDUMP
  └─ 生成 Makefile / config.h / config.status
make -j1
  ├─ 目标 daemon（overlord.o process.o servexec.o parserlexer.o debug.o lib.o both.o）
  ├─ 目标 client（client.o both.o）
  ├─ pcsum.h  ← `cat common.h config.h config.status Makefile | $(MD5SUM)`（client/daemon 协议校验和）
  ├─ lexer.l / tokens.h / lexer.c 均由 tarball 自带，Makefile 用
  │   `lexer.l: language.i4`、`tokens.h: language.i4` 空规则锁住，**不需要 m4/flex**
  └─ version.h ← `echo '#define VERSION "$(VERSION)"'`（client.c / servexec.c 需要）
make check  → 只打印 "There is no validation suite for this package."（退出码 0）
make install DESTDIR=... → sbin/uservd(755)、bin/userv(4755)、etc/userv/*（仅当目标不存在时才安装）
```

关键平台假设（`INSTALL` 明文列出）：`setreuid/getgroups/initgroups`、BSD `syslog(3)`、
`wait3/waitpid`、`AF_UNIX` + `socketpair`、`mkfifo`、POSIX `sigaction/sigprocmask/sigsuspend`、
`setsid`、`fnmatch`、`strsignal`、`realloc(0,size)==malloc(size)`、`free(0)`。

### 3.3 与 OHOS（musl 系 libc + clang 15）的差异核查

系统头文件清单（`grep '^#include <' *.c *.h` 去重）：
`assert ctype dirent errno fcntl fnmatch grp inttypes limits pwd signal stdarg stdio stdlib
string sys/resource sys/socket sys/stat sys/time sys/types sys/un sys/wait syslog time unistd`
—— 全部是 POSIX 头，**没有** glibc 专有头（`error.h`、`sys/sysmacros.h`、`ucontext.h`、`bsd/*`）。

逐个核对 INSTALL 要求的接口：`setreuid`/`initgroups`/`strsignal`/`fnmatch`/`openlog`+`syslog`/
`wait3`/`socketpair`/`mkfifo`/`setsid` 在 musl 系 libc 中均有（`-D_GNU_SOURCE` 由 configure 自己加，
`wait3`/`initgroups`/`strsignal` 正好需要它）。`realloc(NULL,n)`、`free(NULL)` 语义满足要求。

因此 **本轮没有写任何源码补丁**（`patches_applied: []`）：平台差异全部在配方层解决（§四）。
唯一需要真机确认的编译期风险是 clang 15 的新告警级别（见 §六）。

### 3.4 本包形态与运行时边界（重要，避免误判"适配完成"）

* `userv` 客户端**按设计必须是 setuid root**（`Makefile.in:81` 用 `-m 4755` 安装），
  且依赖系统级 `/etc/userv` 配置与常驻 `uservd`。Conan 包只负责"能编译、能打包、
  二进制能执行"；真正把它装成系统服务（setuid、/etc/userv、/var/run/userv、systemd 单元
  `userv.service`）属于系统集成方的工作，不在本包 PR 范围内。
* `uservd` 运行期需要 `VARDIR=/var/run/userv`（`common.h:37-46`）与 `SYSTEMCONFIGDIR=/etc/userv`，
  OHOS 上这些路径的可写性/权限策略未验证 → 本轮不声明"服务已可用"，只声明"构建产物 +
  CLI 契约可用"。

## 四、配方设计要点（每条都有上游依据）

1. **不使用 `AutotoolsToolchain`**（`conanfile.py` 文件头第 1 条）。
   Conan 对 Release/RelWithDebInfo/MinSizeRel 会把 `-DNDEBUG` 放进 `CPPFLAGS`
   （`conan.tools.gnu.autotoolstoolchain` 的 `ndebug`），CI profile 正是 `build_type=Release`。
   而 userv 把 NDEBUG 当成"构建配置错误"：
   * `client.c:1335` `#ifdef NDEBUG` → `# error Do not disable assertions in this security-critical code !`
   * `overlord.c:273` `#ifdef NDEBUG` → `abort();`
   虽然 `Makefile.in:26` 用 `CPPFLAGS=@DEBUGDEFS@ $(XCPPFLAGS)` 重新赋值、会静默丢掉环境里的
   CPPFLAGS（`@CPPFLAGS@` 未被替换），当前未必真把 `-DNDEBUG` 传进编译 —— 但这是"侥幸"，
   且一旦将来有人给 make 传 `XCPPFLAGS` 就会踩雷。配方改为
   `VirtualBuildEnv` + 从 `tools.build:compiler_executables` / `tools.build:cflags` 取
   `CC/CXX/CFLAGS/LDFLAGS`（仍然满足 R33：不依赖 CI 上未定义的 shell 变量）。
2. **`INSTALL_FLAGS=` 覆盖**：`Makefile.in:35-36` 的 `INSTALL_FLAGS=-o root -g 0`
   会让非 root 的 CI 在 `make install` 时 `cannot change ownership` 失败。
3. **`sbindir=/bin`**：`uservd` 默认落到 `$(sbindir)`；CI 的 L2/L5 门禁只扫描 `bin/`，
   Conan 标准可执行目录也是 `bin/`。两个二进制都进 `bin/`（与 `archives/d/duo-unix` 同思路）。
4. **`etcdir=/res`**：把 `/etc/userv` 配置骨架收进 `<pkg>/res/userv/`，Conan 包不往系统 `/etc` 写。
   `bindir/sbindir/etcdir` 一律用绝对路径，规避 `$(DESTDIR)$(var)` 直接拼接时缺 `/` 的坑
   （`archives/c/cachefilesd-inotify` 记录过同类问题）。
5. **构建期 md5sum → `tool_requires("coreutils/9.10")`**：`Makefile.in:144-149` 的 `pcsum.h`
   依赖 `$(MD5SUM)`；`configure` 只探测 `md5sum/md5/gmd5sum`，探测不到就留空 → 构建必失败。
   上游 `INSTALL` 把 md5sum 列为构建期程序要求，因此在配方里显式声明（已核对 ohpcd 二进制含 `md5sum`）。
6. **`folders.build = "."`**：userv 只支持源码树内构建（`pcsum.h`、`spec.sgml` 等目标用相对路径），
   与 `archives/z/zlib/1.3.1` 相同处理；已用探针配方验证此写法下 `build() == source()`
   且源码会被复制进 build 目录。
7. **`package_type = "application"` + `commands.json`（R38）**：`archives/u/userv/commands.json`
   声明 `type: tool`、`binary: true`。

## 五、上游测试清点与裁剪说明（不冒充通过率）

**上游测试用例总数 N = 4**（`tests/t-basic`、`tests/t-config`、`tests/t-userconfig`、`tests/t-persist`，
均为 Debian autopkgtest 脚本）；**CI 构建沙箱内可运行 0 个**；`make check` 本身没有校验集
（`Makefile.in:113-114` 只打印说明，退出码 0）。

| 项 | 事实 | 本轮处理 |
|----|------|----------|
| `make check` | `Makefile.in:113-114`：`@echo There is no validation suite for this package.`，退出码 0 | `build()` 中仍然调用（保留上游入口，L1c 可见执行痕迹），但**不声称跑过任何断言** |
| `tests/t-basic` | autopkgtest：`userv --override 'execute whoami' games spong`；`debian/tests/control` 要求 `needs-root, isolation-container` | 未运行（Conan 沙箱非 root、无系统级 setuid 安装、无守护进程） |
| `tests/t-config` | 需要 `needs-root, breaks-testbed` + Debian 包 `chiark-really` | 未运行 |
| `tests/t-userconfig` | 同上 | 未运行 |
| `tests/t-persist` | 需要常驻守护进程 + `needs-root` | 未运行 |

因此本包的测试口径是：

* **上游用例数 N=4，沙箱内运行 0/4（0%）**。原因是**环境限制**（不是"上游没有用例"）：4 个用例逐条登记为
  `needs-root / isolation-container / breaks-testbed`、依赖 `chiark-really`、需要系统级 setuid 安装
  （`/usr/bin/userv` + `/usr/sbin/uservd`）与常驻守护进程 + `/etc/userv` 配置；
* **新增打包产物验证 10 项**（`test_package/test.sh`）：真机实测 **9 项通过 + 1 项 SKIP**，
  在允许客户端运行的环境（或 setuid-root 部署）为 13 条全执行。

| # | 断言 | 源码依据 | 真机（OHOS 沙箱） |
|---|------|----------|------------------|
| 1-2 | `bin/userv`、`bin/uservd` 存在且可执行 | `Makefile.in` install 规则 | PASS |
| 3-4 | 两者都是 AArch64 ELF（magic + `e_machine=0xB7`） | 交叉/原生构建产物契约 | PASS |
| 5-6 | `uservd --help`：退出码 **3**，stderr 出现 `usage: uservd [-daemon]` | `overlord.c:279-283`（在 `openlog`/`chdir(VARDIR)` 之前，无需 root） | PASS（真实执行） |
| 7 | `userv` 运行期 CLI 契约：`--version == 1.2.3std`、`--help` 的用法/版本文本、`--copyright` 的 GPLv3 声明、非法选项非 0 退出 | `client.c` `of_version()`/`usage()`/`of_copyright()`/`usageerror()` | **SKIP**（需 setuid-root；见 §十.5） |
| 8-10 | `userv` 构建身份静态校验：嵌入 `1.2.3std`、`usage: userv`、`GNU General Public License` | 编译进 `.rodata` 的同一批字面量 | PASS |

这 10 项（含 SKIP 项）都要求 `bin/` 下真实产物存在，因此 CI L1e（移走 `bin/` 后测试必须失败）
依然成立；SKIP 项在日志里显式打印原因，不伪装成通过。
若在允许普通用户进程执行 `setreuid` 的环境（或 setuid-root 部署）里运行，
第 7 项会自动走完整 CLI 契约分支（本机用 mock 验证过该分支：13 条断言全过）。

## 六、本机验证（已完成 / 受限）

已完成的静态与本机验证：

| # | 验证项 | 命令/方式 | 结果 |
|---|--------|-----------|------|
| 1 | sha256 与已签名 .dsc 一致 | `Get-FileHash -Algorithm SHA256` + 对比 `.dsc` | 一致（`259431d0…46db`，202235 字节） |
| 2 | 版本与目录结构 | `tar tzf` / 读 `debian/changelog` | 1.2.3；单一顶层目录 `work/` |
| 3 | 配方依赖图解析 | `conan graph info . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=同` | 通过；`coreutils/9.10` 命中 ohpcd 已发布二进制（package_id `6b129b06…` 与 profile 完全匹配） |
| 4 | 目录/文件布局假设 | 探针配方 `conan create`（`basic_layout` + `folders.build="."`） | `build_folder == source_folder`，源码被复制进 build 目录 → `./configure` 可执行 |
| 5 | **真配方 `conan create`** | `conan create archives/u/userv/1.2.3 -pr:h=<ohos> -pr:b=<ohos> --build=missing` | `source()` 走通：`Sources correctly downloaded from https://deb.debian.org/debian/pool/main/u/userv/userv_1.2.3.tar.gz` + `Uncompressing … to .`（Conan 自己校验了 sha256）；`generate()` 走通；`build()` 停在 `RUN: /data/service/hnp/bin/bash ./configure --prefix=/`（Windows 上没有 OHOS 工具链，预期失败） |
| 6 | 构建环境脚本内容 | 读 `<cache>/b/.../build-release/conan/conanbuildenv-userv.sh` | `CC=/data/service/hnp/bin/clang`、`CXX=…/clang++`、`CFLAGS=-O2`、`PATH=<coreutils>/bin${PATH:+:$PATH}` ✔ |
| 7 | 源码树复制结果 | 列 build 目录 | `configure / Makefile.in / debian/ / tests/ …` 全在（`strip_root=True` 生效，无嵌套 `work/`） |
| 8 | CI L0 门禁等价自检 | 按 `ci/conan/build_and_test.sh` L0a-L0e/L0h/L0k/L0m 的判定逻辑逐条自查 | 全部通过（见 §6.1） |
| 9 | 元数据语法 | `yaml.safe_load` / `json.load` / `py_compile` | `conandata.yml`、`manifest.yaml`、`test_package/MANIFEST.yml`、`commands.json`、两个 `conanfile.py` 全部通过 |
| 10 | **test_package 断言逻辑自测** | 用 mock（按 `client.c`/`overlord.c` 行为伪造 `userv`/`uservd`）跑 `bash test.sh <mockbin>` | 正向：`assertions: 13, failures: 0`，脚本退出 0；反向 1（版本号改成 1.2.2std）：7 条失败、退出非 0；反向 2（bin/ 为空，等价 CI L1e 移走 bin/）：12 条失败、退出非 0 → 断言确实依赖被测产物 |

本机 `conan create` 还顺手暴露并修掉了两个配方缺陷（都已修正并复测）：

1. **`tools.build:ldflags` 不是合法 conf** —— Conan 里只有 `tools.build:exelinkflags` /
   `tools.build:sharedlinkflags`。原写法在 `generate()` 直接抛
   `ConanException: [conf] 'tools.build:ldflags' does not exist in configuration list`。
   改用 `exelinkflags`（userv 只产出可执行文件）。
2. **`save_script("conanbuild")` 与 Conan 聚合入口撞名** —— `conanbuild.sh` / `conanrun.sh`
   是 Conan 自己生成的聚合脚本名，覆盖同名文件后聚合脚本会 source 到自己
   （实测内容为 `. "…conanbuildenv-release-armv8.sh" && . "…conanbuild.sh"`），
   结果 `CC/CFLAGS` 全部丢失。改名为 `conanbuildenv-userv` 后聚合脚本正确串联两个脚本。
3. **不要依赖 tool_requires 的隐式 PATH 合成** —— 探针配方实测：虽然
   `require.run=True`、`package_type=application`、`bindirs` 指向真实存在的目录，
   但 profile `[buildenv]` 已定义 `PATH` 时，`VirtualBuildEnv` 最终 PATH 里**没有** coreutils。
   因此配方显式 `env.prepend_path("PATH", <coreutils>/bin)`，不再依赖隐式行为
   （这段行为差异在 Windows 上被放大：`${PATH}` 占位符在 Windows 子系统下不被识别；
   真机是 Linux 子系统、可能表现不同，但显式 prepend 在两种情况下都成立）。

**没能做的（如实记录）**：本轮没有在本机做真正的编译验证，原因是本机不存在可用的 Linux/OHOS 编译环境：

* WSL `Ubuntu-22.04` 已注册但发行版磁盘缺失（`Wsl/Service/CreateInstance/MountDisk/HCS/E_ERROR_PATH_NOT_FOUND`），起不来；
* `podman-machine-default`（Fedora 42）可启动但**没有 gcc/make/clang**，且容器内网络不可达（`Network is unreachable`），无法 `dnf install` 或拉镜像；
* Windows 侧只有 mingw gcc，编译 POSIX `syslog/initgroups/AF_UNIX` 代码不具代表性，强行编译只会产生误导性结论；
* 本机没有 OHOS aarch64 工具链（该工具链在真机上）。

因此"编译 + test_package"必须在真机/ shadow CI 上完成（命令见 §八）。
这也是本轮状态写 `pending` 而不是 `built` 的唯一原因。

### 6.1 自检记录（CI L0 等价检查）

```
L0a test_package/ 目录存在                       → pass
L0b test_package/conanfile.py 存在               → pass
L0c test_package/ 下有 .sh 源文件                → pass (test.sh)
L0d test() 存在且含 self.run()                   → pass (conanfile.py:test)
L0e test_package/MANIFEST.yml 存在               → pass
L0f conandata.yml patches 段格式                 → N/A（无 patches 段）
L0h self.run() 未裸用 ${CC}/${CFLAGS}/...        → pass（CC/CFLAGS 经 Environment 注入）
L0k 工具包必须有 commands.json                   → pass（archives/u/userv/commands.json）
L0m 目录层级 archives/u/userv/1.2.3 与 version 一致 → pass
```

## 七、阻塞点 / 风险 / 未验证项

| 级别 | 项 | 说明与应对 |
|------|----|-----------|
| 必须真机确认 | 编译是否一次通过 | clang 15（OHOS 定制版）+ musl 系 libc；上游代码是 2005 年代 C 风格，若出现 `-Wimplicit-*` 级别错误（clang ≥15 有把这类告警升级为错误的趋势）需加 `0001-*.patch`，届时按 R6 只改源模板 |
| 必须真机确认 | `md5sum` 是否真的可执行 | 已用 `tool_requires("coreutils/9.10")` + 显式 `PATH` prepend 兜底，并在本机核对了生成的 `conanbuildenv-userv.sh` 内容；真机上若 coreutils 的 ELF 未签名/不可执行，退路是直接用真机自带 md5sum（去掉 prepend 即可）或给 make 传 `MD5SUM=<真机 md5sum>` |
| 已识别、无需处理 | `-DNDEBUG` 注入 | 通过不用 `AutotoolsToolchain` 规避；已核对 `client.c`/`overlord.c` 的 `#error`/`abort()` |
| 已识别、无需处理 | `install -o root -g 0` | 通过 `INSTALL_FLAGS=` 覆盖 |
| 运行期边界（不在本 PR 范围） | setuid 安装、`/etc/userv`、`/var/run/userv`、常驻 `uservd` | Conan 包不负责系统级部署；已在 §3.4 与 `manifest.yaml` 声明，避免把"能编译"说成"服务可用" |
| 平台差异（未验证） | 真机是否允许 setuid 属性、`/var/run` 是否可写 | 影响的是"整机部署可行性"，不影响本包的编译/打包/CLI 验证结论 |

## 八、下一步命令（真机 / shadow CI）

> 真机单包排队，重任务错峰；userv 是小包（8 个 C 文件），但**不要**与 Apache Arrow / MPI 同跑。

```sh
# 1) 进入 worktree（真机上同步该分支后）
cd <repo>/archives/u/userv/1.2.3

# 2) 单包构建 + test_package（真机隔离环境，务必带项目 settings.yml/profile）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

# 3) 影子 CI / 单包门禁（不要无参数扫全仓；必须经统一 runner 以获得 TMPDIR/TMPPREFIX 与全局锁）
sh "$HOME/bin/ohos-test-runner.sh" --user <user> --lib userv --task shadow-1.2.3 --mode heavy \
   --workdir "$CI_REPO_ROOT" -- sh "$HOME/validation/run-ohos-shadow-ci-local.sh" archives/u/userv/1.2.3

# 4) 提交前检查清单（CI 输出）
#    - build 日志只发现目标包；Build Summary Total: 1
#    - L0/L1 pass；L2 pass（userv --version 可执行；uservd 的 L2 warn 属预期，overlord.c:273/283 行为）
#    - L4 warn 已阅读；L5 确认 <pkg>/bin 下 userv、uservd 真实存在
#    - ci-metadata.json 与日志一致
```

真机若需要人工复核（可选，验证守护进程路径）：

```sh
# uservd 的运行期依赖（本轮未验证，仅作为整机部署参考）
ls -ld /var/run /etc        # VARDIR=/var/run/userv、SYSTEMCONFIGDIR=/etc/userv 是否可创建
command -v md5sum           # 构建期工具（配方已用 coreutils/9.10 兜底）
<在真机上以 root 跑上游 autopkgtest 用例：tests/t-basic 等，需要先 make install 到系统路径>
```

## 九、提交与收尾

本轮已在本 worktree 提交（分支 `feat/userv-1.2.3`，1 个 commit，只含 8 个文件）：

```powershell
cd D:\harmonyos\worktrees\userv
git log --oneline -1          # feat(userv): 1.2.3 前置适配（配方 + test_package，待真机验证）
git diff --stat main HEAD      # 8 files changed, 785 insertions(+)，无删除
```

复现本轮本机验证（证据文件都在 `D:\harmonyos\_userv-stage\`）：

```powershell
python D:\harmonyos\_userv-stage\local-validate.py     # 26 项静态/L0 等价检查
# create-local2.log  = 最终配方的 conan create 本机日志（source+generate 通过，build 停在 ./configure）
# graph-info.log     = conan graph info（含 coreutils tool_requires 解析）
# wsl-probe*.sh      = 本机无可用 Linux 编译环境的取证脚本
```

* 本 worktree 使用 sparse-checkout（`archives/u/userv ci docs scripts templates references knowledge`）：
  原因是 `main` 上存在一个文件名带 CR 的路径 `archives/g/gama/2.29/patches/0002-dataparser-ungated.patch\r\r`，
  Windows 无法检出（`error: unable to create file ... Invalid argument`），会阻断 `git worktree add`。
  实测该 commit 的树仍是完整仓库（`git ls-tree -r HEAD | wc -l` = 111967 = main 的 111959 + 本包 8），
  但后续会话建 worktree 时同样会遇到，建议单独修。
* PR 标题：`feat(userv): 1.2.3 编译完成`（真机验证通过后再提；本轮只做前置适配，不提 PR）。
* 若真机一轮通过，后续动作：把 `manifest.yaml` 的 `status` 改为 `built`（并补 `compile_date`）、
  把本文件 §六 的 `device_pending` 项替换为真机实测结果，然后提 PR。

## 十、真机记录（2026-10-13，影子 CI）

### 10.1 真机环境事实（与配方相关，已实测）

| 项 | 实测值 |
|----|--------|
| 设备 | HarmonyOS / HongMeng Kernel 1.12.0 / aarch64 / Toybox，`$HOME=/storage/Users/currentUser` |
| 登录 PATH 上的 conan | `$HOME/.local/bin/conan`（2.31.1）；影子 CI 内部使用 `$HOME/ohpc-ci-shadow/python-user` 的 **Conan 2.29.1** |
| git | `/data/service/hnp/bin/git`（2.45.2，**不在默认 PATH 上**，跑影子 CI 前必须显式加进 PATH） |
| clang | `/data/service/hnp/bin/clang` **不存在**（该目录只有 git）；实际工具链是 `$HOME/usr/local/bin/clang-15` + `$HOME/usr/local/sysroot` |
| 影子 CI 工具链 | `$HOME/validation/run-ohos-shadow-ci-local.sh` 每次运行生成 `$RUN_ROOT/tools/clang{,++}` 垫片：`clang-15 --sysroot=… -fuse-ld=lld -Wl,--code-sign -D__MUSL__`，并写 `ci/conan/profiles/ohos-local`（`CONFIG_SHELL/SHELL=$HOME/usr/local/bin/bash`） |
| md5sum | `$HOME/usr/local/bin/md5sum` **存在**（构建期依赖在真机本来就满足；配方里的 coreutils/9.10 是双保险） |
| /tmp | **只读** —— heredoc/临时文件必须落在 `$TMPDIR`（直接用 `sh 脚本.sh` 会在 `can't create temporary file /tmp/shXXXX.tmp: Read-only file system` 处失败） |
| 全局锁 | `$HOME/ohos-test-locks/device-global.lock.d`（mkdir 语义）；本次第一次尝试时被 pkgfile 会话占用 → 按规范视为"锁忙"，未抢锁，等其释放后重跑 |

### 10.2 运行方式（隔离 + 排队）

```sh
# job 仓库：从本地 checkout 做对象拷贝克隆（HMDFS 不支持硬链接，--hardlinks 会失败），再增量 fetch origin/main
# 基线：origin/main = 06bbd38cd1012014ff4c3aece5afec7f5b4b1dd4
# 本包改动以 git apply --cached 方式落到索引后提交（影子 CI 用 git archive HEAD，不需要工作树）
sh "$HOME/bin/ohos-test-runner.sh" --user userv-codex --lib userv --task shadow-1.2.3 --mode heavy \
   --workdir "$JOB_BASE/repo/build_in_harmonyos" \
   -- sh "$HOME/validation/run-ohos-shadow-ci-local.sh" archives/u/userv/1.2.3
```

### 10.3 第一轮结果：conan create 失败（Error 127），根因是配方里硬编码的 shell 路径

```
userv/1.2.3: RUN: /data/service/hnp/bin/bash ./configure --prefix=/
/system/bin/sh: /data/service/hnp/bin/bash: inaccessible or not found
ERROR: userv/1.2.3: Error in build() method, line 134
	ConanException: Error 127 while executing
```

根因：`build()` 里写的是
`config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")`。
`CONFIG_SHELL` 由 profile `[buildenv]` 注入，只存在于 **`self.run` 的子进程环境**里，
不在 Conan 进程的 `os.environ` 里；于是取到兜底值 `/data/service/hnp/bin/bash`，
而该路径在本设备上不存在（影子 CI 的 bash 在 `$HOME/usr/local/bin/bash`）→ 127。

修法（本轮已改）：不写死任何绝对路径，用 shell 参数展开在**运行时**求值并校验可执行位：

```python
config_shell = ('config_shell="${CONFIG_SHELL:-${SHELL:-sh}}"; '
                '[ -x "$config_shell" ] || config_shell=sh')
self.run(f'{config_shell}; "$config_shell" ./configure --prefix=/')
```

同一类问题在 `test_package/conanfile.py` 里也已修（改为 `CONFIG_SHELL` → `which(bash)` → `which(sh)` 探测，
找不到则显式报错），并把 `test.sh` 改成 POSIX 语法（去掉 bash 专有的 `pipefail`），
这样即使只能用 `sh` 也能跑。

第一轮同时确认了**其余部分在真机上是好的**（都是继续推进的正向证据）：

* 源码：`Sources correctly downloaded from https://deb.debian.org/debian/pool/main/u/userv/userv_1.2.3.tar.gz` ✔
* 依赖：`coreutils/9.10:…:6b129b06…` 从 ohpcd 下载并安装成功，`tools.build:compiler_executables` 解析到影子 CI 的 clang 垫片 ✔
* 生成的 `conanbuildenv-userv.sh`：`CC=<run>/tools/clang`、`CXX=<run>/tools/clang++`、`CFLAGS=-O2`、
  `PATH=<conan coreutils>/bin:${PATH}`（md5sum 就位）✔
* `conanbuild.sh` 聚合脚本正确串联两个 env 脚本（没有自引用）✔
* KC1-KC5 知识检查、JC 杂项文件检查全部 pass ✔

### 10.4 第二轮结果：configure 成功但 `config.status` 报权限错 → 加 `0001` 补丁

```
checking for md5sum... md5sum          ← 真机本来就有 md5sum，configure 探测通过
CHECKING … EPROTO yes / LOG_AUTHPRIV yes / WCOREDUMP yes / C compiler works
will build version 1.2.3
configure: creating ./config.status
./config.status: line 602: ./confTpMnmo/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

根因：Autoconf 生成的 `configure`/`config.status` 用
`tmp=\`(umask 077 && mktemp -d "./confXXXXXX")\`` 建临时目录。真机上实测：

```
$ ( umask 077 && mktemp -d "./confXXXXXX" )
drwx--S--- 2 20001006 file_manager 3440 ./confdoFIeI
$ ls ./confdoFIeI/probe.awk
ls: ./confdoFIeI/probe.awk: Permission denied     ← 连 stat 都不允许
```

`umask 077` 在该 HMDFS 分区上生成的目录会带上有问题的 MAC 标签，目录内容此后不可访问
（项目经验库 E011/E114 类问题；`archives/v/vcprompt/1.3.0` 在同一天、同一台设备上
复现过一模一样的 `subs1.awk: Permission denied`，并确认 `umask 077 → 022` 后
configure/make/上游测试全部通过）。

修法：新增 `patches/0001-configure-mktemp-umask.patch`（unified diff，2 行），
把 `configure` 第 4458-4468 行那两处 `umask 077` 改成 `umask 022`；这段文本会被
autoconf 原样写进它生成的 `config.status`，所以改一处即两头生效。
补丁已在 `conandata.yml` 的 `patches:` 段声明，由 `apply_conandata_patches()` 在
`build()` 里、configure 之前应用。

（第四轮的最终门禁结果记录在 §十一 / `manifest.yaml` 的 `verification.device_done`。）

### 10.5 第三轮：构建/打包全通，但 `userv` 客户端在真机上被安全策略杀死（SIGSYS）

第三轮（commit `ae92e70d31`）结果：**configure → make → 链接 → make install → package 全部通过**，
产物正是预期布局：

```
package(): Packaged 3 files: uservd, userv, COPYING
package(): Packaged 1 '.default' file: system.default
package(): Packaged 1 '.override' file: system.override
Package '6b129b068851896169fae42d399fa922d239ce8a' created
```

`umask 077 → 022` 补丁生效（`config.status: creating Makefile / config.h` 正常），
编译告警只有 clang 对“编译期未用的 `-Wl,--code-sign` / `-fuse-ld=lld`”提示（链接期才生效）。

随后 test_package 阶段暴露了一个**更深的平台事实**：

```
[test] PASS: userv exists and is executable
[test] PASS: uservd exists and is executable
[test] FAIL: userv --version: exit=159 output='' (expected '1.2.3std')
```

在设备上逐项排查（全部是实测，不是推断）：

| 试验 | 结果 |
|------|------|
| `bin/uservd --help` | exit=3，打印 `usage: uservd [-daemon]` ✔ 正常 |
| `bin/userv --version`（打包件，4755） | **exit=159 + Bad system call (core dumped)**，无任何输出 |
| 拷贝出来 `chmod 755` 再跑 | 同样 159 → **与 setuid 位无关** |
| 构建树里的 `b/client`（755，未安装） | 同样 159 → 与打包/安装方式无关 |
| 最小 C 探针（同工具链编译） | `getpid/getuid/getgid/getgroups` 全部正常，**`setreuid(0,uid)` 立即 SIGSYS** ✔ 定位到具体系统调用 |

根因（源码依据 `client.c:808-821` + `client.c:248`）：

```c
int main(...) { security_init();           /* ← 内部最后调用 priv_suspend() */
                parse_arguments(...); ... }

static void priv_suspend(void) {           /* 非 DEBUG 构建 */
  if (setreuid(0,myuid) != 0) syscallerror("suspend root setreuid(0,myuid)");
}
```

* `userv` 客户端**按设计要求以 setuid root 安装**：启动时无条件把 euid 降回真实用户、
  保留 ruid=0 以便后续恢复。Conan 包里的二进制不是 setuid root（CI 用户无法 `chown root`），
  所以这一步必然失败 —— 在普通 Linux 上表现为 `EPERM` + 报错退出，
  在 OHOS 上表现为该特权系统调用被安全策略直接拦成 **SIGSYS（159）**。
* 因此 **`userv --version/--help/--copyright` 在沙箱里根本跑不到**，
  这与本包构建是否正确无关；原先 test_package 里“跑 `userv --version` 断言版本号”的
  设计前提是错的，本轮已按此事实重写（见下）。

配套改动（本轮提交）：

1. `test_package/test.sh` 重写为分层验证：产物存在性 + AArch64 ELF 头 → `uservd` 真实执行
   （exit 3 + usage 行）→ `userv` 能执行就验完整 CLI 契约，不能执行就退化为
   **构建身份静态校验**（二进制内嵌 `1.2.3std` / `usage: userv` / `GNU General Public License`）
   并显式 `SKIP` 打印原因。真机实测：9 断言 0 失败 1 SKIP，退出码 0。
2. `manifest.yaml` 增加 `compatibility`（level: partial）与 `test_results`，明确写出
   “编译打包可用、客户端运行期需 setuid-root、整机部署未验证”，不把跑不起来说成通过。
3. 运行期边界（**不在本包 PR 范围，需要系统集成**）：setuid-root 安装到系统路径 +
   `/etc/userv` 配置 + 常驻 `uservd`（`VARDIR=/var/run/userv`）。

（第四轮的最终门禁结果记录在 §十一。）

## 十一、第四/五轮：影子 CI 全绿（真机验证结论）

运行方式与第三轮相同（`ohos-test-runner.sh --mode heavy` + `run-ohos-shadow-ci-local.sh`），
基线 `origin/main = 06bbd38cd1012014ff4c3aece5afec7f5b4b1dd4`：

| 轮次 | 被测提交（设备 job 仓库） | 内容 | 结果 |
|------|--------------------------|------|------|
| 第 4 轮 | `821c5f6003f68a6b779c968efae0afe58cd234d3` | 配方 + test_package（文档为当时版本） | 全绿（RUN_DIR `userv-codex-userv-shadow-1.2.3-20261014-002501-47630`） |
| 第 5 轮 | `391d676b9aeb97dacbd22365c5f9f1c2ab069396` | **最终内容**（含本文件与 manifest.yaml） | 全绿（RUN_DIR `userv-codex-userv-shadow-1.2.3-20261014-003145-51931`） |

两轮门禁输出一致：

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: userv version/help failed, uservd failed      ← 非阻塞 warn，原因见 §10.5
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content

━━━ Build Summary ━━━
  Total: 1   Success: 1   Failed: 0   Pass rate: 100.0%
[step] All packages built and tested successfully ✅        （runner exit-code.txt = 0）
```

关键门禁明细（摘自 `logs/build_and_test.log`）：

* `L0i` 依赖检查：`[ok] dependency in registry: coreutils/9.10`
* `L0j` R37 版本冲突：`[ok] version not in registry yet (first publish)`
* `L0k` R38 工具声明：`[ok] commands.json valid (type=tool)`
* `L0m` 目录结构：`[ok] L0m: directory structure valid`
* `L1e` 破坏性反向验证：`[sabotage] bin/ moved away` → `[ok] Negative test confirmed — test genuinely depends on userv`
* `L2`：两条 `[warn] ... (non-blocking)`，对应 §10.5 的平台限制（客户端需 setuid-root、`uservd` 只接受 `-daemon`）

test_package 实际输出（`9 断言 / 0 失败 / 1 SKIP`，两轮一致）：

```
[test] platform: HarmonyOS aarch64
[test] PASS: userv exists and is executable
[test] PASS: uservd exists and is executable
[test] PASS: userv is an AArch64 ELF
[test] PASS: uservd is an AArch64 ELF
[test] PASS: uservd rejects unexpected arguments with exit status 3
[test] PASS: uservd prints its usage line
[test] SKIP: userv runtime CLI contract (exit=159): client.c:248 setreuid(0,uid) requires setuid-root install; OHOS traps the syscall (SIGSYS)
[test] PASS: userv embeds the build version string '1.2.3std' (static build identity)
[test] PASS: userv embeds its usage contract text
[test] PASS: userv embeds the GPLv3 notice
[test] assertions: 9, failures: 0, skipped: 1
```

`ci-metadata.json`（`$RUN_REPO/archives/u/userv/1.2.3/ci-metadata.json`）记下了
source url/sha256、profile `ohos-local`、runner `local-ohos-shadow`、commit 与五道门禁结果。

**内容等价性（内容寻址，永久可校验）**：本包 7 个配方相关文件在“本分支提交”与
“真机第 5 轮被测提交”中逐字节相同（git blob 哈希一致）：

```text
b86020db149b5f14c1bc66416d58381e9d41d685  archives/u/userv/1.2.3/conandata.yml
01965c47fc8c7ee428af0b5631b294612c7360cd  archives/u/userv/1.2.3/conanfile.py
a622be10aa3e3f4c861b8b671632fd54fc666ea3  archives/u/userv/1.2.3/patches/0001-configure-mktemp-umask.patch
754e3846623e3741a31c3f889903ba2b311ab5a8  archives/u/userv/1.2.3/test_package/MANIFEST.yml
f10003e34a5161942c91be779b08a8098e8f0a1e  archives/u/userv/1.2.3/test_package/conanfile.py
0d1ba3275d89e9000ab6a9a3993360bca1308a84  archives/u/userv/1.2.3/test_package/test.sh
80c919728bc30c8262b3f534d27c574d1e92eb4d  archives/u/userv/commands.json
```

产物（真机实测，`package()` 输出）：

```
bin/userv      55744 字节（AArch64 ELF，内嵌 1.2.3std/usage/GPL 文本）
bin/uservd    108992 字节（AArch64 ELF，参数校验路径真机执行通过）
res/userv/{system.default,system.override}
licenses/COPYING
```

至此本包的真机结论是：**构建、安装、打包、门禁全部通过（连续两轮）**；
`userv` 客户端的运行期行为需要 setuid-root 整机部署（见 §10.5 与 `manifest.yaml` 的 `compatibility`），
本包不声称"服务可用"。
