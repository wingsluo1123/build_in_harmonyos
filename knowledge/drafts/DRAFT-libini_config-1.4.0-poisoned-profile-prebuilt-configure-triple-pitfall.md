# DRAFT-libini_config-1.4.0-poisoned-profile-prebuilt-configure-triple-pitfall
> 毒化profile下Autotools预生成configure三连坑：CONFIG_SHELL与CC实测兜底加PKG_CONFIG指向pkgconf真名加runtime install多文件覆盖
## 问题特征（真实日志片段/标记）
- HMBS能力声明 `HMBS_PLATFORM_CAPABILITIES={"shell":"/bin/sh",...,"install_shim":true,...}`，`HMBS_BUILD_TOOLS` 仅含 cmake/make/ninja/python3，无 pkg-config。
- 坑1坏shell：`src/configure[139]: /data/service/hnp/bin/bash: inaccessible or not found`，`AUTOTOOLS configure Error 127`，上游测试 0/0/0。删 `autoconf/automake/libtool` 后本包直调仍同错复现，证非 m4 而是本包 configure 继承毒化 env。
- 坑1b坏CC：`checking for gcc... /data/service/hnp/bin/clang` 后 `checking whether the C compiler works... no`，`configure: error: C compiler cannot create executables`，`config.log: /data/service/hnp/bin/clang: inaccessible or not found`，`$?=127`。裸 `sh configure` 直调绕过 `AutotoolsToolchain`，`env="conanbuild"` 又丢 `TMPDIR/am_cv/PKG_CONFIG_PATH`，同错在 Error 77 往返。
- 坑2缺名：CC兜底后 `supports -fno-rtti/PIC/static flag works均为 yes`，新卡点 `checking for pkg-config... no` → `configure: error: pkg-config not found`，`Computing dependency graph` 已含 `pkgconf/3.0.5` 仍为 no。
- 坑3安装器：编译与 `make check` 已过（`# FAIL: 0/# XFAIL: 0/# ERROR: 0`），`package()` 在 `.../runtime/libini_config-1.4.0/bin/install -c -m 644 ... install-dist_docDATA] Error 64`，单文件 libtool 安装可过、多文件 `-c -m 644 a b c dir` 报 EX_USAGE/64。
## 根因
- ci profile `ohos-aarch64 [buildenv]` 把 `SHELL/CONFIG_SHELL` 硬编码为预检机不可访问的 `/data/service/hnp/bin/bash`，把 `tools.build:compiler_executables` 钉为部分机器不可见的 `/data/service/hnp/bin/clang`。`Environment.define` 被 `conanbuild.sh` 重载覆盖，autoconf 遇非空 `CONFIG_SHELL` 即重 exec 坏路径；文件存在性检查发现不了不可执行驱动，唯有 hello-world 链接实测可判定。
- 配方为打 `0003-configure.ac` 引入 `autoconf/automake/libtool`，拉起 conancenter m4 源码重建先败；tarball 自带预生成 configure，`0001/0002 config.guess/sub` 与 C/H 补丁均无需重生成。
- `pkgconf/3.0.5` 只装 `pkgconf` 真名、不提供 `pkg-config` 别名，而 ding-libs 系预生成 configure 用 `AC_PATH_TOOL(PKG_CONFIG,pkg-config)` 单名探测，有包无变量指向恒为 no。
- HMBS runtime `bin/install` 包装器多文件拷贝不兼容，多文件 `INSTALL_DATA` 派生自 baked `INSTALL` 即败；需 make 命令行覆盖。另手动链赢过 `conanbuild.sh` 会丢 `tc.extra_cflags` 的 `-I<check>/include`，需显式补 Check 头路径；多 token 引号内联会经二次转义泄漏字面引号致 Error 77，故单 token 与多 token 走不同通道。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. 去 autoreconf 直用预生成 configure：`archives/l/libini_config/1.4.0/conanfile.py` 的 `build_requirements()` 删除 `autoconf/2.72、automake/1.18、libtool/2.5.4` 仅留 `check/0.15.2 test-requires`；`conandata.yml` 删除 `0003-configure.ac` 并删该补丁文件；`build()` 对预生成 configure 做 `umask 077->022` 直修，不跑 aclocal/autoconf/automake。
2. CONFIG_SHELL 内联覆盖：新增 `_inline_prefix()/_configure_args_list`，以 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh /bin/sh configure --prefix=... --disable-nls --disable-dependency-tracking` 显式直调，`make/make check/make install` 同加内联前缀并保留 `env="conanbuild"` 继承 toolchain/flags；同步 `_environment()` 定义与 `notes.md`。
3. CC 实测兜底：新增 `_probe_compiler()` hello-world 链接实测与 `_find_working_compiler()` 去重发现，跳过不存在文件、识别 EAGAIN，仅接受真实产出可执行文件的驱动，首个可用者以单 token `CC=` 内联透传；保留 `TMPDIR` 真实写入探测（优先 HMBS 注入 TMPDIR，逐个 `makedirs+open(w)+unlink` 实测）、`am_cv_sleep_fractional_seconds/am_cv_filesystem_timestamp_resolution` 缓存、`PWD` 透传、`-j1` 串行；失败时限幅转储 `config.log` 首错段。
4. 依赖旗标防引号泄漏：删除 `_inline_prefix` 中 `CPPFLAGS="$CPPFLAGS -I..."` 带内层双引号透传，Check 头仅走 `AutotoolsToolchain.extra_cflags` 环境通道加日志；手动链另以校验 helper `_check_include_dir()` 经 `CPPFLAGS/CFLAGS` 内联与 `_environment append` 双补齐。
5. PKG_CONFIG 指真名：`build_requirements()` 新增 `self.tool_requires("pkgconf/3.0.5")`；`generate()` 经 `tc.environment().define("PKG_CONFIG","pkgconf")` 落盘，手动行经 `_inline_prefix` 内联单 token `PKG_CONFIG=pkgconf` 双通道生效。
6. runtime install 覆盖：新增 `_select_install_args()` 在 `build_folder/install-probe` 做多文件 `-m 644` 真实拷贝+内容比对，按 `/system/bin/install、/bin/install、/usr/bin/install、which` 顺序试探、失败试 `cp -fp` 回退；`package()` 的 `make install DESTDIR` 追加探测通过的 `INSTALL=...` tokens（空格 join，不整体 quote）。
7. 测试证据补齐：主配方解析 `test-suite.log` 的 `# TOTAL/# PASS` 取 TOTAL 最大者为聚合发射 `HMBS_UPSTREAM_TEST_RESULT` 并落盘至 `res/`；`test_package/test.c` 逐项打印 `CASE PASS:` 共7项并计数发射 `HMBS_TEST_PACKAGE_RESULT`，`MANIFEST.yml assertion_count` 更正为7。
## 禁止策略
- 禁止为 `configure.ac` 补丁重新引入 `autoconf/automake/libtool` 自举链：重现 m4 `src/configure[139]` 坏 bash 不可访问失败。
- 禁止沿用 `CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash` 或裸 `autotools.configure()` 直 exec：`Environment.define` 覆盖不掉 conanbuild 聚合透传，必须命令行内联前缀强制覆盖。
- 禁止裸 `sh configure` 丢 `conanbuild` 或 `env="conanbuild"` 丢 `os.environ`：前者丢 CC/CFLAGS/LDFLAGS/--host 致 Error 77，后者丢 TMPDIR/am_cv/PKG_CONFIG_PATH 同致 Error 77。
- 禁止多 token `CPPFLAGS/CFLAGS` 带内层双引号内联透传：经 shell 二次转义泄漏字面引号致 conftest 链接失败，改走 toolchain 环境通道。
- 禁止只加 `pkgconf` 包而不指 `PKG_CONFIG` 真名：PATH 有包也命中不了单名探测。
## 与相近条目的边界（查重）
- 本条增量是三坑组合：`CONFIG_SHELL/CC` 双毒化实测兜底 + `PKG_CONFIG` 指 `pkgconf` 真名双通道 + runtime install 多文件 `EX_USAGE/64` 探测覆盖。可复用于 `ding-libs/ballandpaddle/kyua` 等同族预生成 configure 库。
- 查重命中均为通用样板或相邻异因：单纯 `CONFIG_SHELL=/bin/sh` 钉选、单纯 `TMPDIR` 可写探测、单纯引号泄漏改走 `tc.environment`、单纯加 `pkgconf` 包，均无本条真名映射与 install 覆盖及双实测兜底组合覆盖。
## 适用判断
- 适用：自带预生成 configure 的 Autotools 库；profile 毒化 `SHELL/CONFIG_SHELL/CC` 为不可访问绝对路径但 HMBS 保证 `/bin/sh` 可用；configure 硬需 `pkg-config` 单名而真机仅供给 `pkgconf` 真名；`make install` 多文件 DATA 经 runtime `bin/install` 报 `Error 64`；HMBS 仅注入 cmake/make/ninja/python3。
- 不适用：需重生成 configure 的 `configure.ac` 大改场景；持续 OOM 落在大 TU RSS 峰值而非 fork 探测；SSH 网关熔断等环境故障轮不得改配方。
