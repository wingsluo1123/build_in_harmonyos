# sispmctl 4.12 适配笔记

## 编译环境
- 构建系统: autotools（上游发布包自带预生成 configure + libtool）
- 编译日期: 2026-10-10
- 编译器: clang/clang++（/data/service/hnp/bin）
- 状态: built
- 目标平台: HarmonyOS PC (OHOS/aarch64)

## 软件简介
sispmctl 是控制 GEMBIRD (m)SiS-PM 系列 USB 电源插座（排插）的命令行工具，
随包安装 `sispmctl` CLI 与 `libsispmctl` 共享库，并附 Web 管理界面。

## 编译步骤（conan create 内部，真机执行）
1. `get()` 解压官方 sispmctl-4.12.tar.gz（SourceForge，sha256 见 conandata.yml）。
2. requirements: `libusb-compat/0.1.7`（提供 libusb-0.1 API：`usb.h` + `-lusb`）。
3. generate(): 用 AutotoolsToolchain 注入编译器/构建环境，并向 `PKG_CONFIG_PATH`
   前置一个手工编写的 `libusb.pc` shim（Version 0.1.12，Libs 同时带
   `-lusb` 与 `-lusb-1.0`）。
4. build(): 依次
   - patch config.guess/config.sub 识别 HarmonyOS（aarch64-unknown-linux-ohos）；
   - configure shebang 修正为 `#!/system/bin/sh`，并用 bash 直跑 configure
     （`./configure --prefix=/ --enable-static --disable-shared`）；
   - config.status umask 077→022；
   - 预建 src/.libs 等目录；
   - `make -j1 V=1`。
5. package(): `make install DESTDIR=$package_folder`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure `PKG_CHECK_MODULES(LIBUSB, libusb >= 0.1.11)` 报版本不符 | libusb-compat 生成/安装的 libusb.pc 版本为 0.1.7，不满足 >= 0.1.11 | generate() 手工编写 libusb.pc shim，Version 置为上游 libusb-0.1 API 版本 0.1.12（与 libusb-compat 自带 LIBUSB01_VERSION 一致） |
| 2 | configure 无法识别目标平台 | OHOS 不在 admin/config.guess、admin/config.sub 支持列表 | build() 内按仓库先例（aribb24）给 config.guess/config.sub 增加 aarch64-unknown-linux-ohos 识别 |
| 3 | OHOS /bin/sh(mksh) 执行 ELF/生成脚本不可靠 | 平台 shell 限制 | configure 用 bash 直跑，shebang 改 /system/bin/sh |
| 4 | libtool 产物未落盘/权限位错 | HMDFS umask 077 | config.status umask 077→022 + 预建 .libs/.deps 目录 |
| 5 | 静态链接传递链断裂 | sispmctl 直接 -lusb，缺 libusb-1.0 | pc shim 的 Libs 同时声明 -L{libusb-compat/lib} -lusb 与 -L{libusb-1.0/lib} -lusb-1.0 |

## 依赖版本
- libusb-compat/0.1.7（→ libusb/1.0.27）

## 上游测试审计
- **上游无测试套件**。审计依据：发布包无 tests/ 目录；configure.ac 无测试宏；
  Makefile.am 与 src/Makefile.am 均无 TESTS/check_PROGRAMS/check-local；
  `make -n check` 返回 "No rule to make target"。→ `upstream_tests_exist: false`
  （详见 test_package/MANIFEST.yml 的 upstream_test_audit）。

## 验证结果
- test_package 消费者测试（见 test_package/）：
  - `test_sispmctl.c`：链接 libsispmctl 真实调用 `plannif_reset()`、
    `pms2_schedule_to_buffer()`/`pms2_buffer_to_schedule()` 往返一致性；
  - 执行安装产物 `sispmctl -v`，校验版本串包含 "4.12" 且退出码 0。
- 真机预检通过率以 HMBS 真机日志为准（本笔记不计 PR 正文数字）。

## 注意事项
- sispmctl 的实际插座控制功能需要物理 GEMBIRD USB 设备，真机/CI 无此硬件，
  故消费者测试只覆盖纯库 API 与版本/帮助路径，不伪造硬件操作。
- 定制 svc 端口 / Web 界面为本工具附带功能，不影响核心编译适配。

## 2026-10-11 真机预检失败（compile 阶段）诊断记录
- 现象：preflight.sh[331] 报 `can't fork - try again`（fork 返回 EAGAIN），发生在
  conan create 编译阶段由 shell 派生子进程时；日志中无任何 gcc/clang/configure/链接/源码
  错误输出。
- 判定：环境型资源耗尽故障（fork EAGAIN = 进程数/内存/PID 表瞬时不足），非配方/代码问题。
  依据：
  1) 本包此前已成功构建（manifest.yaml status: built；真机编译成功过）；
  2) 失败点在 shell 调 conan create 时 fork 失败，尚未进入真实编译，无编译期告警；
  3) 配方本身为轻量构建（`make -j1`、几个小 C 文件、无并行 fork），不构成资源压力来源。
- 处理：按守则对环境故障不做代码改动，保持工作树原样，等待真机资源恢复后由 HMBS 复跑预检。

## 2026-10-11 真机预检失败（compile 阶段）——E386 getcwd 修复
- 现象（focus round）：configure 全部子 shell 刷屏 'job-working-directory: error
  retrieving current directory: getcwd: cannot access parent directories'，最终
  'configure: error: working directory cannot be determined'，conan create 退出码 1。
  HMBS 平台诊断：shell_getcwd——HNP bash 无法访问当前 HMFS/HMDFS 工作目录；要求使用
  HMBS 注入的 SHELL=/bin/sh 与 CONFIG_SHELL=/bin/sh，不要硬编码 /data/service/hnp/bin/bash。
- 根因（E386，仓库 knowledge 先例 classads/hamlib/remctl）：profile [buildenv] 注入
  CONFIG_SHELL=/data/service/hnp/bin/bash，该 OHOS 系统 bash 对 HMFS 目录 getcwd 返回
  ENOTSUP/EINVAL；configure 采用 CONFIG_SHELL 后 config.guess/sub/conftest 全链路 getcwd
  失败。配方的 os.environ 读取在 build() 阶段非 run 时点的终值，故此前读到的 CONFIG_SHELL
  与 self.run 时 conanbuild.sh 重新导出的值不一致（remctl 的 save-order 陷阱）。
- 修法（与本轮实际一致）：conanfile.py build()/package() 与 test_package 全部去掉
  CONFIG_SHELL→bash 的解析，改为在内联 USER=root
SSH_CLIENT=119.181.45.103 2237 22
AGENT=1
XDG_SESSION_TYPE=tty
SHLVL=0
HOME=/root
OLDPWD=/data/hmbs/wa/tasks/sispmctl-4.12
DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/0/bus
LOGNAME=root
_=/usr/bin/nohup
XDG_SESSION_CLASS=user
XDG_SESSION_ID=12277
OPENCODE=1
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin
XDG_RUNTIME_DIR=/run/user/0
LANG=C.UTF-8
OPENCODE_PID=3235223
XDG_DATA_HOME=/data/opencode-home
SHELL=/bin/sh
PWD=/data/hmbs/wa/tasks/sispmctl-4.12/archives/s/sispmctl/4.12
SSH_CONNECTION=119.181.45.103 2237 172.16.0.12 22 前缀 +  执行 configure/config.status/make/make install/
  测试命令，就近覆盖 buildenv 在 self.run 时点注入的 bash 值；删除未用的 shutil import。
- 保持未提交，等待 HMBS 真机复跑预检验证。

## 2026-10-11 真机预检失败（compile 阶段）——config.sub 未识别 linux-ohos
- 现象（focus round）：config.guess 已正确输出 `aarch64-unknown-linux-ohos`，但
  configure 调 `./admin/config.sub aarch64-unknown-linux-ohos` 报
  `Invalid configuration ...: Kernel 'linux' not known to work with OS 'ohos'`，
  conan create 退出码 1。
- 根因：conanfile.build() 的 `_patch_config_sub()` 有两处缺陷，导致
  `linux-ohos*` 没进 config.sub 的 kernel-OS-combo 白名单：
  1) **guard 顺序冲突**：patch1 先插入 `ohos-linux)` case，其内部写入字面量
     `basic_os=linux-ohos`，随后 patch3 的守卫 `if "linux-ohos" not in content:`
     据此判为"已加过"而整体跳过，kernel-OS-combo 的 `linux-ohos*` 分支根本没写进去。
  2) **正则误命中**：patch3 原正则 `linux-uclibc[\*/-]?\s*\)` 会同时命中
     `uclinux-uclibc* )`（第三段 kernel-combo 子句，含子串 linux-uclibc），写出
     非法 shell（Syntax error）。
- 修法：将 patch3 守卫改为 `if "linux-ohos*)" not in content:`（只认 combo 行才有的
  `*)` 结尾，patch1 写的 `linux-ohos` 不带 `*)`，不会误判）；patch3 替换串锚定为
  `"| linux-uclibc* )"`（带前导 `| `，不会命中 `uclinux-uclibc* )`）。已对本机解压的
  原版 admin/config.sub 验证：patch 后 `config.sub aarch64-unknown-linux-ohos`
  返回同串且退出 0，x86_64-linux-gnu / aarch64-linux-gnu / aarch64-linux-android
  等常规三元组仍全部通过。
- 保持未提交，等待 HMBS 真机复跑预检验证。

## 2026-10-11 真机预检失败（compile 阶段）——unsafe_local_mktemp（config.status 临时目录）
- 现象（focus round）：configure 末尾 `configure: creating ./config.status` 后，
  `./config.status[993]: can't create ./confpifnch/subs1.awk: Permission denied`，
  `config.status: error: could not setup config files machinery`，conan create 退出码 1。
  HMBS 平台诊断：[unsafe_local_mktemp] 真机文件系统上 mktemp 创建的目录无法供
  Autoconf 后续写入；当 HMBS_AUTOCONF_MKTEMP_FALLBACK=1 时，仅在 configure 阶段让
  mktemp 返回失败，触发 Autoconf 的 mkdir fallback。
- 根因：configure → config.status 的 AS_TMPDIR 用 `(umask 077 && mktemp -d
  "./confXXXXXX")` 建临时目录（本例为 ./confpifnch）。真机（HMFS/HMDFS）上
  toybox mktemp 产 drwx--S---（组/其他无写），构建进程写不进 subs1.awk → EACCES。
- 修法（与本轮实际一致）：conanfile.py build() 新增 `_autoconf_mktemp_fallback()`
  （读环境 HMBS_AUTOCONF_MKTEMP_FALLBACK，truthy 即启用）与
  `_patch_configure_as_tmpdir_umask(configure)`（把发布包 `configure` 中 AS_TMPDIR
  的两处 `umask 077`——主分支 `(umask 077 && mktemp -d "./confXXXXXX")` 与 fallback
  `(umask 077 && mkdir "$tmp")`——改为 `umask 022`）。
- 关键机理：configure 在末尾用带引号的 `cat >>"$CONFIG_STATUS" <<\_ACEOF` heredoc
  原样写 config.status 并随即运行它，因此任何"先跑 configure 再事后改 config.status"
  都为时已晚（configure 在 create config.status 阶段就已失败）。必须在跑 configure
  **之前**把 umask 改好，且 config.status 是 configure 内联生成、继承 configure 文本，
  故改 configure 文本即可传导。PATH-prepend mktemp wrapper 方案不可靠：HMBS_CAP_CHMOD=0
  使新写 wrapper 无 exec 位，shell 会跳过它落回真 mktemp，无法拦截（多次复现证据）。
- 依据：Inn/DRAFT 同卷受控实验——`umask 077 && mktemp -d` → drwx--S--- 写不进；
  `umask 022 && mktemp -d` → drwxr-s--x 可写；mktemp-d 最终模式 = 0777 & ~umask，
  放宽 umask 确实生效。两处都改成 022，无论走 mktemp 分支还是 mkdir 分支都可写。
- 同时移除无效的"configure 后改 config.status umask 并重跑"死代码（configure 失败时
  根本到不了）与不再使用的 `_create_mktemp_fallback_wrapper`/`shutil` import。
- 保持未提交，等待 HMBS 真机复跑预检验证。


## 2026-10-11 真机复跑失败（compile）——round-1 umask 补丁无效，改用 bypass-mktemp 策略
- 现象：round-1 把 configure AS_TMPDIR 两处 umask 077→022 后，真机仍报
  `./config.status[993]: can't create ./confllekKE/subs1.awk: Permission denied` +
  `could not setup config files machinery`（同一 unsafe_local_mktemp 指纹）。
- 结论：**本机 mktemp -d 强置不可写模式、无视 umask**（DRAFT-6507 场景，与 inn2 的
  umask-022 实验结论相反）。因此 relax umask 无效：mktemp 分支仍“成功”建出坏目录，
  `test -d` 通过，Autoconf 的 mkdir fallback 根本不会执行 → 写 subs1.awk 继续 EACCES。
- 新策略（与本轮实际一致，对齐 HMBS 诊断“让 mktemp 失败 → 触发 mkdir fallback”）：
  `_patch_configure_tmpdir_bypass_mktemp(configure)` 把 configure 中 AS_TMPDIR 整块
  （主分支 `(umask 077 && mktemp -d "./confXXXXXX")` + fallback `(umask 077 && mkdir
  "$tmp")`）重写为直接 `(umask 022 && mkdir "$tmp")`——彻底不复用 mktemp，强制走
  Autoconf 的 mkdir 建临时目录，并放宽 umask 022（mode=0777&~umask，创建者可写，
  Inn/DRAFT-verified）。config.status 由 configure 带引号 heredoc 原样生成，故改
  configure 文本即传导，且必须改在 configure 运行之前。
- 已本地验证：old_block 与真实 configure 精确匹配（含 `conf$$-$RANDOM` 的 PID 双
  `$$`）；patch 后 0 处 mktemp、0 处 umask 077、1 处 umask 022；`sh -n` 语法合法；
  在本机跑 patch 后 configure 完整走通（exit 0，生成 Makefile/config.h，
  config.status 785 行为 `(umask 022 && mkdir "$tmp")`，无临时目录权限错误）。
- 注意：写入 conanfile 时 `$$` 须保留为字面双美元（PID），编辑工具可能把 `$$` 折叠成
  `$`，改完需 grep 确认 `conf$$-$RANDOM`。
- 保持未提交，等待 HMBS 真机复跑预检验证。


## 2026-10-11 真机复跑失败（compile）——round-2 未生效，改为无条件应用 mkdir 重写
- 现象：round-2 把 configure AS_TMPDIR 重写为 mkdir + umask 022 后，真机仍报
  `./config.status[993]: can't create ./confllekKE/subs1.awk: Permission denied`
  （再后一轮又 `./confLJkGEp`）。
- 关键取证：失败临时目录名是 `confLJkGEp`（6 位随机字母、**无连字符**）——这正是
  `mktemp -d "./confXXXXXX"` 模板的产物；而改后 mkdir 分支产物应为
  `conf$$-$RANDOM`（带连字符）。→ 证明 **round-1/round-2 的 configure 补丁根本没生效**，
  真机仍走 mktemp 分支。
- 根因：round-1/2 的 `_autoconf_mktemp_fallback()` 都依赖环境变量
  `HMBS_AUTOCONF_MKTEMP_FALLBACK`，而该变量并未传到配方进程（或未置真），
  `os.environ.get` 读到 None 返回 False → 补丁从未执行。
- 新策略（与本轮实际一致，第 3 次修复、改用不同策略）：**去掉环境变量门控**，在
  build() 中无条件调用 `_patch_configure_tmpdir_bypass_mktemp(configure)`（本配方唯一
  目标就是 HarmonyOS，其中必然存在 HMFS unsafe_local_mktemp 问题）。该方法把 configure
  AS_TMPDIR 整块重写为直接 `(umask 022 && mkdir "$tmp")`（不经过 mktemp）。依据：
  cpdb-libs 同卷实证——纯 `mkdir`（靠 umask，非 mktemp 的显式 chmod 0700）得
  drwxrws--x 可写；HMBS 诊断也指明应走 mkdir fallback。方法幂等：已重写则不改。
- 已验证：method 的 old_block 与真实 configure 精确匹配=1（含字面 `$$` PID）；
  patch 后 mktemp=0、umask077=0、umask022=1；`sh -n` 合法；本机 patch 后 configure
  完整 exit 0，config.status 中 AS_TMPDIR 实测为 `{ tmp=./conf$$-$RANDOM;
  (umask 022 && mkdir "$tmp") }`。
- 血泪教训：编辑工具（edit/apply_patch）会把 `$$` 折叠成 `$`，写入含 `$$` 的方法时
  必须用 Python 文件写回并 grep `conf$$-$RANDOM` 核对，否则 old_block 无法精确匹配
  真实 configure、补丁静默不生效。
- 保持未提交，等待 HMBS 真机复跑预检验证。

## 2026-10-11 真机预检失败（compile 阶段）——AC_FUNC_MALLOC rpl_malloc 修复
- 现象：configure 已成功跑完（mktemp/E386 已修复），make 编译 src/main.c 时报：
  main.c:671:19: error: incompatible integer to pointer conversion assigning to
  'char *' from 'int' [-Wint-conversion]  usbdevsn[i] = malloc(5);
  日志中 config.h 内容回显 `#define malloc rpl_malloc`。
- 根因：configure.ac 调用 AC_FUNC_MALLOC，其在 OHOS 上判 `no`（case $host_os 的
  guess-yes 列表覆盖 *-gnu*/BSD/Solaris 等，不含 linux-ohos；cross/运行时 conftest
  无法验证 malloc(0)）。`no` 时 config.h 定义 `malloc rpl_malloc` 并把不存在的
  malloc.o 追加进 LIBOBJS，导致 main.c 的 malloc(5) 隐式声明为 int 返回，
  clang 报 -Wint-conversion 编译失败。
- 修法：在 build() 的 configure 内联 env 命令中加入 autoconf 缓存变量
  `ac_cv_func_malloc_0_nonnull=yes`。该变量作为 preset ac_cv_* 环境变量被 configure
  的 `if test ${ac_cv_func_malloc_0_nonnull+y}` 守卫直接采纳（打印 "(cached) yes"），
  从而 HAVE_MALLOC=1、不定义 rpl_malloc、不追加 malloc.o。本地用 autoconf 2.71 复现：
  env ac_cv_func_malloc_0_nonnull=no => `#define malloc rpl_malloc`（复现原报错），
  env ac_cv_func_malloc_0_nonnull=yes => HAVE_MALLOC 1 且 `#undef malloc`（修复后）。
  OHOS libc 的 malloc(0) 与任何现代 libc 一样返回有效非 NULL 指针，覆盖为 yes 正确。

## 2026-10-11 真机预检失败（package 阶段）——install shim 多源拷贝 Exit 64 修复
- 现象：make install 到 install-data 阶段 `install-pkgdata1DATA` 规则报
  `make[2]: *** [Makefile:572: install-pkgdata1DATA] Error 64`，
  失败命令 `install -c -m 644 web1/index.html ... web1/style.css '<dest>/httpd/skin1'`，
  使用的 install 是 HMBS 注入的 install shim（capabilities: install_shim=true, chmod=0）。
- 根因：HMBS 因 HMFS chmod 无效（E046）注入 install shim（拦截 PATH 中的 install）。
  该 shim 对“多源文件→目标目录”这一 automake 数据安装形式（$(INSTALL_DATA) 展开为
  `install -c -m 644 <13 个文件> <dir>`）返回退出码 64（EX_USAGE）；而 install-exec 阶段
  libtool 的单文件安装已成功，说明仅数据类多源安装被 shim 拒绝。
- 修法：package() 的 make install 命令行追加 `'INSTALL_DATA=cp -f'`，让 automake 数据规则
  （三个 skin pkgdata 目录 + man 页）用 `cp -f <files> <dir>` 完成纯文件拷贝，绕过 install
  shim；install-exec（libtool 安装二进制/库）不受影响。cp 本来就是标准 HMFS 工具，
  且这些 HTML/CSS/PNG/man 文件的 mode 在 HMFS 上本就被归一化（E046），cp 足够。
- 本地验证（autoconf automake 同款规则模拟）：`/bin/sh -c "make ... 'INSTALL_DATA=cp -f'"`
  该命令行变量覆盖被规则采纳，命令变为 `cp -f <files> <dir>` 且文件正确落盘；
  默认（无覆盖）则为 `install -c -m 644 <files> <dir>`（真机上被 shim 拒）。

## 2026-10-11 真机预检失败（test_package 阶段）——消费者找不到公共头 sispm_ctl.h 修复
- 现象：主包编译+打包成功（malloc/INSTALL_DATA 修复均已通过），test_package 编译
  test_sispmctl.c 时报 `fatal error: 'sispm_ctl.h' file not found`（test_sispmctl.c:21
  #include <sispm_ctl.h>），conan create 退出码 1。
- 根因：上游 sispmctl 不安装公共头（Makefile.am 无 include_HEADERS），配方在 package()
  手动把 src/sispm_ctl.h 拷贝到 <package>/include，但 package_info() 只设置了
  cpp_info.libs/bindirs，没有显式导出 includedirs，导致 CMakeDeps 生成的
  sispmctl::sispmctl 目标未把 -I<package>/include 传给消费者（test_package），
  find_package(sispmctl) 虽成功（target 可链接）但头文件不可见。
- 修法：package_info() 显式设置 `self.cpp_info.includedirs = ["include"]`，与
  package() 拷贝头文件的目标目录一一对应；并确保 test_package 已显式声明/链接
  libusb-compat（sispm_ctl.h 依赖 <usb.h>，已满足）。recipe 哈希变化会触发主包
  重建，package() 的拷贝一并重跑，头文件与导出 include 目录同时就位。

## 2026-10-11 真机复跑失败（test_package 阶段）——round-3 includedirs 未传递，改显式注入
- 现象：round-3 的 `package_info()` 显式 `cpp_info.includedirs=["include"]` 后，真机复跑
  （11:35 预检，晚于 11:32 改动同步）仍在 test_package 编译 test_sispmctl.c 报
  `fatal error: 'sispm_ctl.h' file not found` 失败。找到包 `find_package(sispmctl CONFIG
  REQUIRED)` 成功、目标可链接，但 include 目录未到达编译器。
- 结论：**生产侧 cpp_info.includedirs 的 CMakeDeps 传递在本机未生效**，反复依赖该假设
  即是重复同一根因。改为完全确定性的新路线：test_package 在 build() 里
  `cmake.configure(variables={"SISPMCTL_INCLUDE_DIR": <pkg>/include})`，从依赖的
  package_folder 直接取 include 目录，于 configure 时点显式注入到消费者编译；
  CMakeLists.txt 用 `if(NOT DEFINED SISPMCTL_INCLUDE_DIR OR NOT EXISTS "<dir>/sispm_ctl.h")`
  硬性 FATAL_ERROR 守卫，杜绝"空 include 路径静默通过"。此方案不依赖
  CMakeDeps 对 application 包类型 cpp_info 的传递行为，且由真实 package_folder
  驱动、可复现。
- 保留 package_info() 的 includedirs（对真实下游消费者正确的接口），但 test_package
  编译不再依赖它。
- 保持未提交，等待 HMBS 真机复跑预检验证。


## 2026-10-11 真机复跑失败（test_package 链接阶段）——libsispmctl.a 未进入消费者链接
- 现象：主包编译（malloc/INSTALL_DATA/sispm_ctl.h 三项修复均通过）后，test_package
  编译 test_sispmctl.c 成功，但链接报 3 个未定义符号：
    ld.lld: error: undefined symbol: plannif_reset
    ld.lld: error: undefined symbol: pms2_schedule_to_buffer
    ld.lld: error: undefined symbol: pms2_buffer_to_schedule
  这恰是 test_sispmctl.c 用到的全部 libsispmctl 函数（test 只用了这 3 个库 API），
  所以是**整个库没被链上**，不是某函数缺失。
- 根因：与上一轮 includedirs 未传递同源——`package_type = "application"` 的
  sispmctl 包，其 CMakeDeps 生成的 sispmctl::sispmctl 消费者目标不向 test_package
  传递库链接（cpp_info.libs=sispmctl 未生效）。日志里 find_package(sispmctl CONFIG
  REQUIRED) 成功、目标可写，但链接不带 -lsispmctl。
- 证据：本地用真实上游源码 + 官方 tarball sha256 建静态库（--disable-shared
  --enable-static）：
  * `nm -g .libs/libsispmctl.a` 三条 `T` 符号齐全（plannif_reset / pms2_schedule_to_buffer
    / pms2_buffer_to_schedule 均存在且全局可见）。
  * libtool install 安装产物为 `<pkg>/lib/libsispmctl.a`。
  * 用“先 libsispmctl.a 再 libusb”的显式链接顺序本地验证成功并运行通过，证明
    符号/归档/链接顺序均正确，唯一缺的是把归档交给链接器。
- 修法：沿用本配方已验证的显式注入模式（SISPMCTL_INCLUDE_DIR）：test_package 的
  build() 从依赖 package_folder 直接取 `<pkg>/lib/libsispmctl.a` 注入为
  SISPMCTL_LIBRARY，CMakeLists.txt 用 `if(NOT DEFINED ... OR NOT EXISTS ...)` 硬性
  FATAL_ERROR 守卫（缺库直接报错），并把 `sispmctl::sispmctl` 从 target_link_libraries
  换成 `${SISPMCTL_LIBRARY}`，置于 libusb-compat/libusb-1.0 **之前**（静态归档先
  行、其未解析的 usb_* 由后面的 libusb 目标补足）。
- 本地验证：等价链接命令局部编译通过并运行 socket=0 rc=0。保持未提交，等待 HMBS
  真机复跑预检验证。

## 2026-10-11 真机复跑失败（test_package 阶段）——sispmctl -v rc=127 缺 conanrun 运行时环境
- 现象（focus round）：test_package 内 test_sispmctl 8/8 全过、返回
  'RESULT total=8 passed=8 failed=0'，但随后 `sispmctl -v` 检查判
  `ERROR: sispmctl -v failed (rc=127) or no 4.12 in output`，
  HMBS_TEST_PACKAGE_RESULT passed=false，conan create 退出码 1。
- 根因：**check 2 用裸 subprocess.run 跑 sispmctl -v，未带 conanrun 运行时环境**；
  而 check 1 用的是 `self.run(..., env="conanrun")`。sispmctl 可执行文件经 pc shim 的
  `-lusb-1.0` 动态链接了 libusb-1.0.so（libusb-compat 静态归档拉入的共享库），
  -v 纯版本路径虽不调用 USB 函数，但动态装载器启动时仍须解析 libusb-1.0.so。
  不带 conanrun 的 LD_LIBRARY_PATH 时动态装载器报
  'error while loading shared libraries: libusb-1.0.so.0 ...' → shell 返回 127
  （"command not found"/"无法装载共享库" 码），与"测试真的失败/二进制缺失"无关。
  rc=127 是动态装载失败档位，不是 sispmctl 应用层错误。
- 修法（与本轮实际一致）：把 check 2 改为与 check 1 同构——用
  `self.run(..., env="conanrun", ignore_errors=True)` 应用 conanrun 运行时环境，
  命令为 `"'<bin>/sispmctl' -v; echo $? > '<rc_file>'" > '<out_file>' 2>&1`，
  rc 与真实 stdout/stderr 分别落盘后由确定性文件源读取（不在 stdout 上数字符串数数），
  计数逻辑保持不变（ok2 = rc==0 且输出含 "4.12"，无条件 total 计 2、仅通过 +1）。
  移除不再使用的 subprocess import（新增 tempfile）。
- 依据：check1(check 1 走 conanrun) 8/8 通过 与 check2(裸 subprocess) rc=127
  在同一日志中并存，唯一的差异化变量就是运行时环境 LD_LIBRARY_PATH。
- 保持未提交，等待 HMBS 真机复跑预检验证。
