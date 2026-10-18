# sleuthkit 4.12.1 适配笔记(【依赖项】任务,osquery contrib-9235 的依赖)

> Windows 阶段(W0 依赖分析 + 配方/补丁/测试编写)产出。OHOS 真机结论一律以
> MateBook 验证为准;本文件随验证结果更新。取代旧 stub 的 notes.md
> (旧文件描述的 5 个补丁基于另一份源码快照,已废弃,见下)。

## 任务定位

osquery(路径 C,contrib-9235)的文件取证表依赖 sleuthkit;制品仓
archives/ 仅有 stub(manifest+notes+旧补丁,无 conanfile),PF4 依赖闸
要求补齐本包。本任务为独立【依赖项】任务,分支 `feat/sleuthkit-4.12.1`。

## 源码与查重

- 官方 release tarball:github.com/sleuthkit/sleuthkit release
  sleuthkit-4.12.1,sha256
  `6b2de0baabc6a38429a33993114ca3820329b477d5038cbf45fcf69fca8addfd`
  (本机下载实测,3768424 字节,解包目录 sleuthkit-4.12.1/)。
- archives/ 上游查重:仅本 stub 目录,无已归档同名库/版本;L0j 口径待
  MateBook `conan download` 复核。
- 语言:C/C++(autotools 构建)。

## 旧 stub 补丁为何全部重做

stub 的 0001-0005 由某次 device-side 构建生成,但其基底是另一份
4.12.1 源码快照(config/config.guess 时间戳 2021-06-03;官方 release
tarball 为 2021-08-14)。对官方 tarball 实测:5 个补丁中 4 个
(patch/fuzz)不能应用;唯一能应用的 0004 打在 configure 生成的
tsk/pool/Makefile 上,而 configure 运行前该文件不存在,等于无效。

新补丁集(全部最小 diff,`patch -p1 --dry-run` 对官方 tarball 全通过):

| 补丁 | 内容 | 依据 |
|---|---|---|
| 0001-ohos-config-sub-triplet.patch | config.sub 接受 `| ohos*` OS 与 `linux-ohos*` kernel-os | 设备三元组 aarch64-unknown-linux-ohos |
| 0002-configure-umask-022.patch | configure 两处 `umask 077` → `022`(24261/24266) | E114(HMDFS setgid,同 tarsnap/tnef) |
| 0003-remove-werror-pool-util.patch | tsk/pool 与 tsk/util 的 Makefile.am/.in 移除 `-Werror` | 旧 stub 笔记问题 #3;漏了 tsk/util,本次补齐 |

config.guess 不替换:用 `--build=aarch64-unknown-linux-ohos` 显式传
三元组即可跳过猜测(tarsnap 1.0.41 先例);0001 保证 configure 内部
canonicalization 接受该三元组(本机已验证 `sh config/config.sub
aarch64-unknown-linux-ohos` 回显,linux-gnu/musl/android 等常规三元组
不受影响)。

## 构建设计

- autotools + Conan 官方工具链(tarsnap 房风):AutotoolsToolchain +
  AutotoolsDeps(zlib 的 -I/-L/-l 经 conanbuild 环境注入,R33);
  in-source 构建(basic_layout);`make -j1`(E074 HMDFS jobserver)。
- 依赖:唯一默认启用且制品仓已有的是 zlib(TSK_OPT_DEP_CHECK,
  configure.ac:162)→ `requires("zlib/1.3.2")`。afflib/libewf/libbfio/
  libvhdi/libvmdk/libvslvm 用 `--without-*` 显式关闭(上游本就探测不到,
  显式化保证确定性);openssl 支持在 configure.ac:307-310 整段注释,
  非可用选项。
- 产物:libtsk(static+shared,libtool)+ 25 个 CLI 工具
  (fls/icat/mmls/img_stat/tsk_recover/srch_strings/...)。
  package_type=library,cpp_info.libs=["tsk"] → osquery 等库消费者
  经 CONFIG/变量均可链接。

## 上游测试的真实边界(如实说明)

`make check`(tests/Makefile.am):

- `TESTS = runtests.sh test_libraries.sh`(2 个,离线不可运行,原因具体):
  - runtests.sh 需 `$HOME/from_brian` 镜像集,上游源码注释明言
    "not public"(非公开,未随任何发布渠道提供);
  - test_libraries.sh 运行时从 Google Drive 下载磁盘镜像(离线不可达),
    且其 mmls 子测试依赖 libvmdk/libvhdi/libewf,本配方按确定性要求
    `--without-*` 关闭,即使有镜像也属空转。
- `check_PROGRAMS = read_apis fs_fname_apis fs_attrlist_apis
  fs_thread_test`(4 个,全部真实执行):main 均要求
  `argv[1]` = 文件系统镜像根目录,release tarball 不含任何磁盘镜像
  (tests/Makefile.am 预期的 data/ 目录未随包发布)。
  配方自带 **gen_upstream_fixtures.py**(纯 Python 标准库,仅
  struct/os/sys):在构建期按各测试断言生成 6 个合成 FAT12/16/32 +
  NTFS 镜像(fat12.dd、fat-img-kw.dd、fat32.dd、fe_test_1.img、
  ntfs-comp-1.img、ntfs-img-kw-1.dd),conanfile.py build() 编译后
  以下列方式真实运行,任一失败即 create 失败:
  - read_apis:6 个子测试(fat12 读 API、FAT slack 标记、FAT 恢复
    fe 镜像、NTFS fe、NTFS 压缩/稀疏、NTFS slack+ADS);
  - fs_fname_apis:fat12 与 fe NTFS 目录打开/遍历一致性(2 个);
  - fs_attrlist_apis:fat12(47/1)与 fe NTFS(35/3、9/7)(3 个);
  - fs_thread_test:fat32.dd 与 ntfs-comp-1.img 各一组,按上游
    runtests.sh 同型协议——单线程基准存 base.log,重跑后 diff
    确定性校验。
  合成镜像满足的断言均为上游测试源码中的具体检查(inode 号、
  内容偏移标记、属性数、ADS 名/ID);除这些内容断言外,上游测试
  本身是自洽性校验(walk 缓冲与 file_read 对比),通用合法镜像即可。
- 结论:上游 6 项中 4 项(check_PROGRAMS)离线真实执行,2 项 TESTS
  按上游设计不可离线运行(原因如上,非适配缺陷);执行数字以
  MateBook 真机 create 日志为准如实记录。

消费者测试(test_package,12 断言)覆盖真实使用面:

- 10 个核心工具 `-V`(真实执行,版本含 4.12.1);
- `img_stat` 真实打开自生成 1MiB raw 镜像(libtsk 镜像层);
- `srch_strings` 在镜像中找回预埋标记(内容检索)。

## Windows 已验证 / 留给 MateBook

Windows 已验证:

- sha256 实测一致;3 个新补丁对官方 tarball `patch -p1 --dry-run` 全过;
- 应用后 `sh config/config.sub aarch64-unknown-linux-ohos` 通过、
  常规三元组不回归、`umask 022` 生效、4 个文件 Werror 计数为 0;
- conanfile.py / conandata.yml / commands.json / manifest.yaml 语法
  检查(conan export、python -c json/yaml 解析);
- conan export 通过;`conan graph info`(隔离 CONAN_HOME + CI 口径
  OHOS profile,os=OHOS/6.0 armv8 clang15 libc++ cppstd17 Release)对
  ohpcd 远端全图解析通过;zlib/1.3.2#73f9291bb 二进制按 CI package_id
  在 ohpcd 直接 Download(R35 预验证;最终以 MateBook conan install
  为准);sleuthkit 本身 binary:false,真机源码构建;
- **round1 真机失败修复(2026-10-13)**:MateBook 探针定位配方缺
  export_sources()/apply_conandata_patches() 两件套,conandata 声明的
  3 个补丁从未应用,configure 首步拒绝 OHOS 三元组(rc=1);已补两件套
  并在本机以真实 conan source() 路径端到端核验(下载→解包→3 补丁全部
  应用→config.sub 通过 ohos 三元组→umask 022×2→Werror 零残留)。
  MateBook 探针口径:修复后 create rc=0、check_PROGRAMS 4/4、
  test_package 12/12(日志 ~/sleuthkit-verify-logs/create-fixed.log)。

MateBook 待验证(未在本机验证,不推断为通过):

1. R35:`conan download` 复核 zlib/1.3.2 二进制可得性
   (round1 已预验证:package_id 6b129b06… 从 ohpcd 真实重拉成功);
2. `conan create`:configure(zlib 探测经 AutotoolsDeps 注入是否命中)、
   make -j1、make install(探针已全绿,待正式 SHA 复跑);
3. check_PROGRAMS 四个测试二进制编译通过并**真实执行**(round4 新增
   gen_upstream_fixtures.py 生成合成镜像后运行;Windows 侧已用 MinGW
   本地构建的 libtsk + 上游测试源全量预验:read_apis 6/6 子测试、
   fs_fname_apis、fs_attrlist_apis、fs_thread_test fat/ntfs 确定性
   diff 全绿,见 2026-10-15 会话记录);
4. test_package 12 断言(探针 12/12;-V 输出格式风险未出现,断言无需改);
5. `ohc-run.py finish sleuthkit 4.12.1 built` → W4 审计 → 报告回传
   (round4 对新 SHA 执行)。

## 风险

- `-V` 断言依赖 TSK 工具统一的版本输出行为(源码逐个核对过用法串,
  但未本机运行);如个别工具 -V 行为不同,按实际输出收窄断言集。
- libtool 在 musl/OHOS 的 shared 库构建为通用路径,风险低;若 shared
  失败可退 --disable-shared(留给真机首轮判断)。
- osquery 侧消费接口(FindSleuthkit 桥接)在 osquery 配方中已按
  变量/thirdparty 目标三级 fallback 设计,与本包 cpp_info 对接。

---
**编译结束**: 2026-10-15 20:10
**最终状态**: built
