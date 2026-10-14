# svox 1.0 适配笔记

## 上游信息
- 软件：SVOX Pico small-footprint TTS 引擎（离线语音合成，德/英/西/法/意）。
- 代码真正上游：Android AOSP `platform/external/svox`（SVOX 引擎随 Android 发布）。
- 版本 1.0 的源码包形态是 Debian 官方快照 `svox_1.0+git20130326`
 （salsa `a11y-team/svox` 维护），OpenWrt `sound/svox` 用的就是同一个包：
  `PKG_SOURCE_URL:=http://ftp.debian.org/debian/pool/non-free/s/svox`。
- 源码包：`https://deb.debian.org/debian/pool/non-free/s/svox/svox_1.0+git20130326.orig.tar.gz`
  （注意分池是 `non-free` 不是 `main`；conandata 保持单条官方 URL，
  CI 侧 mirror fallback/pre-download 会按需改写，见 `build_and_test.sh` L0j）。
- sha256：`337b25e6ccb3764f0df1e176470b883c90e40e98840d4133340fcc89eb3cea0c`
  （Launchpad `1.0+git20130326-{1,3,13}` 三个源码包页 + OpenWrt `.mk` 的
  `PKG_HASH` 四方一致；真机 `get()` 会再校验）。
- 授权：代码 Apache-2.0。Debian 把二进制包划入 `non-free` 是因为
  lingware 语音数据文件的授权问题，不是代码授权问题（OpenWrt
  `PKG_LICENSE:=Apache-2.0`）；PR 补充说明里如实写明。

## 构建系统
直接 CC 编译（非 autotools）：Debian orig 包的 `pico/` 内根本没有
`configure.ac/configure/Makefile.am`（真机 2026-10-13 source tree 实证：
`pico/` 只有 `Android.mk/compat/lang/lib/res/src/tests/tts`）。
autotools 文件是 Debian 打包（`debian.tar.xz` 的 patches）现场添加的，
orig 包本身不可 `autoreconf`；OpenWrt 的 `PKG_FIXUP:=autoreconf` 能工作
是因为它先打了 Debian 系补丁。沿用 autotools 路线必然在
`_find_autotools_root` 报 `svox autotools root not found`（本轮失败）。
因此按上游 `pico/lib/Android.mk` 列出的 30 个 `lib/*.c` +
`bin/pico2wave.c` 直接 `CC -c` + `ar rcs` + `CC -o pico2wave`，
`-Dpicolangdir` 指向包内 `share/pico/lang`，静态链接 vendored popt。
产物：`libttspico`（C API）+ `pico2wave`（命令行工具，需 popt）
+ `share/pico/lang/*`（lingware 语音数据，架构无关）。

## 编译步骤
1. `get()` 下载 Debian 官方包并 `strip_root` 解压。
2. 定位含 `lib/picoapi.c` 的 pico 根（`<source>/pico` 或 `<source>`，
   递归兜底；找不到则把源码树打进日志再失败，防静默错位）。
3. 直接 CC 构建 vendored popt 并安装到构建目录内 `poptinst/`
   (按 `Makefile.am` 的 5 个 `libpopt_la_SOURCES` 直接 `CC -c` +
   `ar rcs`，不走 configure/make，不触及 config.sub/SHELL，
   见下第八策略周期)。
4. 按 `pico/lib/Android.mk` 的 `lib/*.c` 逐文件
   `CC -c -O2 -fPIC -I lib` 成 `.o`（`CC` 来自
   `tools.build:compiler_executables`，`ar` 取 CC 同目录兄弟），
   再 `ar rcs libttspico.a`（`shared` 时另链 `libttspico.so`）。
5. `CC pico2wave.c libttspico.a -L poptinst/lib -lpopt -lm
   -Dpicolangdir=<package>/share/pico/lang` 产出 `pico2wave`
   （静态链接 popt，运行期仅依赖 libc）。
6. `package()` 拷头文件（`lib/pico*.h`→`include/`）、库、工具、
   lingware（`lang/*.bin`→`share/pico/lang/`），随后产物自检
   （缺 `lib/libttspico.*` / `include/picoapi.h` / `bin/pico2wave` /
   `share/pico/lang/*.bin` 任一直接失败并打印包内树）。
7. 对真实源码树跑无测试审计（`UPSTREAM_TEST_AUDIT` 日志行）。

## 依赖
- 无外部 Conan 依赖（requirements() 为空，PF4/R36 无探测项）。
- pico2wave 用的 popt 以 vendored 源码静态编入（沿已合入的
  logrotate/3.22.0 先例，保持单包原子性）：conandata.yml 的 popt
  条目（popt-1.16，OpenBSD distfiles 镜像，与 archives/p/popt/1.16
  同包同 sha256）→ source() 解压到 ./popt → build() 先以
  --enable-static --disable-shared --disable-nls 编译安装到构建目录内
  poptinst/（OHOS 下加 --build 三元组，E007）→ 主构建经显式
  -I poptinst/include / -L poptinst/lib 找到它（上游是 AC_CHECK_LIB
  风格检测；Raspbian 官方构建指南依赖表里没有 pkg-config，故不用
  PkgConfigDeps，也不再用 AutotoolsDeps）。
- 切外部边的原因（真机预检 2026-10-12 实证）：requires popt/1.16
  时远端排序先命中 conancenter 修订，其自带古董 config.sub 在
  HarmonyOS 下 configure 直接报 cannot run config.sub，OHOS 下总是
  从源码重编 popt 而失败，svox 本体连被读到的机会都没有。vendoring
  后该失败域消失；pico2wave 仍静态链接 popt（运行期仅依赖 libc），
  产物形状不变（bin/pico2wave 保留，commands.json 仍为 tool）。

## 上游测试
- 审计结论：**上游无任何自动化测试**。
  `pico/**/Makefile.am` 无 `TESTS`/`check_PROGRAMS`/`check-local`；
  `pico/tests/` 只有 `data/` 夹具而无测试程序（与 AOSP 同期树一致）；
  Debian/OpenWrt 打包均不跑测试套件。
- 处理：`test_package/MANIFEST.yml` 声明 `upstream_tests_exist: false` +
  非空 `upstream_test_audit` + `upstream_test_total: 0` /
  `upstream_test_count_method: autotools_tests`（cvechecker 4 同款先例）；
  `conanfile.py build()` 真实执行审计（日志留证），`no_tests` 标记按
  `upstream_test_in_build: false` 由 test_package 阶段输出。

## test_package
- `test_svox.c`：13 条断言，真实调用 libttspico 系统层 API（无需 lingware）：
  `pico_initialize` 建系统句柄 → `pico_getNrSystemWarnings` 零警告 →
  `pico_getSystemStatusMessage` 状态文本 → `pico_createVoiceDefinition` 建
  语音定义 → 重复建定义被拒绝（阴性对照，证明 harness 能观测真实失败）→
  `pico_releaseVoiceDefinition` 释放 → `pico_terminate` 终止 →
  终止后重新初始化再终止（文档允许的 init/terminate 多轮循环）。
  API 契约来源：`picoapi.h` "Basic_Usage"（SVOX Pico 1.0 and later）。
- `test_package/conanfile.py test()` 运行二进制后输出
  `HMBS_TEST_PACKAGE_RESULT`（discovered=1/passedCount=1，对应唯一的
  `add_test(test_svox)`）与 `HMBS_UPSTREAM_TEST_RESULT`（no_tests）。

## 已知风险（待真机预检验证）
1. 直接编译的 `.c` 清单以 `pico/lib` 通配为准（真机实测 29 个）；
   清单变化自适应，缺失时产物自检会如实失败并打印包内树。
2. `pico2wave.c` 不在 orig 包内（Debian 打包侧附加工具），已按
   nanotts 同源文件（Mathieu Parent/Apache-2.0）vendored 到
   `files/pico2wave.c` 并经 `export_sources` 导出；构建期优先用上游
   自带、缺失时回退 vendored。
3. 头文件若装到 `include/pico/` 而非 `include/`，配方有兜底（源码树定位
   `picoapi.h` 补拷）；`package()` 自检会如实失败并打印包内树。
4. 外部 popt 依赖已切除：真机预检 2026-10-12 实证
   conancenter 修订的 popt 在 OHOS 下必从源码重编且 config.sub 失败，
   故改 vendoring；不再需要“改掉 pico2wave 只编 lib”回退（产物形状
   保持不变）。vendored popt 自身构建失败见下一条（第五策略周期）。

## 验证结果
- 本机：`python -m py_compile` 通过全部 py 文件；中文文件均为 Python 直写
  UTF-8（无 BOM）；`conanfile.py` 无裸 `${CC}` 等环境变量（R33：CC/AR 均
  经 `tools.build:compiler_executables` 显式解析），平台
  判断用 `in ("Linux", "OHOS")`（R32）。
- 真机预检：待 HMBS 后台执行（本轮保持未提交工作树）。
- 2026-10-13 第四策略周期（pico2wave.c 缺失）：真机
  `pico root: <source>/pico` + `lib_sources=29 headers=33 lang_bins=12
  wave=<missing>` 后 `ConanException: svox pico2wave.c not found`。
  根因是 pico2wave 系 Debian 打包侧附加工具（Mathieu Parent/Apache-2.0），
  orig 包内根本没有该文件（AOSP 上游亦只有库）。本轮按 nanotts 同源文件
  vendored 到 `files/pico2wave.c`（`export_sources` 导出），构建期优先用
  上游自带、缺失时回退 vendored；产物形状不变。
- 2026-10-13 第三策略周期（autotools 根不存在）：真机
  `ConanException: svox autotools root not found` + source tree 显示
  `pico/` 只有 `Android.mk/compat/lang/lib/res/src/tests/tts`，无任何
  `configure.ac/configure/Makefile.am`。根因是 orig 包本身不含 autotools
  文件（Debian 打包经 `debian.tar.xz` patches 现场添加，orig 不可
  `autoreconf`），旧配方的 pico-autotools 假设不成立。本轮改走直接 CC
  路线：按 `pico/lib/Android.mk` 的 30 个 `lib/*.c` + `bin/pico2wave.c`
  直接编译归档，不再 `autoreconf`，不再依赖 automake/libtool。
- 2026-10-13 第二策略周期（tar fork OOM）：上一周期连续三次“环境资源故障、
  零改动待重跑”均未通过（下载 Signal 9 → harness fork 失败 → 解包 tar fork
  OOM，阶段各不相同），证明单纯等待环境恢复无效，且本轮已禁止沿用相同根因
  假设。重读日志：失败点 `tar: child process: Cannot fork: Out of memory` 发
  生在解包/编译期，而配方此前在 `build()` 对整个 `<source>` 做
  `**/configure` 递归 glob、在 `_find_autotools_root()`/`package()` 对含
  25MB lingware 大数据目录的全树 `os.walk`，与 tar/编译进程争用内存，直接抬
  高 fork 失败概率。本轮改走配方减负路线：walk 剪掉
  `lang/data/lingware/voices/popt/.git` 大数据目录；configure 改写限定
  `pico_dir` + vendored `popt` + 源码顶层；头文件/授权搜索限定探测根附近且
  授权搜索只下探两层。产物与构建语义不变。
- 2026-10-13 第五策略周期（vendored popt configure 失败）：真机
  `configure: error: cannot run /data/service/hnp/bin/bash ./config.sub`
  （`_build_popt` 内 `--build=aarch64-unknown-linux-gnu` 触发）。
  根因是 vendored popt-1.16 自带 2009 版 config.guess/config.sub，
  不认识 aarch64 三元组——vendoring 只搬运了源码，没有搬运独立
  popt 配方的 E007 修复。本轮把 `archives/p/popt/1.16/patches/` 的
  三个补丁（0001-config.guess、0002-config.sub、0003-umask/mktemp）
  按字节原样复用到本配方 `patches/`，经 conandata `patches:`
  （`base_path: "popt"` + `strip: 1`，bamutil 同款写法）打到
  vendored 子目录；`build()` 开头的 `apply_conandata_patches` 已在
  `_build_popt` 之前执行，顺序成立。`--build` 显式三元组保留
  （新版 config.sub 可识别，host 默认为 build 仍为原生构建）；
  未另起 mktemp shim，复用 HMBS 注入的 TMPDIR（0003 补丁即用它）。
- 2026-10-13 第六策略周期（同一指纹第 2 次失败，换策略）：上一轮预检
  与本轮报错逐字相同（`cannot run ... ./config.sub`，且行号 263→266 /
  330→339 证明新 `conanfile.py` 已进预检），但导出日志只有
  `.yml/.py/.c` 拷贝、无 `.patch` 拷贝——`conandata patches` +
  `base_path: "popt"` 的整文件替换没有作用到 vendored 源码（bochs 等
  `base_path` 先例均作用于主源码多文件布局，未必覆盖本案的 vendored
  子目录情形）。本轮改走与 `conanfile.py` 同步的确定性路径：OHOS 下
  `_build_popt` 在构建期以恒等映射脚本覆盖 `popt/config.sub`
  （`_stub_popt_config_sub`：先读原文首行留证，缺文/写回失败直接抛错，
  不静默跳过）。`--build=aarch64-unknown-linux-gnu` 本身已是规范三元组
  （取值与 logrotate/bochs 合入先例一致），恒等输出与新版 config.sub
  一致；其余 configure 编译器/特性探测仍真实执行，不伪造检查结果。
  Linux 路径不动。`conandata.yml` 的 `patches:` 声明与 `patches/` 目录
  已移除（未生效的死配置不保留）。
- 2026-10-13 第七策略周期（同一指纹第 3 次失败，换策略）：行号 265/341
  与工作树逐字吻合，证明带恒等 printf stub 的新代码已进预检——而该 stub
  在内容上不可能失败（分支已执行且未抛错，`--build` 也已出现在失败命令
  中），同一错误复现只能说明失败与脚本内容无关，问题在执行它的解释器。
  顺藤摸瓜：`ci/conan/profiles/ohos-aarch64` 的 `[buildenv]` 导出
  `SHELL=/data/service/hnp/bin/bash`，configure 内部用 `$SHELL` 跑
  `config.sub`，该解释器在真机上无法执行脚本（旧 config.sub 与新 stub
  一视同仁地报 cannot run）。本轮：configure/make/install 三处调用一律
  `SHELL=/bin/sh` 前缀覆盖（HMBS 平台能力 `shell=/bin/sh`，且 configure
  本体正是经 `/bin/sh` 启动成功的）；stub 保留（旧 config.sub 在可用
  shell 下仍会拒绝 aarch64）。另加 configure 失败时自动转储 `config.log`
  尾部 + SHELL 存活探针，供机器取证。只改本配方，不动共享 profile
  （单库 PR 边界）。
- 2026-10-13 第八策略周期 (同一指纹第 4 次失败，换实现路线)：上一轮带
  `SHELL=/bin/sh` 前缀 + 恒等 printf stub 的新代码已进预检
  (行号 265/341 与工作树吻合)却同一错误逐字复现，
  证明上一方案无效且失败与脚本内容无关。重读日志 +
  `ci/conan/profiles/ohos-aarch64`：`[buildenv]` 同时导出
  `SHELL` 与 `CONFIG_SHELL` 到同一失效路径
  `/data/service/hnp/bin/bash` (真机探针 `ls`/`--version` 均报
  inaccessible) ，autoconf configure 内部以 CONFIG_SHELL 覆盖 SHELL，
  单纯前缀 SHELL 永远无效。本轮放弃 configure 路线：
  vendored popt 按 `Makefile.am` 的 5 个 `.c` 直接 CC 编译 +
  `ar rcs libpopt.a` + 拷 `popt.h`，与主库同 CC/同 ar；
  `-D_GNU_SOURCE -D_REENTRANT` 同 configure.ac，`POPT_SYSCONFDIR=/etc` +
  `PACKAGE=popt` 手动定义，HAVE 最小集
  (FLOAT/FNMATCH/GLOB/UNISTD/STRERROR，真机标准头文件)其余走上游
  回退分支；HAVE_STRERROR 必须定义（否则回退到已移除的
  sys_nerr/sys_errlist）。不动共享 profile，不再调用
  config.sub/config.guess/make。
- 2026-10-13 第九策略周期（直接 CC 下 stpcpy 重定义）：真机
  `popt/system.h:69: static declaration of 'stpcpy' follows non-static
  declaration` + 注 `string.h:65: previous declaration is here`。
  根因是直接 CC 的 HAVE 最小集漏了 `HAVE_STPCPY`：上游 `system.h`
  以 `#if !defined(HAVE_STPCPY)` 控制 static inline 回退，
  configure 经 `AC_CHECK_FUNCS(... stpcpy ...)` 在提供该函数的
  平台上定义它从而关闭回退；本配方 `-D_GNU_SOURCE` 下 OHOS
  sysroot 同样提供非 static 声明，直编时回退与之冲突。本轮仅在
  `_build_popt` 的 defines 追加 `-DHAVE_STPCPY=1`，其余 HAVE
  集与回退语义不变，不伪造 `glob_pattern_p` 等 OHOS 未提供的符号。
- 2026-10-13 第十策略周期（harmonybrew tar EPERM）：真机
  `sh: /storage/Users/currentUser/.harmonybrew/bin/tar: Operation not
  permitted`（compile 阶段，上游/新增测试均 0）。配方本身从不调用
  `tar`（grep 全树仅注释提及 tarball；build 仅 CC/ar/CC-link），唯一
  tar 依赖是 Conan 自动解包（`get(strip_root=True)`）。指纹与
  DRAFT-14257（registry glib 工具 stale-codesign exec 126）/
  vgmplay（CMake install 改写 RUNPATH 破坏签名后 EPERM）同属
  HarmonyOS XPM 对失信 ELF 的 exec 拒绝，不是权限位问题（chmod 无效）。
  本轮改走去外部 tar 路线：`source()` 改纯 Python
 （`download` + `check_sha256` + `tarfile.open(r:gz)` 手动 strip_root，
  zutils/1.15 同款先例），URL/sha256 不变；`_find_ar` 降级 harmonybrew
  候选（优先 hnp 同目录 + /usr/bin + /bin）；`build()` 首行加非致命
  `HOST_TAR_PROBE`（候选存在性 + `--version` rc + 纯 Python 声明）供下轮
  取证。不跳过任何测试，产物语义不变。
