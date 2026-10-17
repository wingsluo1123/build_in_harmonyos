# pwauth 2.3.11 HarmonyOS 适配笔记（A 类：前置适配）

## 范围与任务信息

- 任务类型：A 类（前置适配：W0 依赖检查 → 源码/构建系统分析 → 配方与 test_package → 本机验证 → 记录下一步真机命令）
- 任务记录：`/contrib` 任务 ID 由任务页给出（本阶段 issue 与 PR 解耦，未绑定 issue）
- taskBranch：`feat/pwauth-2.3.11`
- worktree：`D:\harmonyos\worktrees\pwauth`
- 允许改动范围：仅 `archives/p/pwauth/`

## W0 依赖检查（先查依赖，再动手）

pwauth 的构建与运行只需要一个外部依赖：PAM 实现（头文件 `security/pam_appl.h` + `libpam`）。

```
conan download "linux-pam/1.7.2" -r=ohpcd
→ recipe：linux-pam/1.7.2#79e562f180eb5683f20590ea0d65e378（本地 cache 已有）
→ binary：package_id 01d92cf349a0dd98ff915f4bd99a04430171517f，
  Conan 从 ohpcd 实际拉取 package revision 2f65a36646a4a1d1fc6e1261a3171e3f
  （日志：“Retrieving package ... from remote 'ohpcd'” → “Downloaded package revision”）
```

结论：**依赖已发布，无需拆新库**。

> 本机注意事项：这台 Windows 主机的 ohpcd 查询对「本地 cache 里没有的 ref」会返回
> `error:system acceleration policy not enabled`（例如 `pwauth/2.3.11`：确认尚未发布；
> 同一个报错也出现在不存在的包名上）。因此本机无法用远端「查不到」反推依赖缺失，
> W0 结论以上面的真实 package 拉取记录 + main 中的下游适配为依据；
> 正式判定由真机/CI 的 L0i（R36）完成。

- `linux-pam/1.7.2` 已在本仓 `archives/l/linux-pam/1.7.2` 适配（issue 1765），
  OHOS 侧已真机验证 `L0/L1/L4/L5 pass`；
- 下游 `pam-wrapper/1.1.8`（`requires("linux-pam/1.7.2")`）也已在真机通过，
  说明该依赖的 recipe、binary、头文件与 `-ldl` 链接在 OHOS 上可用。

其他依赖：无。构建工具只需要 `make`（OHOS worker 自带）。

## 源码分析

- 上游仓库：`https://github.com/phokz/pwauth`（Google Code 迁移镜像）
- 上游 2.3.11 发布包：`pwauth_2.3.11.orig.tar.gz`，23 974 字节，
  sha256 `3c6ab789d6ec92984954b4217418781508df393639adc32514d8491d8825fa22`
- 源码结构：`main.c`、`auth_*.c`（按口令库类型各一份 `check_auth`）、`fail_log.c`、
  `lastlog.c`、`nologin.c`、`snooze.c`、`config.h`、`pwauth.h`、`Makefile`
- 构建系统：**纯 Makefile**，没有 `configure`/`Makefile.in`/CMake/Meson
  - `Makefile` 里写死 `CC=gcc`、`LIB= -lcrypt`、`LOCALFLAGS= -g`
  - 没有 `install` 目标；除 `pwauth` 外还有独立的 `checkfaillog` 目标（默认不构建）
  - 没有 `check`/`test` 目标 → **上游自动化测试数为 0**
- 认证后端由 `config.h` 的宏选择：`SHADOW_NONE` / `SHADOW_BSD` / `SHADOW_SUN` /
  `SHADOW_JFH` / `SHADOW_MDW` / `SHADOW_AIX` / `SHADOW_HPUX` / `PAM` /
  `LOGIN_CONF_OPENBSD` / `AUTHENTICATE_AIX`，各后端在 `auth_*.c` 中用 `#ifdef` 隔离
- 程序接口：从 stdin 读 `login\npassword\n`，结果只通过退出码表达
  （`0` 成功、`1` 未知用户、`2` 口令错误、`3` uid 低于 `MIN_UNIX_UID`、
  `50` 调用者 uid 不允许、`51` 参数/输入错误、`52` 内部错误、`53` 读不到口令库）

### 源码可移植性问题（本包需要处理的）

| 位置 | 问题 | 处理 |
| --- | --- | --- |
| `config.h` 默认值 | 默认 `SHADOW_SUN` 走 `getspnam()`；OHOS 的 linux-pam 适配记录显示 `getspnam()` 未声明，musl 环境也没有 glibc 影子口令接口 | 改为 PAM 后端（与 Debian 打包一致） |
| `config.h` 默认值 | 默认打开 `UNIX_LASTLOG`、`HAVE_LASTLOG_H`、`NOLOGIN_FILE`、`CHECK_*_EXPIRATION`、`SLEEP_LOCK`、`SERVER_UIDS` | 按 PAM 后端语义关闭，见下方“配置决策” |
| `main.c:47` | `main(int argc, char **argv)` 省略返回类型（C99 起为隐式 int，Clang 16 起默认报错） | 补 `int` |
| `main.c:111` | `bzero()` 是遗留 BSD 接口，`pwauth.h` 只包含 `string.h`，OHOS 头文件下没有声明 | 改为等价的 `memset()` |

`bzero`/隐式 int 在 Clang 15 上只是 warning，但工具链会升级，且这两处是零风险的可移植性修复，
因此固化为补丁。

> 关于 R6（“只改源文件不改生成文件”）：pwauth 的 `config.h` **不是**构建生成物，
> 而是上游手工维护、随发布包分发的配置源文件（项目里没有 `configure`，也没有
> `config.h.in`），上游 `INSTALL` 文档要求使用者在编译前直接编辑它。
> 因此按 PAM 后端改写 `config.h` 是通过 `patches/` 修改源文件，符合 R6 的处置方式
> （Debian 打包也是这么做的）。
>
> 关于 R3（补丁生成方式）：本轮是 A 类前置适配，本机没有可用的 OHOS/Conan 构建环境，
> 无法运行 `refresh-patch --auto`（它需要真实构建上下文）。两个补丁是标准 unified diff
> （`--- a/<file>` / `+++ b/<file>`，`-p1` 语义），已用 Conan 实际使用的
> `patch_ng`（`strip=0`）在 `conan source` 解出的源码树上验证可干净应用；
> 若审核要求，可在真机构建后用 `refresh-patch --auto` 重新产出并替换。

## 配置决策（config.h）

选择 **PAM 后端**，与 Debian `pwauth 2.3.11-6` 的打包配置一致（Debian 的
`debian/patches/01-config-debian-1.patch` 同样启用 PAM、关闭 SHADOW_*）：

- `#define PAM`，取消 `#define SHADOW_SUN`
  （两者同时定义会让 `auth_sun.c` 与 `auth_pam.c` 重复定义 `check_auth`，链接失败）
- 关闭 `UNIX_LASTLOG` / `HAVE_LASTLOG_H`：lastlog 是 glibc/BSD 的 `/var/adm/lastlog`
  索引文件，PAM 模式下上游也建议关闭
- 关闭 `NOLOGIN_FILE` / `MIN_NOLOGIN_UID`：nologin 语义交给 PAM
- 关闭 `CHECK_LOGIN_EXPIRATION` / `CHECK_PASSWORD_EXPIRATION`：账号/口令过期交给 PAM
- 取消 `SERVER_UIDS 30`：不写死调用者 uid，改用安装权限约束（上游文档给出的第二种方案；
  Debian 同样注释掉该项，并以 `04755 root:www-data` 安装）
- `MIN_UNIX_UID` 500 → 100（沿用 Debian 取值，避免 OHOS 普通用户 uid 落在阈值以下）
- 关闭 `SLEEP_LOCK "/var/run/pwauth.lock"`：失败序列化睡眠锁依赖可写的 `/var/run`，
  OHOS 上不可靠，且属于限速策略而非认证必需

## 构建方案

- 编译器与标志来自 Conan：`tools.build:compiler_executables.c` + `AutotoolsToolchain`
  的 `cflags/defines`（R33：不使用裸 `${CC}`/`${CFLAGS}`）
- 上游 Makefile 自己赋值 `CC/CFLAGS/LIB`，makefile 赋值会覆盖环境变量，
  因此这些值在 **make 命令行**上传入（命令行变量优先级最高）：
  ```
  make -j1 CC=<clang> CFLAGS="<toolchain flags> -I<linux-pam>/include" \
       LIB="-L<linux-pam>/lib -Wl,-rpath,<linux-pam>/lib -lpam -ldl"
  ```
- `-lpam` 来自 `linux-pam` 包，`-ldl` 对应其 `pam` 组件声明的 `system_libs=["dl"]`
- 额外加 `-Wl,-rpath,<linux-pam>/lib`，让安装后的 `bin/pwauth` 不依赖
  `conanrun` 环境也能找到 `libpam.so.0`
- 不修改 Makefile（少一个补丁）：上游没有 `install` 目标，recipe 在 `package()` 中
  直接把 `pwauth` 拷进 `bin/`（R38 工具包）
- `checkfaillog` / `unixgroup` 不构建、不打包（PAM 后端下无意义；Debian 也在打包时删除）

## 产物清单

```
archives/p/pwauth/
  commands.json                                  # R38：软件级命令行声明
  README.md                                      # 软件级说明（ARCHIVE-SPEC §2.1）
  manifest.yaml                                  # 软件级元数据 + 版本索引
  2.3.11/
    conanfile.py
    conandata.yml
    manifest.yaml
    notes.md
    patches/0001-config.h-ohos-defaults.patch
    patches/0002-main.c-ohos-portability.patch
    patches/0003-auth-pam.c-ohos-test-confdir.patch
    test_package/conanfile.py
    test_package/MANIFEST.yml
    test_package/test.sh
    test_package/test_consumer.c
    reports/W0-and-source-analysis.md
```

## 本机验证（已完成）

1. 源码校验：主源与清华镜像分别下载，文件大小 23 974 字节、sha256 完全一致
   （镜像等价性有据，T11.2）。
2. **Conan 真实取源**：在隔离 `CONAN_HOME` 下执行 `conan source`，
   Conan 按 `conandata.yml` 从主源下载并**校验 sha256 通过**，且 `strip_root=True`
   后 `config.h`/`main.c`/`Makefile` 直接位于源码根目录（与补丁的 `a/config.h` 路径一致）。
3. 补丁验证：用 `patch_ng`（Conan `apply_conandata_patches()` 的实际实现，
   `strip=0` + `a/` 前缀自动剥离）在 Conan 解出的源码树上应用两个补丁，均 `APPLY OK`；
   随后脚本核对 `config.h` 的 8 处宏与 `main.c` 的 `int main` / `memset` 全部符合预期。
4. 语法校验：`python -m py_compile conanfile.py test_package/conanfile.py` 通过；
   新文件均为 LF、无 BOM（代码规范 §21）。
5. 元数据校验：`conandata.yml`、`manifest.yaml`、`test_package/MANIFEST.yml` 可解析；
   `commands.json` 为合法 JSON 且 `name/type/versions` 满足 CI L0k 要求。
6. CI L0 门禁静态复核（按 `ci/conan/build_and_test.sh` 的判据逐条对照）：
   L0a `test_package/` ✓、L0b `test_package/conanfile.py` ✓、L0c `test.sh` ✓、
   L0d `def test` + `self.run` ✓、L0e `MANIFEST.yml` ✓、L0f patches 列表格式 ✓、
   L0g 无硬编码 remote ✓、L0h `self.run` 中无 `${CC}/${CFLAGS}` ✓、
   L0i 依赖已发布（见 W0）✓、L0k `commands.json` ✓、
   L0m `archives/p/pwauth/2.3.11` 与 `version = "2.3.11"` 一致 ✓、
   L0n 分支名 `feat/pwauth-2.3.11` 含 `pwauth-2.3.11` ✓。

### 本机未能执行的验证（如实记录）

- `conan create`：本机 conan 是官方 2.29.1（`settings.yml` 无 OHOS 枚举），
  无法加载 `ci/conan/profiles/ohos-aarch64`，也没有 OHOS 工具链，
  因此无法在本机完成真正的编译/测试验证。
- **本地 Linux 编译验证也未能完成**（尝试过两条路，均不可行，记录以便后续复用）：
  - WSL `Ubuntu-22.04` 发行版启动失败：`ERROR_PATH_NOT_FOUND`（ext4.vhdx 缺失），无法使用；
  - WSL `podman-machine-default`（Fedora 42 container image）可用但**没有 gcc/make/pam-devel**，
    且其 dnf 被 `copr:containers-podman-*` 仓库 404 卡死；禁用 copr 后 Fedora 42
    的官方源在清华镜像上已 404（发行版过旧），无法安装编译器与 PAM 开发头文件。
  结论：本机没有可用的 Linux + libpam 开发环境，编译验证留给真机完成（见下节）。

## OHOS 真机验证（单包 shadow CI，已完成）

真机：HarmonyOS PC aarch64（`uname -a` 显示 HongMeng Kernel 1.12.0 aarch64）。
隔离 job：`~/ohos-users/codex-pwauth/pwauth-2.3.11-r1`（独立 repo 快照 + 独立 `CONAN_HOME`），
经 `ohos-test-runner.sh` 持 `device-global.lock` 执行（wait 0s，全程约 10 秒）。

```
run_dir  : /storage/Users/currentUser/ohos-test-runs/codex-pwauth-pwauth-pwauth-2.3.11-r1-ci-20261015-195200-48243
command  : CI_PACKAGES="archives/p/pwauth/2.3.11" zsh ci/conan/build_and_test.sh
exit_code: 0

L0_RESULT=pass: all checks passed
    含 [ok] dependency in registry: linux-pam/1.7.2
       [ok] version not in registry yet (first publish)
       [ok] commands.json valid (type=tool)
       [ok] L0m: directory structure valid
L1_RESULT=pass: test_package executed
    [ok] L1a: test_package was executed by conan create
    [ok] L1e: Negative test confirmed — test genuinely depends on pwauth
L2_RESULT=skip: pwauth version/help failed（上游无 --version/--help，CI 中非阻塞）
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
Build Summary: Total 1 / Success 1 / Failed 0（Pass rate 100%）
```

test_package 实测输出（真机 stdout 逐字摘录，7/7 PASS）：

```
PASS 1: end-to-end consumer flow: PAM authentication succeeded -> exit 0
PASS 2: end-to-end consumer flow: broken PAM service -> exit 1 (documented non-zero status)
PASS 3: default PAM configuration (no private service dir) -> exit 52
PASS 4: empty stdin -> exit 51 (STATUS_INT_ARGS)
PASS 5: unknown login -> exit 1 (STATUS_UNKNOWN)
PASS 6: existing login 'root' + wrong password -> exit 3 (documented non-zero status)
PASS 7: binary declares a libpam shared-library dependency
test pwauth 2.3.11: 7/7 checks PASS
```

退出码含义（人工注解，非脚本输出）：`0` = 端到端成功链路（私有 PAM 服务用
`pam_permit.so`，`pam_authenticate`/`pam_acct_mgmt` 均为 0）；`1` = 服务模块无法加载
或 `getpwnam()` 失败；`52` = 默认链路落到系统 PAM，设备没有 `/etc/pam.d/pwauth`，
`pam_start` 失败后 `pam_end` 报错；`51` = stdin 读不到 login/password；
`3` = STATUS_BLOCKED，登录名 `root` 的 uid 0 低于 `MIN_UNIX_UID=100`。失败链路的断言
写的是“非 0 且属于 `pwauth.h` 状态码集合”（具体值随设备 PAM 配置与调用者 uid 变化），
成功链路则精确断言退出码为 0。

构建与产物证据：

```
pwauth/2.3.11: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.version=15 build_type=Release
pwauth/2.3.11: RUN: make -j1 CC="/storage/Users/currentUser/usr/local/bin/clang"
  CFLAGS="-O3 -DNDEBUG -I<linux-pam pkg>/include"
  LIB="-L<linux-pam pkg>/lib -Wl,-rpath,<linux-pam pkg>/lib -lpam -ldl"
pwauth/2.3.11: Apply patch (portability): 0001 config.h OHOS PAM defaults
pwauth/2.3.11: Apply patch (portability): 0002 main.c OHOS portability
Package pwauth/2.3.11:0cbc32c0e0af33cb27a49e222166cdc8f64abc0f  →  bin/pwauth (23 040 B, sha256 8a26468d…)
llvm-readobj --dynamic-table bin/pwauth:
  NEEDED Shared library: [libpam.so.0]
  NEEDED Shared library: [libc.so]
```

关键结论：`libpam.so.0` 在 OHOS 上可加载，`pam_start()` 会被真正调用
（非 root 用户走 PAM 分支并返回 52，因为设备没有 `/etc/pam.d/pwauth`），
说明这不是“只编译不运行”的空壳适配。

### 真机环境侧适配（不随仓库提交）

1. 仓库 profile `ci/conan/profiles/ohos-aarch64` 指向 `/data/service/hnp/bin/clang`，
   但本机该目录只有 git 工具链，DevBox 编译器在 `~/usr/local/bin`（clang 是 clang-15
   wrapper，带 OHOS sysroot / lld / `-Wl,--code-sign`）。因此为本次验证新增了
   `ci/conan/profiles/ohos-aarch64-local`（仅存在于真机快照）并用
   `CONAN_PROFILE=ohos-aarch64-local` 运行。
2. 共享 `~/ohpc-ci-shadow/python-user` 里的 conan 是官方版（`default_settings.py`
   无 OHOS），会让 `conan create` 报 `Invalid setting 'OHOS'`；改用早期 shadow 运行
   安装的 OHOS 版 conan 基座（`~/ohpc-ci-shadow/mr11440-20260924/python-user`）
   搭配本 job 独立 `CONAN_HOME`（其中 `settings.yml` 含 OHOS）。
3. CI 的源码预下载步骤需要 `curl`，runner 默认 PATH 里没有，已在 `--path` 中补 `/usr/bin`。

以上三条都是镜像/设备差异，均未改动仓库基础设施文件。

## 端到端消费者用例（人工检视 rule12 整改）

首轮 PR 的人工检视结论是 `VERDICT=FAIL`，唯一不通过项是 **rule12 鸿蒙特有测试**：
原有 5 项都是纯断言，缺少“真正跑通核心流程”的端到端消费者用例。整改内容：

1. **新增消费者程序** `test_package/test_consumer.c`：按 Apache
   `mod_authnz_external` 的方式使用 pwauth —— `fork`/`exec` 已安装的二进制，把
   `"<login>\n<password>\n"` 写进它的 stdin，并以退出码作为认证结果。
2. **新增补丁 0003** `0003-auth-pam.c-ohos-test-confdir.patch`：`auth_pam.c` 在
   环境变量 `PWAUTH_PAM_CONFDIR` 存在时改用 `pam_start_confdir()` 指向私有 PAM 服务
   目录。设备没有 `/etc/pam.d`，没有这个钩子就无法在测试里跑出“认证成功”。
   安全约束：该钩子**只在 `getuid() == geteuid()`（非提权进程）时生效**，setuid
   安装始终使用系统 PAM 配置，非特权调用者无法把服务目录指向自定义的宽松服务；
   该 API 属 Linux-PAM ≥1.3 扩展，其它 PAM 实现（Solaris/OpenPAM）上会被编译掉。
3. **test.sh 编排三条端到端链路**（用 linux-pam 包的 `pam_permit.so` 构造服务文件）：
   - 成功链路：私有服务 `auth/account sufficient pam_permit.so` → 认证+账号检查全部
     通过 → **pwauth 退出码 0**（真正跑通的成功认证）；
   - 失败链路：服务引用的模块不存在 → 退出码 1（合法非零状态码）；
   - 默认链路：不设 `PWAUTH_PAM_CONFDIR` → 落到系统 PAM（设备无 `/etc/pam.d/pwauth`）
     → 退出码 52，证明钩子不改变默认行为。
4. 其余检查保留为失败路径断言（空输入 51、未知用户 1、错误口令的合法非零状态码）
   与 `libpam` 动态依赖校验，共 **7 项检查全部通过**。

实现细节：真机 `/tmp` 只读，`test.sh` 把 `TMPDIR` 指向自建 `WORK_DIR`，消费者程序用
`clang`（未设 `CC` 时的回退）在测试内编译；`PWAUTH_TEST_PAM_MODULE` 由
`test_package/conanfile.py` 从 `linux-pam` 包路径推导，缺失时回退到该包导出的
`LINUX_PAM_MODULE_DIR`。

## 风险与后续项

1. **正向认证未做断言**：pwauth 成功认证需要 `/etc/pam.d/pwauth` 服务与真实口令；
   test_package 不改设备 `/etc`，因此只断言输入校验与失败路径。
   OHOS 的 `linux-pam` 包目前只构建了 `pam_permit`，真实口令认证需要后续单独适配
   `pam_unix` 等模块。
2. **`pam_start()` 真机行为已实测**：设备没有 `/etc/pam.d/pwauth`，非 root 用户
   （`system`，uid 1000）返回 `52`（STATUS_INT_ERR，即 `pam_end()` 失败路径），
   而 `root` 因 `MIN_UNIX_UID=100` 在 `auth_pam.c` 的 uid 门限处返回 `3`
   （STATUS_BLOCKED）。两者都是 `pwauth.h` 的合法状态码，断言不会误判。
3. **L2 冒烟步骤**：CI 的 L2 用 `--version/--help` 探测命令行工具，pwauth 不支持这两个
   参数（它只读 stdin），真机实测 L2 为 `skip: pwauth version/help failed`；
   该步骤在 CI 中明确是非阻塞的，真实 CLI 验证由 test_package（L1，7/7）承担。
4. **签名**：`bin/pwauth` 是 ELF 可执行文件；本次真机运行未出现签名/执行被拒，
   因为 profile 中的 clang wrapper 自带 `-Wl,--code-sign`。若后续换用不带签名的
   工具链，需要按仓库做法在 package 阶段调用 `binary-sign-tool`。
5. **官方 CI 仍需最终确认**：本次是 SSH 真机上的 shadow CI（等价复刻公开构建逻辑），
   不替代 GitCode/GitCode 流水线；PR 创建后仍需以官方流水线结果为准。

## 下一步命令

真机单包验证（本次已通过，可在新设备/新 commit 上复用）：

```sh
CONAN_PROFILE=ohos-aarch64-local CI_PACKAGES="archives/p/pwauth/2.3.11" \
  zsh ci/conan/build_and_test.sh
# 或 shadow CI 运行器
/path/to/run-ohos-shadow-ci.sh archives/p/pwauth/2.3.11
```

正式流程（配方已通过真机验证）：

```sh
git push -u origin feat/pwauth-2.3.11     # 建 PR 前先推送分支
# 然后按 SKILL 流程走 finish / submit（W3 本地编译门禁 + W4 Pre-PR 审计）
```

通过标准：build 日志只发现目标包、`Build Summary Total: 1`、L0/L1 pass、
L2 有证据地 skip、L4 warn 已判读、L5 中 `bin/pwauth` 真实存在。

## W4 Pre-PR 独立审计

按 `templates/audit-prompt.md` 由独立子任务（上下文隔离）执行，输入为
`pre_pr_audit.py generate` 生成的审计包，结论：

- `verdict = pass`，`P0 = 0`、`P1 = 0`、`P2 = 3`、`P3 = 7`
- 审计独立复核（不只读文件）：上游 `pwauth.h` 的状态码集合与 test.sh 断言一致；
  Debian 签名 `.dsc` 记录的 sha256/字节数与本地 tar 包实测一致；
  两个补丁 `git apply -p1` 到上游 orig 源树干净应用且结果与文档一致；
  提交仅含一个配方、未触碰框架文件
- 可当场处理的 P2/P3 已修复：真机 test_package 输出改为**逐字摘录**并把退出码含义
  单独放 `status_code_notes`（人工注解）；补齐软件级 `README.md` 与 `manifest.yaml`；
  补丁改名 `0001-config.h-ohos-defaults.patch` / `0002-main.c-ohos-portability.patch`；
  `upstream_check_command` 置空；`_find_shell()` 改为 bash 优先；检查 3/4 注释不再
  声称必然进入 PAM
- 保留的偏差（已在 PR 说明中声明）：补丁为标准 unified diff 而非
  `refresh-patch --auto` 产出（本机无 OHOS 构建环境）

## 交接信息

- 分支：`feat/pwauth-2.3.11`（基于 `main` = `b544378a4e`），最新 commit 见该分支 HEAD
- 提交内容仅 `archives/p/pwauth/**`；真机验证后只在 `manifest.yaml`/`notes.md`/`reports/`
  补写了证据（CI 只读 conanfile.py / conandata.yml / test_package / patches，
  这 8 个输入文件的 sha256 与真机快照逐一相同，见 manifest.yaml 的
  `verification.ohos_real_device`）
- 当前状态：真机 shadow CI 单包通过（L0/L1/L4/L5 pass，L2 skip，test_package 7/7）；
  W4 审计 pass；已提交 PR #15995，并按人工检视 rule12 完成端到端用例整改
- 典型运行时长：约 10 秒（conan create + test_package），适合插在重任务之间
