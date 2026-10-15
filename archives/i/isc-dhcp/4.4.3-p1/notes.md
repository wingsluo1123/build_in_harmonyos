# isc-dhcp 4.4.3-p1 适配笔记

## 编译环境
- 构建系统: autotools（2014 年代的树：顶层 configure + 子目录递归 Makefile，libtool 静态库）
- 编译日期: 2026-10-14（首次适配）
- 编译器: clang 15.0.4（OHOS SDK 26，aarch64-linux-ohos，musl）
- 工作副本: 设备 `$HOME/tmp/builds/isc-dhcp-4.4.3-p1.work`（in-source 构建）
- 状态: built

## 本件定位

ISC DHCP 4.4.3-P1 是单体 autotools 工程，本包交付完整套件（服务器/客户端/中继/
omshell + 三库），捆绑 BIND 9.11.36 的四个库作为静态链接闭包随包交付。与 kea 系
（kea/kea-hooks/kea-hook-* 等 3.x Meson 包）是不同代际、不同构建系统的独立实现。

## 编译步骤

```bash
# 1) Conan 配方构建（CI profile 默认选项 tests=False，无外部依赖）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 2) 门禁
ohc-run.py conan-verify isc-dhcp 4.4.3-p1
ohc-run.py finish isc-dhcp 4.4.3-p1 built
```

真机全量测试（上游 ATF 套件，需外带 atf-0.19）：

```bash
conan create . -pr:h=... -pr:b=... \
  -o tests=True -c user.isc-dhcp:atf_prefix=$HOME/atf19
```

## 上游测试（实测执行）

启用方式：`--with-atf=<prefix>`（configure 探测 ATF 0.19 并把 `bin/` 写进生成的
tests/unittest.sh），`make check` 依次运行 common/client/relay/server 四个 tests
目录、共 13 个 ATF 程序：

- `common/tests`：alloc_unittest、dns_unittest、domain_name_unittest、
  misc_unittest、ns_name_unittest、option_unittest（25 用例）
- `client/tests`：duid_unittests（1 用例）
- `relay/tests`：relay_unittests（3 用例）
- `server/tests`：dhcpd_unittests、hash_unittests、leaseq_unittests、
  legacy_unittests、load_bal_unittests（27 用例）

**注意（空转陷阱）**：不配置 ATF 时 `make check` 只编译 tests/libt_api.a，不执行
任何测试即"通过"。因此配方在 `tests=True` 而未提供 `user.isc-dhcp:atf_prefix`
时直接拒绝（fail-closed），防止把空转当绿。

**测试工具链（环境侧，非交付物）**：atf-0.19（GitHub jmmv/atf 官方发布版，
sha256 d1a5a8aa…）在真机上现编（`--enable-tools --disable-shared`）。ATF 自身的
`tools/generate-revision.sh` 直 exec 被 OHOS 拒绝，须以 `$(SHELL)` 前缀调用。

**结果统计（真机实战）**：13 程序 / 56 用例 / 0 失败 / 0 跳过。四个 tests 目录的
`atf-run` 退出码全为 0（`make check` RC=0）。逐用例原始输出（各目录
`atf-run-*.out`）随 reports/ 归档；原始构建/CI 日志（含 `conan-create-tests.log`）
因 PR 体积控制未随档（本地留存）。

## 遇到的问题与解决方案（真机实测）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报无法识别构建主机类型 | 2014 年代 config.guess 不认 HarmonyOS（UNAME_SYSTEM=HarmonyOS） | 补丁 `0001`/`0004`：加 HarmonyOS 探测分支，输出 `aarch64-unknown-linux-ohos` |
| 2 | `--host=aarch64-unknown-linux-ohos` 校验失败 | 同期 config.sub 无 `*-linux-ohos` 模式 | 补丁 `0002`/`0005`：加 ohos 模式 |
| 3 | configure 报 "cannot create a temporary directory in ." | HMDFS 用户卷拒收 mktemp 探测创建的 0700 目录（E011） | 补丁 `0003`/`0006`：探测 umask 077 → 022 |
| 4 | 捆绑 BIND 构建失败（configure 直 exec "Permission denied"）；CI 链中该子 configure 另死于 `configure: line 577: 0: Bad file descriptor` | ① OHOS 内核拒绝直接 exec 非签名解释器脚本；② autoconf 前导 `exec 7<&0`（configure 第 577 行）需要可用的 stdin，而构建链中该调用继承的 fd0 可处于关闭态 | 补丁 `0007`：bind/Makefile.in 加 `$(SHELL)` 前缀并给同一调用显式 `< /dev/null`（保持 stdin 恒开）；bind1/bind2 规则幂等，自动完成 BIND 四库的 configure/构建/安装 |
| 5 | make 败于 `install-sh: Permission denied`（创建 tests/.deps 等目录） | automake 生成的 Makefile 里 `MKDIR_P` 回退为 `.././install-sh -c -d`（脚本直 exec 被拒） | 配方 `_fix_mkdir_p()`：configure 后把全树 Makefile 的该行改写为 `mkdir -p` |
| 6 | configure 尾部报 `Something went wrong bootstrapping makefile fragments`（重配时暴露） | autoconf 2.70+ 的 "race-free mkdir -p" 探测只认 GNU mkdir（对 toybox 判定失败）→ `MKDIR_P` 回退 install-sh；config.status 的 depfiles bootstrap 经 make 间接调该帮助脚本，被直 exec 限制拒绝 | 配方 configure 前置 `MKDIR_P='mkdir -p'` 环境变量（`MKDIR_P` 是 AC_ARG_VAR，有值即跳过探测；config.status 与全部 Makefile 一致采用 `mkdir -p`）；`_fix_mkdir_p()` 保留为第二道防线 |
| 7 | `make check` 显示通过但零用例执行（假绿） | `tests/unittest.sh` 用 `type atf-run` 的输出经 `awk '{print $3}'` 提取工具路径；mksh（OHOS sh）的 `type` 输出为 "atf-run is a tracked alias for <path>"，`$3` 取到字母 "a" → `-x` 守卫判假 → 静默跳过全部套件 | 补丁 `0008`：改用 POSIX `command -v`（bash/mksh/dash 输出一致），守卫正常进入运行分支 |
| 8 | atf-run 报 `mkdtemp(3) failed: Read-only file system`（/tmp/atf-run.XXXXXX） | atf-run 的工作目录取 ATF 配置变量 `atf_workdir`（默认 /tmp，OHOS 上为只读挂载），不读 TMPDIR 环境变量 | 配方在 `make check` 前置 `ATF_WORKDIR=<可写目录>`（ATF 官方文档的环境覆盖名）；目录选择沿用仓库惯例 `_writable_tmpdir()` |
| 9 | 日志出现 `atf-report: ERROR: Could not create file -` 但 make check 判定通过 | `atf-report` 默认把报告写到 `-`＝`/dev/stdout`，OHOS 沙箱拒绝打开 /dev/stdout（源码 `open_outfile()` 实锤） | 不修（显示层）：判定以 atf-run 退出码为准（`unittest.sh` 末尾 `exit $status`）；完整 per-case 结果由 `atf-run-*.out` 原始输出归档佐证 |
| 10 | CI：`conan create` 在依赖图阶段报 `ERROR: Package type is 'library', but no 'shared' option declared` | Conan 2 对 `package_type = "library"` 强制要求声明 `shared` 选项；本包此前未声明（早期验证走的是设备手工作业链，未经过 conan 路径，CI 首次暴露） | 配方声明 `options = {"shared": [True, False]}`（默认 `False`，与 CI 模板一致），`validate()` 拒绝 `shared=True`（本包只产静态归档）；非 shared 的 `--enable-static --disable-shared` 由 `AutotoolsToolchain` 依 `shared=False` 自动发出（R26）——实测本树无 libtool，configure 仅告警忽略这两项，归档始终是 plain `ar` 产物 |
| 11 | （预修，未实发）配方 `unzip` 解包 `bind/bind.tar.gz` 时为相对路径 | `conan.tools.files` 对相对路径按进程 cwd 解析，不是配方目录——CI 的 cwd 与手测不同时找不到该文件 | 改为 `os.path.join(self.source_folder, "bind", "bind.tar.gz")` 绝对路径锚定（对照本仓库 `astronomical-almanac` 等样例惯例） |
| 12 | CI：test_package 阶段 CMakeDeps 报 `Library 'dhcp' not found in package`（包已构建成功，包内只有 4 个 BIND `.a`） | `package()` 从硬编码 `staging/usr/local` 取件，但 Conan `AutotoolsToolchain` 以 `--prefix=/` 配置（`--bindir=${prefix}/bin --sbindir=${prefix}/bin --libdir=${prefix}/lib`），`make install DESTDIR=<build>/staging` 直接落在 `staging/{bin,lib,include,etc}` → 三个 DHCP 库与四个可执行文件全部漏拷（手工链当时用默认 `/usr/local` 前缀，所以没暴露） | `package()` 改为直接 `make install DESTDIR=<package_folder>`（仓库惯例，同 babeltrace：固定前缀 `/` 让安装直接落 Conan 标准布局；`build()` 里的 staging 步骤删除）。另加 fail-closed 检查：7 个关键产物（4 可执行 + 3 库）缺任一即报错，不再让空安装静默出包 |

BIND 侧补丁 `0004`-`0007` 作用于 `bind/bind.tar.gz` 解包出的 `bind/bind-9.11.36`
（顶层补丁 `0001`-`0003` 作用于发布树本体），因此配方在应用补丁链之前先解包内层
tarball。

## 守护进程形态说明（daemon runtime）

dhcpd/dhclient/dhcrelay 是网络守护程序：真实流量验证需要绑定接口、开套接字、维护
租约库等，包 CI 环境不可提供（环境限制）。验证口径：

- 上游 ATF 套件覆盖服务器本体逻辑（dhcpd_unittests 等直接测协议状态机与配置解析）
- test_package 消费者侧：三守护程序 `--version` 实跑（证明可执行文件 + 三库 + 捆绑
  BIND 闭包在目标环境加载执行）+ omshell 加载运行 + 链接三库的 OMAPI API 消费者
  （omapi_init/dhcpctl_initialize 实调、dhcpctl_connect 连接路径实际执行）
- 库链接闭包完整性：libdhcp/libomapi/libdhcpctl 的未定义符号全部由随包 BIND 四库
  与系统库解析（`nm -u` 静态核算）
- `dhcpctl_connect` 负向断言口径（OHOS 实测）：连接关闭端口时非阻塞 `connect()`
  返回 EINPROGRESS，拒绝在 select 可写后由 `getsockopt(SO_ERROR)=ECONNREFUSED`
  取得，OMAPI dispatch 循环先消费该状态并拆除套接字，等待层取不到细码、如实上报
  `ISC_R_NOMORE`（同环境用包内 omshell 对同一端口复现同码），故测试白名单为
  {CONNREFUSED, NETUNREACH, NOMORE}；名字解析类早错（HOSTUNKNOWN 等）不在其内——
  连接确已到达套接字层
