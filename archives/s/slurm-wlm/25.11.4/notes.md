# slurm-wlm 25.11.4 适配笔记

## 编译环境

- 构建系统: autotools（SchedMD release tarball，自带预生成 `configure`）
- 编译日期: 2026-10-14（首轮全通）/ 2026-10-15（CI 失败修复后的复测）
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`）、clang++（llvm-ar）
- 目标: HarmonyOS PC / aarch64（`ci/conan/profiles/ohos-aarch64`，os.version 6.0，musl）
- 状态: built

## 版本说明

- 上游: https://www.schedmd.com/ （SchedMD，GPL-2.0-or-later），版本 `25.11.4`
- 源码: `https://download.schedmd.com/slurm/slurm-25.11.4.tar.bz2`
  sha256 `237f515adcb37b99ff6cb3e1fa81691a5f7188e94c3b6b495858b4eaecf6531d`（官方发布目录，R39）
- 首次适配，版本号沿用上游 `25.11.4`（R37）
- 必须用 release tarball：源码树里带着 `configure`/`Makefile.in`/`aclocal.m4`。
  HarmonyOS 主机只有 autoconf/m4，没有 automake/aclocal/libtoolize，
  GitHub tag 归档（只有 `configure.ac` + `Makefile.am`）在这台机器上无法 bootstrap。

## 编译步骤

```bash
# 配方内部（build()）：
tc = AutotoolsToolchain(self)
tc.extra_cflags += ["-include<build>/conan/slurm_musl_compat.h", "-D_GNU_SOURCE"]
tc.configure_args += [
  "--with-munge=<pkg>", "--with-hwloc=<pkg>", "--with-json=<pkg>",
  "--with-http-parser=<pkg>",
  "--build=aarch64-linux-gnu", "--host=aarch64-linux-gnu",
  "--without-rpath", "--disable-dependency-tracking",
  "--without-freeipmi", "--without-nvml", "--without-rsmi", "--without-mysql",
]
os.environ["PWD"] = build_folder            # HMDFS 上 getcwd() 失效（E114/E386）
os.environ["CONFIG_SHELL"] = "/data/service/hnp/bin/bash"
os.environ["CHECK_CFLAGS"] = "-I<check>/include -pthread"   # 短路 PKG_CHECK_MODULES
os.environ["CHECK_LIBS"]   = "-L<check>/lib -lcheck"
autotools.configure()                       # → HAVE_CHECK 生效
clang -c -O2 -fPIC musl_account_shim.c && llvm-ar rcs libmusl_account_shim.a ...
（_patch_makefile_libs()：给所有生成的 Makefile 的 LIBS 行追加垫片库 + -lncursesw）
make -j1 && make -j1 install                # R9 单 job
make -j1 -k check                           # 上游 41 个 libcheck 用例

conan create archives/s/slurm-wlm/25.11.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题（报错原文） | 根因 | 解决方案 |
|---|------------------|------|----------|
| 1 | `configure: working directory cannot be determined` | HMDFS 上 `getcwd()` 与 `pwd` 探针失效（E114/E386） | `build()`/`package()` 预置 `PWD`，并把 `CONFIG_SHELL` 指向设备上的 bash |
| 2 | `config.guess`/`config.sub` 不认 `aarch64-linux-ohos`（E007） | 随包 config.sub 是 2022 版，没有 `linux-ohos*` 分支 | `--build/--host=aarch64-linux-gnu`（CC/CXX/sysroot 仍来自 OHOS 工具链）；补丁 0001 仍保留 |
| 3 | `config.status: error: could not setup config files machinery` | HMDFS 给新目录加 setgid 位，`umask 077` 建出的临时目录不可用（E129/E011） | 补丁 0002：两处 `umask 077` → `022` |
| 4 | `cannot run C compiled programs`（configure 的 conftest） | 依赖的动态库不在 loader 搜索路径 | `build()` 里把各依赖 `cpp_info.libdirs` 全部并入 `LD_LIBRARY_PATH` |
| 5 | `unable to locate munge installation` | munge/hwloc/json-c/http-parser 只提供 `--with-<x>=PATH` 探测，不走 pkg-config | 显式传 `--with-munge/hwloc/json/http-parser/yaml=<dep.package_folder>` |
| 6 | `'sys/unistd.h' file not found` | `sys/unistd.h` 是 glibc 专有头 | 补丁 0003：改用 `<unistd.h>` |
| 7 | `undefined reference: res_nclose`（sacct） | musl 只有经典解析器接口，没有 `res_n*` 可重入族 | 补丁 0004：`res_ninit/res_nsearch/res_nclose` → `res_init/res_search/(void)0` |
| 8 | `cpu_set_t` 未定义（`src/common/xsched.h`） | musl 只有定义 `_GNU_SOURCE` 才暴露 `cpu_set_t`/`CPU_SET` | `tc.extra_cflags` 追加 `-D_GNU_SOURCE` |
| 9 | 链接期缺 `getpwent_r`/`getgrent_r`/`euidaccess`/`pthread_cancel*`/`inet_nsap_addr`/`canonicalize_file_name`/`get_current_dir_name`/`W_EXITCODE` | 这些是 glibc-only 符号，musl 未实现（族谱见知识条目 DRAFT-ohos-libc-missing-family-variant-entrypoints、musl-pthread-cancel-gap） | 「兼容头 + 垫片库」两件套：静态内联兼容头用 `-include` 强制注入每个 TU；`getpwent_r/getgrent_r/euidaccess/pthread_cancel*` 编译成 `libmusl_account_shim.a` 并追加到生成的 Makefile 的 `LIBS` 行尾 |
| 10 | `has undefined version libnuma_1.1`（lld） | 制品仓的 `libnuma.a` 带 glibc 符号版本，lld 解不开 | 移除 `numactl` 依赖（Slurm 对 NUMA 亲和是可选探测） |
| 11 | termcap 符号 `tgetflag`/`UP` 未定义（`sacctmgr`） | 不是缺库而是链接顺序：configure 生成的 `LIBS` 里 `-lncursesw` 位置在静态库之前 | `_patch_makefile_libs()` 把 `-L<ncurses>/lib -lncursesw` 追加到 `LIBS` 行尾 |
| 12 | `make LIBS="<多词>"` 传参无效（make 打印 usage） | Conan 的 Autotools 助手会把 `args` 拼成命令行，含空格的值被拆成 make 的目标/选项 | 改成遍历 build 目录、改写每个生成的 Makefile 的 `LIBS = ` 行（`make` 与 `make install` 都读它）；不手写、不提交生成物 |
| 13 | CMakeDeps 给消费者生成的 `slurm-wlm_INCLUDE_DIRS_RELEASE` / `slurm-wlm_LIBS_RELEASE` 为空，consumer 找不到 `slurm/slurm.h` | `package_type = "application"` 会剥离 headers/libs traits（知识 DRAFT-12592；用 20 行探针包在本 profile 上复现：`application` → 空，`library` → 有值；**与包名里的连字符无关**，此前以为是 `slurm-wlm` 带 `-` 所致） | 保持 `package_type = "application"`，`test_package` 显式指向安装树的 include/lib（见下一条：改成 library 反而破坏构建） |
| 13b | 按 DRAFT-12592 的建议把包型改成 `library` 后，`conan create` 变红：插件 .so 不产出 + `sacct` 链接报 `undefined symbol: _binary_help_txt_start` | Conan 的 `AutotoolsToolchain` 把**计算出的包类型**翻成 autotools 开关：`library` + `shared=False` → `PackageType.STATIC` → 注入 `--disable-shared --enable-static` → `enable_shared=no` / 生成的 `libtool` 里 `build_libtool_libs=no` → ①`-module` 插件（`lib/slurm/*.so`）不再产出 ②libtool 对"二进制 blob 伪 .lo"（`ld -r --format=binary` + `objcopy` 造的 `help.bino`）的归档不再收录 blob → 链接缺符号（新知识草稿 DRAFT-10718-…-conan-package-type-drives-autotools-shared-static-flags） | 回归 `package_type = "application"`（Conan 不加任何 shared/static 开关，autotools 保持 `enable_shared=yes`，一次构建同时得到 `.a` 与插件 `.so`）；实测两种配置的对照已写入 `reports/test-report.md §4.4` |
| 14 | `make check` 只跑 1 个用例（`log-test`），其余 40 个静默消失 | slurm 把 `testsuite/slurm_unit` 的 check 用例包在 `if HAVE_CHECK` 里，而 `HAVE_CHECK` 来自 `PKG_CHECK_MODULES([CHECK],[check >= 0.9.8])`；configure 时制品仓里没有 check（知识 DRAFT-10251 同型） | `build_requirements()` 里 `test_requires("check/0.15.2")`，并在 build() 里用 `CHECK_CFLAGS`/`CHECK_LIBS` 短路 pkg.m4 探测（知识 DRAFT-13952）；重跑 configure 后 41 条用例全部进入构建 |
| 15 | 全部 check 用例报 `check_msg.c:317: Unable to create temporary file for communication` | libcheck 的 fork 通信临时目录按 `TEMP` → `P_tmpdir`（musl 定义为 `/tmp`）→ `TMPDIR` 选择，设备 `/tmp` 为 root 拥有不可写（知识 DRAFT-E547/DRAFT-E571） | `TEMP` 指向构建目录下的可写目录 |
| 16 | `dns-test` 稳定报 `Test timeout expired` | libcheck 每用例默认 4 秒超时；该用例会真的调用名字服务（`sockaddr_to_string` → `getnameinfo`），解析器不可达时要等更久（知识草稿 DRAFT-10718-...-libcheck-default-timeout-nameservice-test） | `CK_DEFAULT_TIMEOUT=120`（对照组：单跑放大超时后 100% 通过） |
| 17 | `serializer-test`/`topology-test` 报 `PluginDir: .../serializer/yaml/.libs: No such file or directory` → `fatal: Unable to process configuration file` | 夹具里的 `PluginDir` 是**全量插件集合**，slurm 配置解析器要求每个存在的目录都要能加载；`serializer/yaml` 只在 configure 探测到 libyaml 时产出（知识草稿 DRAFT-10718-…-optional-dep-plugin-dir-upstream-tests） | 实测接上制品仓已发布的 `portable-libyaml/0.2.5`（`--with-yaml`，全树 `make` 绿、`serializer_yaml.so` 产出）后，失败面**下移**到 `dlopen` 插件时的加载器作用域差异（`slurm_get_log_level: symbol not found`，符号在 `libslurmfull.so` 中确实已导出），通过率不变；因此本包不引入该额外依赖，两条用例按平台限制如实计入 FAIL（见 test-report §4.3） |
| 18 | `ld.lld: error: target emulation unknown: -m or at least one .o file required` + `llvm-objcopy: error: 'certgen.sh.bino': No such file or directory`（`make[5]: *** [Makefile:858: certgen.sh.bino] Error 1`）—— 设备上全绿，**平台 CI 复现** | 上游 `make_ref.include` 把每个内嵌脚本 `<name>.txt` 转成可重定位对象时用的是 `$(LD) -r --format=binary`，而 `--format=binary` 是 **GNU ld 专有**的输入格式。设备上 `$(LD)` 解析到 GNU ld 2.45（hnp 里装了 binutils），所以本地一路绿灯；worker 的 hnf 工具链里 `$(LD)` 是 `ld.lld`、`$(OBJCOPY)` 是 `llvm-objcopy`，lld 直接拒绝该形式 → **内联这条规则的 13 个目标全部中断**（certgen、sacct、sacctmgr、sackd、scontrol、scrontab、scrun、sinfo、slurmctld、slurmd、slurmrestd、sprio、squeue） | 补丁 0005：用 `objcopy -I binary -O elf64-littleaarch64 -B aarch64` 生成**同样的** `_binary_<name>_start/_end/_size` 对象（`nm` 逐符号对照一致），并把 `--rename-section .data=.rodata,...` 合并进同一步；GNU objcopy 与 llvm-objcopy 都实现这条路径。因 OHOS 主机没有 automake 无法重生成 `Makefile.in`，把 automake 内联进 13 个 `Makefile.in` 的同一处规则一并改掉（`make_ref.include` 是源头，也改） |

## 源码修改

| 补丁 | 内容 | 行数 |
|------|------|------|
| `0001-config-sub-ohos.patch` | `auxdir/config.sub` 的 `maybe_os` 列表加入 `linux-ohos*`（保留；实际三元组已退化为 `aarch64-linux-gnu`） | 8 |
| `0002-configure-umask.patch` | `configure` 里两处 `umask 077` → `022`（HMDFS 的 setgid 目录） | 20 |
| `0003-sys-unistd-musl.patch` | 命名空间插件把 glibc 专有的 `<sys/unistd.h>` 换成 `<unistd.h>` | 8 |
| `0004-musl-resolver-shim.patch` | `res_ninit/res_nsearch/res_nclose` 三个 glibc-only 调用点改走 musl 的 `res_init/res_search`（`res_nclose` 无对应资源） | 22 |
| `0005-make-ref-binary-blob-objcopy.patch` | `.bino` 内嵌对象生成从 `ld -r --format=binary`（GNU ld 专有）换成 `objcopy -I binary -O elf64-littleaarch64 -B aarch64`：`make_ref.include` + 内联该规则的 13 个 `Makefile.in` | 168 |

配方侧另外生成两份**构建期**辅助文件（不是上游源码补丁，不落仓库）：

- `conan/slurm_musl_compat.h`：glibc-only 接口的静态内联兼容头（`-include` 强制注入）；
- `libmusl_account_shim.a`：`getpwent_r`/`getgrent_r`/`euidaccess`/`pthread_cancel*` 垫片，追加到生成的 Makefile 的 `LIBS` 行。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| munge | 0.5.16 | 认证/凭据插件 |
| hwloc | 2.14.0 | 拓扑与 CPU 绑定 |
| json-c | 0.18 | JSON 输出/解析 |
| http-parser | 2.9.4 | `slurmrestd` HTTP 解析 |
| readline | 8.3 | `scontrol`/`sacctmgr` 行编辑 |
| ncurses | 6.6 | termcap 符号（`tgetflag`/`UP`） |
| libcap | 2.78 | capability 检查 |
| libaio | 0.3.112.1 | 异步 IO 记账 |
| zlib | 1.3.1.1 | 传递依赖统一版本（libpng 分支原为 1.3.1） |
| check | 0.15.2 | **test_requires**：上游单元测试框架，不进交付依赖 |

传递依赖（由上述包带入）：cairo、fontconfig、freetype、libpng、pixman、libxml2、expat、bzip2、openssl。

## 验证结果

```bash
$ conan create archives/s/slurm-wlm/25.11.4 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 编译：CREATE_RC=0（包 slurm-wlm/25.11.4）

# 上游单元测试（build() 内 make -j1 -k check，日志内 SLURM-UPSTREAM-* 行）
SLURM-UPSTREAM-TESTS total=41 pass=37 fail=4 error=0 skip=0 rate=90.2%
# 未通过 4 条（均非适配缺陷，逐条原因见 reports/test-report.md §3.2/§4）：
#   backfill-test                        上游用例链接的 libslurmfull 不含 slurmctld 目标文件（40+ 符号）
#   serializer-test / topology-test      需要 serializer/yaml 插件；接上 portable-libyaml 后失败面下移到
#                                        插件 dlopen 的加载器作用域差异（已实测，通过率不变）
#   slurm_addto_id_char_list-test        设备 /etc/passwd 无当前 uid 条目，getpwuid() 返回 NULL

# 消费者用例（链接安装后的 libslurm 静态库，调用公开 API）
SLURM_CONSUMER_CHECKS=6 FAILURES=0
SLURM_CONSUMER_OK
```

## 交付物

| 目录/文件 | 说明 |
|-----------|------|
| `bin/` | 24 个可执行文件（slurmctld、slurmd、slurmdbd、sbatch、srun、squeue、sinfo、scontrol、sacct、sacctmgr、sreport ...） |
| `lib/libslurm.{a,so,so.44,so.44.0.0}` | 客户端库（消费者按 `-lslurm` 链接；`test_package` 走静态 `.a`） |
| `lib/slurm/*.so` | 调度/选择/序列化/认证/凭据等插件（`serializer/{json,url-encoded}`、`sched/{backfill,priority}`、`select/cons_tres`、`auth/munge`、`cred/munge`、`tls/none`、`hash/k12`、`certgen/script` …；`serializer/yaml` 未启用，见下） |
| `include/slurm/*.h` | 公开头文件（`slurm/slurm.h`、`slurm/slurm_version.h` ...） |
| `share/`、`licenses/` | man 手册、配置样例与 `COPYING` |

## 注意事项

1. 服务端（`slurmctld`/`slurmd`/`slurmdbd`）实际拉起集群还需要 munge key、`slurm.conf` 与
   状态目录权限；本次验证范围是"编译 + 上游单元测试 + 消费者链接调用"，未做多机集群联调。
2. 未启用 NUMA 亲和（`numactl` 缺席）；未启用 `freeipmi`/NVML/RSMI/MySQL 后端。
3. 上游 41 条用例中有 4 条在本平台稳定失败（`backfill-test`、`serializer-test`、`topology-test`、
   `slurm_addto_id_char_list-test`），原因均已定位到上游用例自身或平台环境（见 test-report §3.2/§4）；
   其余 37 条全部通过。
4. `slurm_addto_id_char_list-test` 依赖运行用户在 `/etc/passwd` 中有条目 —— 若评审机上换了
   一个有 passwd 条目的用户，该条会转 PASS（通过率随之上升）。
5. `serializer/yaml` 插件未启用（libyaml 是上游可选依赖，未接）：接上制品仓的
   `portable-libyaml/0.2.5` 可让该插件产出（已实测 `make` 全绿），但它无法让
   `serializer-test`/`topology-test` 通过（失败面下移到插件 dlopen 的加载器作用域差异），
   因此本 PR 不引入这个额外依赖；需要 YAML 输出的场景可后续单独升级该依赖。
