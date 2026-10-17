## PR 信息
- **三方库名称**：xastir
- **上游版本**：2.2.4
- **上游仓库地址**：https://github.com/Xastir/Xastir （发布物：Release-2.2.4 tag tarball；官网 https://xastir.org）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：knowledge/drafts/xastir-2.2.4-ohos-bootstrap-magick-bdb-zlib-graph、knowledge/drafts/xastir-2.2.4-ohos-worker-ldflags-prepend-umask0700-xt-displayless

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 7 | 来源：tests/Makefile.am 的 check_PROGRAMS —— test_interface_helpers / test_db / test_object_utils / test_output_my_aprs_data / test_util / test_objects + 条件项 test_nominatim（HAVE_NOMINATIM）；均链接真实 src/*.c 对象 |
| 集成测试 | 242 | 来源：autotest testsuite（tests/*.at，AC_CONFIG_TESTDIR）—— db 30 + interface_helpers 1 + nominatim 12 + object_utils 118 + objects 42 + output_my_aprs_data 23 + util 16 |
| 其他测试 | 0 | 无 |
| **合计** | **249** | 上游完整测试清单（含 Nominatim 组） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 7 | 不变 | 7 个 check_PROGRAMS 全部编译执行 |
| 集成测试 | 242 | 不变 | **242/242 通过**（CHECK_EXIT=0，无跳过），在 OHOS aarch64 worker 原生执行；测试编号 231–242 即 Nominatim 组 |
| 鸿蒙特有测试 | 6 | 新增 | test_package/test_xastir.sh 的 6 组消费者断言：callpass 哈希（4 呼号 vs 独立 Python 复算）、usage 横幅、headless 负测试、DT_NEEDED 正向 soname、DT_NEEDED 反向（无 worker 前缀 curl/pcre2）、运行数据树 |
| **合计** | **255** | **+6** | 上游 249 项 0 增 0 减（全部执行），另有 6 组鸿蒙消费者断言 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游 249 项测试的源码与用例零改动，全部原样执行。四个补丁只触及产品源码与构建脚本：
`src/interface.c`、`src/main.c`、`src/x_spider.c`、`configure.ac`（详见下方"补丁说明"）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

上游自带完整 autotest 测试套件（242 项）与 7 个 check_PROGRAMS（含 test_nominatim），全部纳入构建并实跑通过，无需补全。适配后另**新增** 6 组鸿蒙消费者断言（见上表"鸿蒙特有测试"行），用于验证**打包产物**在 OHOS 上的真实行为（执行打包后的二进制、走真实动态加载器），属于额外验证，而非补全上游测试缺口。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：249/249（100%）
- 新增测试用例通过率：6/6（100%）

### 编译验证
- 编译器: clang (aarch64-unknown-linux-ohos)
- 编译状态: 成功（conan create 全绿，package_id `d79516ea05581c78aa747ca533c5ce80990c21f5`）
- 构建系统: autotools（上游发布物无 configure，配方内 aclocal/autoheader/autoconf/automake 引导）
- 配置选项: `--build=aarch64-linux-ohos --host=aarch64-linux-ohos ac_cv_func_malloc_0_nonnull=yes --without-graphicsmagick --without-imagemagick --without-festival --without-gpsman`
  （**Nominatim 未禁用**：cjson/1.7.19 已发布于制品仓，configure 实测 `checking for cjson/cJSON.h... yes`、`checking for cJSON_Parse in -lcjson... yes`，故上游 nominatim 测试组 12 项 + test_nominatim 一并执行）

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | PASS | 构建系统: autotools, 状态: built |
| 产物存在性 | PASS | bin/xastir、bin/callpass、share/xastir/{config,symbols,help,scripts}、share/man/man1 ×4、licenses/COPYING |
| ELF 格式 | PASS | aarch64-unknown-linux-ohos |
| 运行测试 | 通过 | 上游 make check: **242/242 通过**（CHECK_EXIT=0，无跳过）；消费者测试 6/6 断言通过；跳过 0 |
| 动态依赖 | PASS | DT_NEEDED: libXm.so.4/libXt.so.6/libX11.so.6/libXext.so.6/libXpm.so.4/libSM.so.6/libICE.so.6/libcurl.so/libproj.so.25/libtiff.so.6/libgeotiff.so.5（另有 cjson 随闭包） |

### 补丁说明
全部补丁使用**能力判据**（configure 探测 / C 库实现宏），不含任何平台身份宏（R8）：

- `0004-configure.ac.patch`（portability）: `AC_CHECK_FUNCS([pthread_cancel pthread_testcancel])` —— POSIX 线程取消是可选能力，探测而非假定。（ACX_PTHREAD 已把 `PTHREAD_LIBS` 并入 `LIBS`，glibc 上该探测正确命中；OHOS 实测 `checking for pthread_cancel... no`。）
- `0001-src-interface.c.patch`（portability）: 能力缺失时的诚实降级——`pthread_testcancel`（纯取消检查点，无待取消请求时本就是 no-op）用 `#ifndef HAVE_PTHREAD_TESTCANCEL` 降级；3 处 `pthread_cancel` **调用点**用 `#ifdef HAVE_PTHREAD_CANCEL` 守卫，**不伪造“取消成功”的返回值**。net_connect/read/write 三个线程各自 `pthread_detach(pthread_self())` 且从不被 join（全树 `pthread_join` 仅存在于注释），循环轮询端口状态/描述符，端口关闭后经正常条件退出。
- `0003-src-x_spider.c.patch`（portability）: setproctitle 模拟引用 glibc 专有全局 `__progname`/`__progname_full`，判据用 C 库实现宏 `defined(__GLIBC__)`（7 处）——OHOS 的 clang 同样定义 `__linux__`，故不能只看内核身份。
- `0002-src-main.c.patch`（portability）: `rindex()` 是 BSD 遗留名，非所有 C 库都提供；改为标准等价物 `strrchr()`（5 处）。

### 依赖
- motif/2.3.8
- libxt/1.3.1
- libxext/6.4.0.1
- libxpm/3.5.17
- xorgproto/2025.1
- libgeotiff/1.7.4
- shapelib/1.5.0
- pcre2/10.48
- libax25/0.0.12-rc5
- curl/8.15.0
- cjson/1.7.19（Nominatim 地理编码）
- berkeley-db/4.8.30
- zlib/1.3.1.1

### 已知限制
1. ImageMagick/GraphicsMagick 栅格导入禁用——上游 `XASTIR_CHECK_IMAGEMAGICK` 对 `MagickLibVersion > 0x0700` 硬报错，制品仓仅有 imagemagick/7.1.2.29（0x712）、GraphicsMagick 未发布；GeoTIFF/shapelib 地图路径不受影响。
2. 线程取消为能力探测降级：OHOS libc 无 pthread_cancel，关闭 TNC/串口接口时线程经正常循环条件退出而非被立即取消（线程本就 detach、无 join）。
3. 本机 libXt/1.3.1 无显示错误路径自身 SIGSEGV（最小 8 行 `XtOpenDisplay(NULL,…)` 可独立复现，与被测应用无关），故 headless 消费者断言采用「零动态加载器诊断 + 非零退出」矩阵。
4. Festival/GPSMan 集成未启用（worker 无对应运行时）。Nominatim 已启用（cjson 已发布）。

### 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 tarball 无 configure，bootstrap 失败 | 发布物只含 configure.ac；`ACLOCAL_AMFLAGS=-I m4` 指向树中不存在的 m4/ | `mkdir m4`；aclocal/automake 经 conan automake/1.19 包装脚本以 `sh <wrapper>` 调用，autoheader/autoconf 用 hnp 系统 2.72；`sh configure` + 显式 `--build/--host` |
| 2 | 链接到 worker 前缀旧库，运行期 loader 找不到 soname → SIGSEGV | worker 登录 shell 预设 `LDFLAGS=-L<worker>/usr/local/lib`（含旧 libcurl.so.4 与共享 libpcre2-8.so.0）；conan 环境组合把预设置于 append 之前 | `environment.prepend()` 抢占 -L/-I 顺序；test_package 反向断言 DT_NEEDED 不含 libcurl.so.4/libpcre2-8.so.0 |
| 3 | `-ltiff` 解析失败、运行期 soname 不可满足 | E050：libtiff/libjpeg-turbo/libwebp/zstd/libxau/libxdmcp 包内符号链接节点 stat() EACCES | `generate()` 构建私有链接视图（不可读节点按最高版本可读兄弟文件重建），置于 `-L` 与 `LD_LIBRARY_PATH` 首位；test_package 复刻同视图 |
| 4 | 无显示器下 xastir 静默 SIGSEGV，无 “Can't open display” | libXt/1.3.1 在 OHOS 的无显示错误路径自身崩溃（与依赖闭包无关：musl 预先重定位，零 loader 诊断） | 消费者负测试按「零动态加载器诊断 + 非零退出」断言，接受显示错误文本或信号死亡；notes.md 记录 8 行最小复现 |
| 5 | automake/1.19 报 `'settings.os.version' value not defined` | 构建侧 profile 未定义 os.version（remote automake recipe 需要） | 构建/宿主双上下文统一用 `ci/conan/profiles/ohos-aarch64`（与 CI 同源） |
| 6 | 补丁静默未导出、未应用 | 本 OHOS conan 的 `export_conandata_patches` 只认版本键控字典 | conandata 改用 `patches: {"2.2.4": [...]}` + patch_file/patch_type 元数据 |
| 7 | config/ 语言变体规则与 XastirGitStamp.sh 执行报 126 | HMDFS 上脚本 execve 不可用（E232） | configure 后改写生成的 Makefile：规则行加显式 `perl`/`sh` 解释器 |
| 8 | config.guess 无法猜测构建类型 | HMDFS 拒绝其临时写入且不认识 HarmonyOS | 显式 `--build=aarch64-linux-ohos`；生成 configure 后 `umask 077`→`022`（HMDFS 0700 临时目录写入全拒） |
| 9 | 审阅指出补丁引入 `__OHOS__` 平台条件宏（R8 红线） | 用平台身份宏做条件编译，掩盖了「这是能力差异而非平台差异」 | 改为能力判据：`AC_CHECK_FUNCS` 探测线程取消能力并守卫调用点（不伪造取消成功）；`__progname/__progname_full` 用 `defined(__GLIBC__)`；补丁内 `__OHOS__` 宏归零 |
| 10 | CI JC 门失败：`.build-closed`/`.staging-verified` 被判垃圾文件 | 本地工具标记被跟踪入库（JC1 运行时状态文件 + JC5 未登记隐藏文件） | `git rm --cached` 解除跟踪（本地文件保留），JC 白名单外文件清零 |
| 11 | 规则 4 判「少报」：声明 236 < 上游实测 249 | 早前误以为 cjson 未发布而用 `--without-nominatim` 关闭 Nominatim，导致 12 项 autotest + test_nominatim 未纳入统计 | 核实 cjson/1.7.19 已发布 → 加入 `cjson/1.7.19` 依赖并移除 `--without-nominatim`；上游 **249 项全部实跑通过**，声明与实测一致 |

### 验证命令
```bash
# 本机构建 + 上游测试 + 消费者测试（OHOS aarch64 worker 原生）
python3 -m conans.conan create archives/x/xastir/2.2.4 \
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
# → Package 'd79516ea05581c78aa747ca533c5ce80990c21f5' created
# → 上游 make check：All 242 tests were successful.（CHECK_EXIT=0，无跳过）
# → test_package：6 组消费者断言全 PASS

# CI 同源脚本（JC/L0/L1/L2/L4/L5 全流程）
CI_PACKAGES="archives/x/xastir/2.2.4" zsh ci/conan/build_and_test.sh archives/x/xastir/2.2.4
# → JC=pass(Junk 0) / L0=pass / L1=pass / L4=pass / L5=pass，成功率 100%
```

---

## 补充说明

- **上游测试清点（R51）**：`tests/Makefile.am` 的 check_PROGRAMS 7 个（6 + 条件项 test_nominatim）+ autotest testsuite 242 项 = **249**；`make check` 在构建阶段原样执行，原始输出逐字进构建日志（`[upstream-test]` 行），测试编号 231–242 为 Nominatim 组。
- **Nominatim 启用说明**：cjson/1.7.19 已在制品仓发布；上游 configure 的 `AC_CHECK_HEADERS([cjson/cJSON.h])` + `AC_CHECK_LIB([cjson],[cJSON_Parse])` 在本配方 CPPFLAGS/LDFLAGS 下命中，`HAVE_NOMINATIM` 生效 → 测试组与测试程序全部纳入。Nominatim 测试为桩驱动（`test_nominatim_stubs.c`），不访问网络。
- **鸿蒙消费者断言说明**：`test_package/test_xastir.sh` 真实执行打包后的 `bin/callpass`（4 个呼号的 APRS passcode 与脚本内独立 Python 复算逐一比对）与 `bin/xastir`（无显示器负测试：零加载器诊断 + 非零退出），并用 `llvm-readelf -d` 校验 DT_NEEDED 正/反向 soname，最后校验运行数据树；移走 `bin/` 会使 (a)(b)(c) 全部失败（非桩测试）。
- **平台限制**：无 X server，GUI 无法交互验证；headless 断言形态见"已知限制"第 3 条。
- **验证证据**：按评审规则第 19 条（PR 禁止提交 `*.log`），本 PR **不提交原始构建日志**；证据以「可复现命令 + 关键输出」摘要形式记录在 `2.2.4/notes.md` 的「验证证据摘要」小节，完整输出见平台 CI 运行日志。
