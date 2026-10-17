# pwauth 2.3.11 W0 与源码分析报告

任务类型：A 类（前置适配）
分支：`feat/pwauth-2.3.11`
worktree：`D:\harmonyos\worktrees\pwauth`
改动范围：`archives/p/pwauth/**`

## 1. W0 依赖检查

| 依赖 | 类型 | 制品仓状态 | 证据 |
| --- | --- | --- | --- |
| `linux-pam/1.7.2` | 构建 + 运行（PAM 头文件与 `libpam`） | 已发布（recipe + binary） | `conan download "linux-pam/1.7.2" -r=ohpcd`：Conan 从 ohpcd 实际拉取 package `01d92cf3…`（package revision `2f65a366…`） |

结论：依赖链完整，不需要拆新的依赖库 PR。上游 pwauth 没有其他必需依赖
（`-lcrypt` 只属于 `SHADOW_*` 后端；PAM 后端不需要它）。

本机查询限制（如实记录）：这台 Windows 主机对「本地 cache 中不存在的 ref」查询 ohpcd 会返回
`error:system acceleration policy not enabled`（不存在的包名同样如此），因此本机**不能**
用「查不到」判定依赖缺失；W0 结论依据上面的真实 package 拉取记录，正式门禁由真机/CI 的
L0i（R36）执行。

旁证：`archives/l/linux-pam/1.7.2`（issue 1765）与 `archives/p/pam-wrapper/1.1.8`
均已在本仓 main 中，且 pam-wrapper 已用同一条 `linux-pam` 依赖链在真机通过
`L0/L1/L4/L5`，说明该依赖在 OHOS 上可链接、可加载。

## 2. 源码与构建系统分析

- 上游：`https://github.com/phokz/pwauth`（原 Google Code 项目 `code.google.com/p/pwauth`）
- 版本：2.3.11（`CHANGES` 顶部条目与 tar 包目录名一致）
- 构建系统：纯 Makefile（无 `configure`、无 `Makefile.in`、无 CMake/Meson）
  - `Makefile` 写死 `CC=gcc` / `LIB= -lcrypt` / `LOCALFLAGS= -g`
  - 目标：`pwauth`（默认）、`checkfaillog`、`clean`、`distclean`、`pwauth.tar`
  - **无 `install` 目标，无 `check`/`test` 目标** → 上游自动化测试数 0
- 认证后端在 `config.h` 中选择，各后端实现分散在 `auth_*.c`，用 `#ifdef` 隔离：
  `SHADOW_SUN`（`getspnam()`）、`SHADOW_BSD`/`SHADOW_NONE`（`getpwnam()` + `crypt()`）、
  `SHADOW_JFH`、`SHADOW_MDW`、`SHADOW_AIX`、`SHADOW_HPUX`、`PAM`、`LOGIN_CONF_OPENBSD`、
  `AUTHENTICATE_AIX`
- 接口形态：stdin 读 `login\npassword\n`，只以退出码报告结果（`pwauth.h` 的 `STATUS_*`）

### 2.1 为什么选 PAM 后端

1. OHOS 侧的口径：`archives/l/linux-pam/1.7.2/notes.md` 记录 OHOS 暴露 `shadow.h`
   但**未声明 `getspnam()/getspnam_r()`**，`SHADOW_SUN` 后端无法链接；
   `SHADOW_SUN` 还需要 `-lcrypt`，OHOS 上也没有对应的独立库。
2. 上游与发行版口径：Debian 的 `pwauth` 打包同样是 PAM 后端
   （`debian/patches/01-config-debian-1.patch` 启用 `PAM`、注释掉全部 `SHADOW_*`，
   `debian/patches/03-Makefile-debian-1.patch` 把 `LIB` 改成 `-lpam`），
   `debian/control` 的 `Build-Depends` 只有 `libpam0g-dev`。
3. 依赖可用性：`linux-pam/1.7.2` 已适配并发布（见 W0）。

### 2.2 需要处理的源码可移植性点

- `main.c` 的 `main()` 省略返回类型：C99 起属于隐式 `int`，Clang 15 是 warning，
  Clang 16 起默认报错 → 补 `int`。
- `main.c` 使用 `bzero()`：遗留 BSD 接口，`pwauth.h` 只包含 `string.h`，
  默认特性宏下没有声明 → 改成等价且标准的 `memset()`。
- `config.h` 的默认值面向作者当年的 RedHat 6.1（`SHADOW_SUN` + lastlog + nologin +
  过期检查 + `SERVER_UIDS 30` + `/var/run` 睡眠锁）→ 按 PAM 语义重设，详见
  `notes.md`「配置决策」一节。

## 3. 本包设计

- `package_type = "application"`，产物只有 `bin/pwauth`
- `requires("linux-pam/1.7.2")`
- 编译：`make -j1 CC=<conf 中的 clang> CFLAGS="<AutotoolsToolchain flags> -I<pam>/include"
  LIB="-L<pam>/lib -Wl,-rpath,<pam>/lib -lpam -ldl"`
  - 上游 Makefile 会覆盖环境变量，所以参数走 make 命令行变量（R33 + upstream 事实）
  - `-ldl` 来自 linux-pam `pam` 组件声明的 `system_libs`
  - rpath 让安装后的二进制脱离 `conanrun` 也能加载 `libpam.so.0`
- 打包：上游无 `install` 目标 → `package()` 直接拷贝二进制到 `bin/`
- 不打包 `checkfaillog`、`unixgroup`（PAM 后端下无意义；Debian 同样删除）
- 补丁三个：`config.h`（PAM 默认值）、`main.c`（可移植性）、`auth_pam.c`
  （`PWAUTH_PAM_CONFDIR` 端到端测试钩子，仅在非提权进程生效）；不改 Makefile

## 4. test_package 设计

上游没有可迁移的自动化测试，因此 test_package 以消费者视角补全验证，核心是**完整
的端到端用例**（人工检视 rule12 要求，不能只有纯断言）：

消费者程序 `test_consumer.c` 编译后按 Apache `mod_authnz_external` 的方式使用
pwauth：`fork`/`exec` 已安装二进制 → stdin 写入 `"<login>\n<password>\n"` → 以退出码
作为认证结果。`test.sh` 用 linux-pam 包里的 `pam_permit.so` 构造私有 PAM 服务目录
（依赖补丁 0003 的 `PWAUTH_PAM_CONFDIR`），于是可以验证真正跑通的链路：

| # | 检查 | 依据 / 真机实测 |
| --- | --- | --- |
| 1 | 端到端成功链路：私有 PAM 服务（`pam_permit.so`）→ 认证成功 | `pam_authenticate`/`pam_acct_mgmt` 成功 → pwauth 退出码 `0`（实测 0） |
| 2 | 端到端失败链路：服务模块无法加载 | PAM 模块打开失败 → 合法非零状态码（实测 `1`） |
| 3 | 端到端默认链路：不设私有服务目录 → 系统 PAM | 设备无 `/etc/pam.d/pwauth` → `pam_start` 失败（实测 `52`），证明钩子不改变默认行为 |
| 4 | 空 stdin → 退出码 51 | `main.c`：`fgets()` 失败 → `exit(STATUS_INT_ARGS)` |
| 5 | 未知用户 → 退出码 1 | `auth_pam.c`：`MIN_UNIX_UID` 定义 ⇒ `NEED_UID` ⇒ `getpwnam()` 失败 → `STATUS_UNKNOWN` |
| 6 | 当前用户 + 错误口令 → 合法非零状态码 | PAM 路径或 uid 门限，取值落在 `pwauth.h` 的 `STATUS_*` 集合内（实测 `3`） |
| 7 | `llvm-readobj --dynamic-table` 中出现 `libpam` | 证明真的链接了 PAM，而不是空壳构建 |

补丁 0003 的安全约束：钩子只在 `getuid() == geteuid()`（非提权）时生效，setuid 安装
始终走系统 PAM 配置；`pam_start_confdir()` 是 Linux-PAM ≥1.3 扩展，其它 PAM 实现上
该分支会被编译掉，默认行为不变。仍不做真实系统口令认证：OHOS 的 `linux-pam` 目前只
构建 `pam_permit`，真实口令认证需要后续单独适配 `pam_unix` 等模块。

## 5. 本机验证结果

| 项 | 结果 |
| --- | --- |
| 源码 sha256（主源 + 清华镜像） | `3c6ab789d6ec92984954b4217418781508df393639adc32514d8491d8825fa22`，两者一致 |
| 隔离 `CONAN_HOME` 下 `conan source` | 从主源下载成功并通过 sha256 校验，`strip_root` 后源码位于根目录 |
| `patch_ng`（Conan 实际补丁实现，strip=0）应用三个补丁 | APPLY OK（在 Conan 解出的源码树上） |
| 补丁结果核对（`config.h` 8 处宏、`main.c` `int main`/`memset`） | 全部符合预期 |
| `py_compile`（conanfile + test_package/conanfile） | 通过 |
| YAML / JSON 元数据解析、LF/BOM 检查 | 通过 |
| CI L0 门禁静态复核（L0a–L0h、L0k、L0m、L0n） | 通过（L0i 依赖已发布；L0j 该版本尚未发布，符合首次适配） |
| `conan create`（本机） | 未执行：本机 conan 2.29.1 为官方版，`settings.yml` 无 OHOS 枚举，且无 OHOS 工具链 |
| 本机 Linux 编译校验 | 未完成：WSL `Ubuntu-22.04` 的 `ext4.vhdx` 缺失无法启动；WSL `podman-machine`（Fedora 42 container image）无 gcc/pam-devel，且 Fedora 42 源已 404，无法搭 Linux+libpam 环境 |
| **OHOS 真机 shadow CI 单包** | **通过**：run `codex-pwauth-pwauth-pwauth-2.3.11-r1-ci-20261015-195200-48243`，exit 0；L0/L1/L4/L5 pass，L2 skip（非阻塞）；`Total 1 / Success 1 / Failed 0` |
| 真机 test_package | 7/7 PASS：端到端成功链路（私有 PAM 服务 + `pam_permit` → 退出码 0）、端到端失败链路（模块无法加载 → 1）、端到端默认链路（系统 PAM → 52）、空输入=51、未知用户=1、当前用户错误口令=3、二进制声明 `libpam` 依赖 |
| 真机产物 | `bin/pwauth` 23 040 B，sha256 `8a26468d…`，`NEEDED [libpam.so.0, libc.so]` |
| W4 Pre-PR 独立审计 | `verdict=pass`（P0=0，P1=0，P2=3，P3=7）；P2/P3 中可当场处理项已修复：真机输出改为逐字摘录、补齐软件级 `README.md`/`manifest.yaml`、补丁改名为 `0001-config.h-…`/`0002-main.c-…`、`upstream_check_command` 置空、`_find_shell` 改为 bash 优先 |

## 6. 合规性说明（面向 W4 审计）

- **R6（不改生成文件）**：`config.h` 是 pwauth 上游手工维护、随发布包分发的配置源文件
  （无 `configure`、无 `config.h.in`），`INSTALL` 要求编译前直接编辑它；
  本次通过 `patches/0001-config.h-ohos-defaults.patch` 修改源文件，符合 R6 的处置方式
  （Debian 打包同样如此）。
- **R3（补丁生成）**：A 类前置阶段本机无 OHOS 构建环境，无法运行 `refresh-patch --auto`；
  三个补丁均为标准 unified diff，已用 Conan 实际使用的 `patch_ng`（`strip=0`）验证可应用。
- **补丁 0003 的安全性**：`PWAUTH_PAM_CONFDIR` 只在 `getuid() == geteuid()` 时生效
  （setuid 安装不受影响），`pam_start_confdir()` 不存在时整个分支被编译掉，
  默认行为与上游一致；引入它是为了满足人工检视 rule12 对端到端消费者用例的要求。
- **R33**：编译参数来自 `tools.build:compiler_executables` 与 `AutotoolsToolchain`，
  `self.run()` 中不出现 `${CC}`/`${CFLAGS}`。
- **R34**：test_package 执行被测二进制并断言真实状态码，同时校验二进制链接了 `libpam`。
- **R38**：软件级 `commands.json` 已创建（`type=tool`）。
- **R39**：主源为 Debian 源码池的上游 `orig.tar.gz`（上游 Google Code 已下线、
  GitHub 镜像缺 2.3.11 标签），另附清华镜像并用 sha256 证明等价。
- **W2**：改动仅限 `archives/p/pwauth/**`。

## 7. 阻塞点

无阻塞：依赖已发布、补丁与配方已在真机 shadow CI 通过（L0/L1/L4/L5 pass）。
官方流水线（PR CI）仍需在推送分支后跑一次，作为最终口径。

## 8. 下一步命令

```sh
# 真机单包复验（本次已通过）
CONAN_PROFILE=ohos-aarch64-local CI_PACKAGES="archives/p/pwauth/2.3.11" \
  zsh ci/conan/build_and_test.sh
# 或 shadow CI 运行器
/path/to/run-ohos-shadow-ci.sh archives/p/pwauth/2.3.11

# 正式流程
git push -u origin feat/pwauth-2.3.11
```
