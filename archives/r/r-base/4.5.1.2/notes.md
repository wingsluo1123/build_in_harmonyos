# r-base 4.5.1 HarmonyOS 适配笔记

## 范围

使用 CRAN 官方 R 4.5.1 源码，在 OHOS aarch64 设备原生构建。首轮关闭当前设备无完整验证条件的 X11、Tcl/Tk、Java、readline、recommended packages、ICU 和图形格式依赖。

## 构建策略

- 构建树、staging 和 TMPDIR 放在 `/data/storage/el2/base`。
- C/C++ 使用设备 HNP clang；Fortran 使用 `flang-ohos/20.1.0`。
- 上游测试入口为 `make -j1 check`。
- test_package 真实执行 R 脚本，覆盖版本、算术、PCRE2、矩阵、gzip 和 iconv。

## 当前状态

Round 12 设备完整 CI 已通过；Web Review 01 指出的可移动依赖与 TLS 信任链问题正在 Round 13 修复，最终状态以 Round 13 权威日志为准。

## Round 3 libcurl 接线

从 Conan curl 及其传递依赖的 cpp_info 动态构造 CURL_CPPFLAGS/CURL_LIBS，不写入缓存绝对路径；configure 前编译并运行 curl_https_probe.c，必须输出 CURL_HTTPS_CONSUMER=PASS。

## Round 4 alignof 能力兼容

截至 2026-08-08 检查 R 官方 SVN trunk、R-4-5-branch，以及 CRAN R 4.5.2、4.5.3、4.6.0、4.6.1，`dcigettext.c` 仍保留空的 C23 分支，没有可回移的正式上游修复。本版本采用编译器能力/版本守卫：仅 Clang 18 之前且 C23 分支中未定义 `alignof` 时，将其映射为标准 `_Alignof`；不按 OHOS 平台名分支，不影响 Clang 18+、GCC 和旧 C 标准路径。

## Round 5 权威本地时区契约

设备只读调查确认 `/usr/bin/param get persist.time.timezone` 返回 `Asia/Shanghai`；系统 `/system/etc/zoneinfo/tzdata` 为 OpenHarmony 打包格式，不是 R 可直接遍历的 Olson 目录。R 官方源码自带 `src/extra/tzone/zoneinfo.zip`（含 `zoneinfo/Asia/Shanghai`），因此启用 `--with-internal-tzcode`，以 R 自带、版本固定的 IANA 数据库作为 TZDIR 能力来源。最小 patch 在传统发现链前，仅当 `param` 命令存在、返回单一非空 IANA 名称且该名称在活动 tzdir 中真实存在时接受并缓存；否则透明回退原上游逻辑。未硬编码 `Asia/Shanghai` 或 UTC。

## Round 6 tzdir 候选优先级

Round 5 证明 `/etc/zoneinfo` 目录虽存在，但没有 `Asia/Shanghai` 展开文件，会遮蔽 R internal zoneinfo。0003 patch 改为先读取权威 parameter 名称，再按“R internal zoneinfo → 显式 TZDIR → 标准系统目录”的顺序，仅选择真实包含该 IANA 文件的候选，并将选中目录写入 TZDIR。具体时区值仍来自设备 parameter，未固定 TZ。


## Round 7–12 上游测试与启动器闭环

采用设备原生 `make -j1 check`。补丁 0004 保留 pipe `close()` 状态 oracle，0005 回移 R trunk r88881 的 subnormal `pretty()` 数值性质，0006 让 public/internal `bin/R` 从相邻完整布局解析可移动 R home。Round 12 完整 CI exit 0，consumer 六个功能域通过。

## Round 13 可移动运行时与 TLS 契约

最终 package 不再依赖构建机 Conan cache：`ldpaths` 只加入 `${R_HOME}/lib`，package 内复制运行时所需 `libcurl.so`，并扫描拒绝 `/storage/Users/currentUser`、`.conan2` 与 `.conan-build-r-base`。`R_SHARE_DIR`、`R_INCLUDE_DIR`、`R_DOC_DIR` 均从运行时验证后的 R home 派生。package 自带设备系统的公开 CA bundle 副本，launcher 仅在用户未显式设置 `CURL_CA_BUNDLE` 时选用它，未关闭 peer/host verification。

consumer 将最终 package 复制到不同绝对路径，在清空 R_HOME/RHOME、资源目录、CA 和 LD_LIBRARY_PATH 等环境后，使用移动副本验证 R、Rscript、RHOME、share/include/doc、PCRE、gzip、iconv、matrix 和真实 CRAN HTTPS，并核验全部 ELF NEEDED/RPATH/RUNPATH。测试不依赖原 package 或原依赖 cache 的运行时路径。

本归档只承诺 R 解释器、基础运行时和 HTTPS consumer 能力。清理后的 Makeconf 不再提供构建机依赖与 Fortran 工具链路径，因此不声明移动包可用于编译下游 C/Fortran R 扩展；该限制是显式能力边界，不以失效配置冒充支持。

## Round 14-16 移动运行时与 Rprof 修复

Round 14-15 完成静态 Flang runtime 污染处理（改用远端 external OpenBLAS 精确 binary）、私有 curl prefix-map 构建与 OpenSSL compiler metadata 精确分类，internet.R 真实 HTTPS OK。

## Round 16 修复三条新轴：Rprof memory profiling 空事件（0008：ITIMER_PROF 初始延迟异常探测，回退 RPE_ELAPSED ProfileThread）；test_package 移动后 libopenblas.so.0 SONAME 缺失（conanfile 补充复制）；moved-r-base 的 R.home("share") 固化 //lib/R/share（0009：Makefile.in install sed 对资源目录改用范围限定替换）。Round 16 retry-03 完整 CI exit 0，全部 marker PASS。

## 4.5.1.2 下游 libR 共享库修复（R37 后缀版本）

本版本在 4.5.1.1 基础上唯一的功能变更是新增 `--enable-R-shlib`，
产出 `lib/R/lib/libR.so`，解除下游 R 生态包（Rserve 等）configure 阶段的
`R was configured without --enable-R-shlib` 阻塞。

### 配方变更

1. configure 新增 `--enable-R-shlib`；R 生成 `lib/pkgconfig/libR.pc` 会内嵌
   全部构建期依赖的 `-L` 绝对路径（conan cache / data storage），新增
   `_sanitize_libR_pkgconfig()` 仅保留可移动的 `${rlibdir}` 条目，下游依赖
   解析走 conan requirements 与打包内运行时。
2. 4.5.1.1 的其他 patch、configure 选项与依赖约束原样保留。

### test_package 修复（继承 4.5.1.1 Round 17 结论）

4.5.1.2 首稿基于 4.5.1 基线创建，未继承 4.5.1.1 的 test_package 可移植性
修复（知识 E545 / E546），本地复验暴露并修复三处：

1. `conanfile.py` test() 补 `try/finally` 无条件 `rmtree(moved-r-base)`——
   防止被测包副本（约 90MB / 2000+ 文件）污染归档（E546）。
2. `run_test.sh` 采用 4.5.1.1 版：cache 根改由 `CONAN_HOME` 推导、缺失时
   跳过遮蔽而非 `stat` 直接中止；`.harmonybrew` 根仅在存在时遮蔽（E545）。
3. `test_package/MANIFEST.yml` package 字段由错误的 `r-base/4.5.1` 修正为
   `r-base/4.5.1.2`。

### run_test.sh 的 ELF 扫描白名单对齐

复验发现 openssl/3.5.6.1 发布二进制的 libcrypto.a 自带构建信息串
`compiler: clang --target=aarch64-linux-ohos ... -I$HOME/usr/local/include`
（OpenSSL 自身将编译命令烘焙进二进制，位于 .rodata，紧邻 OpenSSL 版本串），
静态链入 libcurl.so 后被 run_test.sh 的原始 `grep -R -a -E "$HOME|..."`
命中而误报"不可移动"。conanfile `_reject_build_paths` 已对该精确字符串
设白名单（与 4.5.1.1 相同），run_test.sh 现与之语义对齐：非 ELF 文件保留
原始路径扫描；ELF 文件的运行时路径违规由 readelf -d 的
NEEDED/RPATH/RUNPATH 闭包检查覆盖，构建元数据字符串由配方级
`_reject_build_paths` 字节扫描（含白名单）覆盖。

### 缓存残缺包教训

本地复验还发现 conan 缓存中 r-base/4.5.1.2 的二进制包为残缺副本
（package() copytree 被中断，缺整棵 `lib/R/bin/`，conan 仍视为已安装，
测试以 `bin/R RHOME` 返回 `//lib/R` 失败）。`conan remove --binaries -c`
后强制从源码全量重建为权威验证。教训：缓存命中不等于产物完整，W3 验证
前的二进制缓存若来自中断运行必须清除。

## Round 17（4.5.1.2 CI 重试修复）

CI #91778（PR #15348）私有 curl ninja 构建在 157/187 处报
`/bin/sh: can't fork - try again`（fork EAGAIN，设备并发负载下的
瞬时资源故障，非代码/网络问题；CI 诊断的"网络问题"为误分类）。
ninja 为增量构建，修复方案：`_build_private_curl` 对 `cmake --build -j2`
增加最多 3 次重试（退避 5/10s），重试从断点续建；非失败分支不变。

## Round 18（CI #94798 复盘：瞬态 flake + javaconf 固化路径修复）

CI #94798（PR #15348）在 `make -j1` 的 `src/scripts`（R.fe / install-cmds）
处静默 Error 1。本机复现两轮：第一轮 make 阶段顺利通过（证实 CI 报错为设备
并发负载下的瞬态故障，与 Round 17 fork-EAGAIN 同类；CI 诊断的“网络问题”
为误分类——源码经 pre-download 通道实际已成功获取）；但第一轮在后续
`package()` 阶段暴露真实缺陷：`_reject_build_paths` 检出
`lib/R/etc/javaconf` 固化了构建机 JDK 绝对路径
（`JAVA_HOME=/storage/Users/currentUser/bishengjdk17`——configure 即使
`--disable-java` 也会写入探测到的 JAVA_HOME 默认值）。

修复：`_prepare_relocatable_runtime()` 新增 javaconf 清理，与 Makeconf
清理同构——命中构建机路径 token 的行，`JAVA_HOME` 重写为空默认
`: ${JAVA_HOME=}`，其余行替换为注释。Java 支持未启用，该变量为惰性
默认值，重写不影响任何运行行为。随后第二轮本机完整 CI exit 0。

## Round 18 本机完整 CI 证据（exit 0）

- L0-L5 全 pass（L4 对 0004 补丁危险函数为既有 warn，非阻塞）。
- 上游 `make -j1 check`：40 项 R 回归脚本全部 OK，Examples 对比 OK
  （tools-Ex 1 项 NOTE 为无 teTeX 环境的平台差异记录项，非失败）。
- test_package：`R_BASE_HTTPS/RSCRIPT/E2E_CONSUMER/CACHE_MASK/
  RELOCATION_NEGATIVE_TEST` 全 PASS，consumer 断言 8/8。
- L1e 负向破坏性测试确认 test 实质依赖 r-base。

## 结束

最终状态：built —— 4.5.1.2 本地 W3 全量 conan create 从源码构建通过，
test_package 移动性/ELF 闭包/负向检查全部 PASS。
---

**编译结束**: 2026-10-16 11:59
**最终状态**: built
