# xastir 2.2.4 适配笔记

## 编译环境
- 构建系统: autotools（上游发布物无 configure，需 aclocal+autoheader+autoconf+automake 引导）
- 编译日期: 2026-10-13
- 编译器: clang 15（/data/service/hnp/bin/clang，aarch64-linux-ohos）
- 状态: built（本地 `conan create --build=missing` 全绿：build → make check → package → test_package 六组断言全过；CI 待跑）

## 编译步骤

1. 源码：GitHub `Release-2.2.4` tag tarball（SourceForge 无可下载资产），sha256
   `cc521b8590bacc8d1f1f99a6596660c46174f7c809d6ecbbbf4b8dfa57a68419`。
2. bootstrap（build() 内，全部显式解释器调用）：
   - `mkdir m4`（ACLOCAL_AMFLAGS=-I m4 指向树中不存在的目录，必须先创建）
   - aclocal：conan automake/1.19 的 `bin/aclocal` 包装脚本以 `sh <wrapper>` 调用
     （包装脚本再 exec PATH 里的 hnp perl），ACLOCAL_PATH 带上 srcdir/m4
   - autoheader / autoconf：系统 hnp 2.72（可直接 exec）
   - automake：`sh <wrapper> --add-missing --copy --no-force`
3. 补丁（patches/，close-archive 规范化为逐文件补丁，portability；全部为**能力判据**，
   不含任何平台身份宏）：
   - configure.ac：`AC_CHECK_FUNCS([pthread_cancel pthread_testcancel])` —— POSIX 线程
     取消是可选能力，探测而非假定（ACX_PTHREAD 已把 PTHREAD_LIBS 并入 LIBS，glibc 上
     该探测能正确命中；OHOS 实测 `checking for pthread_cancel... no`）
   - interface.c：仅对 `pthread_testcancel`（纯取消检查点，无待取消请求时本就是 no-op）
     用 `#ifndef HAVE_PTHREAD_TESTCANCEL` 降级为 no-op；3 处 `pthread_cancel` **调用点**
     用 `#ifdef HAVE_PTHREAD_CANCEL` 守卫——能力缺失时不伪造"取消成功"的返回值，而是
     不发起取消请求（这些线程都自行 `pthread_detach`、从不被 join，循环轮询端口状态/
     描述符，端口关闭后经正常条件退出）
   - x_spider.c 7 处 `#ifdef __linux__` → `#if defined(__linux__) && defined(__GLIBC__)`
     （glibc setproctitle 模拟引用 glibc 专有全局 `__progname/__progname_full`；判据是
     C 库实现能力 `__GLIBC__`，而非内核身份——OHOS 的 clang 同样定义 `__linux__`）
   - main.c 5 处 `rindex(` → `strrchr(`（BSD 遗留名，非所有 C 库都提供；标准等价物）
4. configure：`sh configure`（E232）+ `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`
   （config.guess 在 worker 上既写不了临时文件也认不出 HarmonyOS）+
   `ac_cv_func_malloc_0_nonnull=yes`（AC_FUNC_MALLOC 的 rpl_malloc 规避）+
   `--without-graphicsmagick --without-imagemagick`（上游硬性拒绝 MagickLibVersion>0x0700，
   registry 的 imagemagick/7.1.2.29=0x712；GraphicsMagick 未发布）+
   `--without-festival --without-gpsman`（worker 无对应运行时）。
   **Nominatim 地理编码保持启用**：cjson/1.7.19 已发布于制品仓，configure 实测
   `checking for cjson/cJSON.h... yes` / `checking for cJSON_Parse in -lcjson... yes`，
   因此上游的 nominatim 测试组（12 项 autotest + test_nominatim 程序）一并纳入构建与执行。
   Berkeley DB 探测名单（db-18.1…db50）不含裸 `db`，berkeley-db/4.8.30 只发 libdb.a →
   toolchain env 预置 `LIBS=-ldb` 让 AC_SEARCH_LIBS 的 none-required 分支命中（USE_MAP_CACHE=1）。
5. make -j1；make check（见下）。
6. package()：copy() 显式落 bin/{xastir,callpass}、share/xastir/{config,symbols,help,scripts}、
   share/man/man1/{xastir,callpass,xastir_udp_client,testdbfawk}.1、licenses/COPYING，
   再做存在性大声校验；上游 `make install DESTDIR=…` 仅作证据性跟踪输出（HMDFS 上
   install-sh 不可执行，twclock/dinotrace 先例）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `umask 077 && mktemp -d` 建的目录里创建文件 Permission denied（config.guess 的 dummy.c、config.status 的 confXXXX/subs1.awk） | HMDFS 对 0700 目录（实际呈现 drwx--S---）拒绝任何写入，即使同进程刚创建它 | 生成 configure 后将 `umask 077` 全量替换为 `umask 022`（含嵌入的 config.status 模板；twclock 先例）；`--build=` 显式三元组绕过 config.guess |
| 2 | 链接期 -lcurl/-lpcre2-8 解析到 worker 前缀 /storage/Users/currentUser/usr/local/lib 的旧版（SONAME libcurl.so.4、共享 libpcre2-8.so.0），运行期 loader 找不到这些 soname → SIGSEGV | OHOS worker shell 预设 `LDFLAGS=-L<worker>/usr/local/lib`、`CPPFLAGS=-I<worker>/usr/local/include`，conan 环境组合保留预设值在先，append 追加在后 | generate() 里用 `environment.prepend()` 把 E050 链接视图与依赖 -L/-I 放到最前（worker 前缀退化为无害的尾部兜底）；test_package 反向断言 DT_NEEDED 不含 libcurl.so.4/libpcre2-8.so.0 |
| 3 | libtiff/libjpeg/libwebp/zstd/libxau/libxdmcp 包内 .so 符号链接节点 stat() EACCES，`-ltiff` 解析失败、运行期 soname 不可满足 | HMDFS tar 解出的符号链接节点跨任务标签不可读（E050 已有条目） | generate() 构建私有"链接视图"：闭包内真实文件直接拷贝、不可读节点以最高版本可读兄弟文件按节点名重建；视图放 -L 首位与 LD_LIBRARY_PATH 首位（make check 的测试二进制真实执行）。test_package 复刻同一视图 |
| 4 | 无显示器下 xastir 与最小 XtOpenDisplay 程序均以 SIGSEGV 静默死亡，无 "Can't open display" | libXt/1.3.1 在 OHOS 上的无显示错误路径自身崩溃（8 行最小程序可独立复现；与依赖闭包无关——musl 预先重定位，无任何 loader 诊断） | 消费者测试按 twclock 矩阵适配：真正的断言是"零加载器诊断 + 非零退出"，接受上游显示错误文本或信号死亡两种形态；文档化为本机 libXt 平台缺陷 |
| 5 | automake/1.19 报 `'settings.os.version' value not defined` | 构建侧 profile 未定义 os.version（remote 的 automake recipe settings 含 os.version） | 用 CI 同款 profile 双上下文 `-pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=…`（与 ci/conan/build_and_test.sh 一致，os.version=6.0） |
| 6 | conandata patches 字典格式导出后 patches/ 目录不进 export（补丁静默不应用） | 本 OHOS conan 的 export_conandata_patches 只认版本键控格式 `patches: {"2.2.4": [...]}` | conandata.yml 改用版本键控 + patch_file/patch_type 元数据格式 |
| 7 | config/ 的 5 个语言变体规则直接 exec `$(top_srcdir)/scripts/lang*.pl`（126 错误）、src/ 的 XastirGitStamp.sh 同类 | HMDFS 脚本 execve 不可用（E232） | configure 后对生成的 Makefile 做 E232 改写：recipe 行加 `perl`/`sh` 显式解释器 |
| 8 | `--build` 缺省时 config.guess 失败 | HMDFS 拒绝其临时写入 + 不认识 HarmonyOS | 显式 `--build=aarch64-linux-ohos`（aalib 先例） |

## 源码修改

- `patches/0001-src-interface.c.patch`、`patches/0002-src-main.c.patch`、`patches/0003-src-x_spider.c.patch`（原合成单补丁经 close-archive 逐文件规范化；详见上表第 3 步与 conandata.yml 描述）。

## 依赖版本

motif/2.3.8（带 libxt/1.3.1、libxext/6.4.0.1、libx11/1.8.13、libice/1.1.2、libsm/1.2.6、
libxau/1.0.11、libxdmcp/1.1.5、libxcb/1.17.0、xorgproto/2025.1、xtrans/1.6.0）、
libxpm/3.5.17、libgeotiff/1.7.4（libtiff/4.7.2、proj/9.3.1.1、libjpeg-turbo/3.2.0、
libwebp/1.6.0、zstd/1.5.7、libz 与 sqlite3 经 proj）、shapelib/1.5.0、pcre2/10.48（静态）、
libax25/0.0.12-rc5、curl/8.15.0（openssl/brotli 内嵌）、berkeley-db/4.8.30（静态 libdb.a）、
zlib/1.3.1.1（顶层 force=True：curl pin 1.3.1.1、libax25 pin 1.3.1，收敛必需）。
构建侧：automake/1.19（tool_requires）；autoconf/autoheader/autom4te 用 hnp 系统 2.72。

### 依赖图注意事项（CI 冷缓存）
- motif force libx11/1.8.13 轨道 + zlib/1.3.1.1 force 组合下，libxext/6.4.0.1 与
  libxpm/3.5.17 的 package_id 均为 eab79208…（libx11/6.4.0/zlib/1.3.1 的已发布二进制
  不在此轨道）。twclock 的 CI 已证明该轨道可从源码重建（libxext eab79208 有缓存命中），
  libxpm 同类风险——两者均为小体量 X11 库，CI 可从源码编译。

## 验证结果

```bash
python3 -m conans.conan create archives/x/xastir/2.2.4 \
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
# → xastir/2.2.4: Package '09a58d77e0b6fe964a536f8fc71cc441ba758579' created
# 上游 make check：All 242 tests were successful.（CHECK_EXIT=0）
# test_package：6 组断言全 PASS（callpass×2、headless、DT_NEEDED×2、数据树）
```

### R51 上游测试清点
- `tests/Makefile.am` check_PROGRAMS：test_interface_helpers、test_db、test_object_utils、
  test_output_my_aprs_data、test_util、test_objects，外加条件项 test_nominatim（HAVE_NOMINATIM，
  本配方启用 Nominatim 故一并构建）= **7 个程序**（均链接真实 src/*.c 对象）。
- autotest testsuite（AC_CONFIG_TESTDIR，make check 时由系统 autom4te 生成并执行）：
  db 30 + interface_helpers 1 + nominatim 12 + object_utils 118 + objects 42 +
  output_my_aprs_data 23 + util 16 = **242 项**。
- 实测 **242/242 通过**（含 nominatim 组 231–242，无跳过）；原始输出逐字进构建日志（[upstream-test] 行）。
- 无 X 显示器时 xastir 主程序不能启动：消费者负测试按"零 loader 诊断 + 非零退出"
  断言（libXt 无显示路径平台缺陷，见上表 #4）。
- callpass 作正向功能断言（源码为纯 C、不调用任何 Xt/Xm 显示路径，在无显示器环境仍可真实执行；但按上游链接规则它与 xastir 共用同一组 LIBS 闭包）：4 呼号 passcode 与独立 Python 复算一致。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/xastir | ~14 MB | 主程序（未 strip） |
| bin/callpass | ~30 KB | APRS passcode 计算器（源码纯 C、不开显示，作测试正路径） |
| share/xastir/{config,symbols,help,scripts} | ~2 MB | 运行数据树（65 dbfawk、11 sys、11 xbm、32 pl、TNC 模板等） |
| share/man/man1/*.1 | 4 个 | xastir/callpass/xastir_udp_client/testdbfawk |

## 注意事项

- **worker 前缀劫持（最重要）**：worker shell 预设的 `LDFLAGS=-L<worker>/usr/local/lib`
  含旧 libcurl.so.4 与共享 libpcre2-8.so.0。任何 append 追加的 -L 都排在它后面，
  `-lcurl`/`-lpcre2-8` 会被它吃掉。配方必须 prepend；test_package 已有 DT_NEEDED
  反向断言兜底。
- **libXt/1.3.1 无显示错误路径 SIGSEGV**：最小 8 行 XtOpenDisplay(NULL) 程序在
  DISPLAY 取消下同样静默 SIGSEGV（零输出、零 loader 诊断）。所有 Xt 应用的
  headless 消费者测试都应按"零 loader 诊断 + 非零退出"断言而非等待错误文本。
- **HMDFS 0700 目录不可写**：autoconf 全家（config.guess/config.status/autom4te 生成的
  testsuite）都会踩 `umask 077 && mktemp -d`；sed 成 022 可解。
- **pthread 取消能力探测（非平台宏）**：POSIX 线程取消是可选能力，OHOS libc 不提供。
  配方以 `AC_CHECK_FUNCS` 探测出 `HAVE_PTHREAD_CANCEL`/`HAVE_PTHREAD_TESTCANCEL`，
  仅对取消检查点降级为 no-op，并守卫 3 处取消调用点——不伪造取消成功。xastir 的
  net_connect/read/write 三个线程都自行 `pthread_detach(pthread_self())` 且**从不被
  join**（源码内无 pthread_join 调用），循环轮询端口状态与描述符，因此关闭接口时线程
  经正常条件退出；取消提前退出这一条路径在 OHOS 上不可用（线程可能延迟退出而非立即
  被杀）。地图显示与网络路径不受影响。
- **make install 不可作打包路径**：install-sh 在 HMDFS 不可执行；copy() 显式落盘 +
  大声校验（twclock/dinotrace 先例）。
- 本机 conan 缓存中 libxau/1.0.11 曾被坏包覆盖后做过缓存 DB 修复（指向完整 1.0.12
  文件夹，pkgid 相同）；如遇 -lXau 失败先查该包是否被重新下载。
---

**编译结束**: 2026-10-13 19:30
**最终状态**: built


## 知识收获

- ✅ xastir 发布物无 configure：bootstrap 全链（mkdir m4 + aclocal/autoheader/autoconf/automake 经显式解释器）+ conandata 版本键控补丁格式 + zlib force 收敛图 + Magick 0x0700 上限绕过 + LIBS=-ldb 预置（ref: xastir-2.2.4-ohos-bootstrap-magick-bdb-zlib-graph）
- ✅ worker 预设 LDFLAGS 的 -L 劫持必须 environment.prepend() 抢占；HMDFS 0700 mktemp 目录写入全拒（umask 077→022）；libXt/1.3.1 无显示错误路径自身 SIGSEGV（headless 断言 = 零 loader 诊断 + 非零退出）；W3 的 zsh 需 TMPPREFIX 指向可写目录（ref: xastir-2.2.4-ohos-worker-ldflags-prepend-umask0700-xt-displayless）


## 验证证据摘要（原始日志不入库）

> 评审规则第 19 条禁止在 PR 中提交 `*.log`；因此本归档**不提交原始构建日志**，
> 证据以「可复现命令 + 关键输出」摘要形式记录（完整输出见平台 CI 运行日志）。

1. `python3 -m conans.conan create archives/x/xastir/2.2.4 -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing`
   - `Package 'd79516ea05581c78aa747ca533c5ce80990c21f5' created`
   - configure 关键行：`checking for cjson/cJSON.h... yes`、`checking for cJSON_Parse in -lcjson... yes`、`checking for pthread_cancel... no`、`checking for pthread_testcancel... no`
   - `make check`：**`All 242 tests were successful.`**（`CHECK_EXIT=0`，无 skipped 行；测试编号 231–242 为 Nominatim 组）
   - 7 个 check_PROGRAMS 全部构建（含 `test_nominatim`）
   - test_package：6 行 `PASS:` + `=== xastir 2.2.4 consumer test: ALL PASS ===`
2. `CI_PACKAGES="archives/x/xastir/2.2.4" zsh ci/conan/build_and_test.sh archives/x/xastir/2.2.4`
   - `JC_RESULT=pass`（Junk Files: 0）、`L0_RESULT=pass`、`L1_RESULT=pass`、`L4_RESULT=pass`、`L5_RESULT=pass`、`Pass rate: 100.0% (1/1)`
3. sha256 独立复算：`cc521b8590bacc8d1f1f99a6596660c46174f7c809d6ecbbbf4b8dfa57a68419`（与 conandata.yml 一致）
4. 合规自检：patches/ 新增行无 `__OHOS__`（PF5/R8）；conandata.yml 仅保留官方 URL（R39/PF7，镜像 fallback 交由 CI 追加）
