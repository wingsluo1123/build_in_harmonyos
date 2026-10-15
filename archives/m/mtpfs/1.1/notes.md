# mtpfs 1.1 适配笔记

## 身份与版本
- 上游: cjd/mtpfs（Chris Debenham），FUSE 用户态文件系统，把 MTP 设备挂载成本地目录。
- 上游无 tag/release，codeload master HEAD = 1177d6cf（AC_INIT 1.1）；
  版本精确的 1.1 规范发行包取 Debian 快照（snapshot.debian.org，2012-02-27 打包），
  sha256 = 1baf357de16995a5f0b5bc1b6833517a77456481d861cdba70f1ce1316ce4c1d。
- 产物: 仅 `mtpfs` 可执行文件（bin_PROGRAMS），无库 → R38 commands.json（type: tool）。

## W0 依赖清单（Windows 静态分析，2026-09-29）
| 依赖 | 版本 | 仓库 archives/ | 制品仓二进制 |
|---|---|---|---|
| libfuse (fuse 2.x API, FUSE_USE_VERSION=22) | 2.9.9 | ✅ conanfile.py | ✅ R35 全量 download rc=0（2026-10-15 真机） |
| libmtp | 1.1.21 | ✅ **已发布**（2026-10 由【依赖项】适配合入，MateBook 第 7 轮全链验证+审计 pass；配方已非旧格式） | ✅ R35 全量 download rc=0（2026-10-15 真机） |
| glib (glib-2.0/gthread-2.0/gio-2.0) | 2.84.0.1 | ✅（组件 .pc 链完整） | ✅ R35 全量 download rc=0（2026-10-15 真机） |
| libmad + libid3tag（可选） | — | ✅ | 本配方 --disable-mad 关闭（termrec curl 降级先例） |
| libusb-1.0（libmtp 传递依赖） | 1.0.27 | ✅（libmtp 依赖图内，R35 已随 libmtp 验证） | ✅ R35 全量 download rc=0（2026-10-15 真机） |

**W0 阻塞判定（R35/R36）——已解除**：W0 时 libmtp/1.1.21 是旧格式条目（无
conanfile.py），属最高风险阻塞；该依赖项任务已独立完成并合入制品仓（真机
conan create rc=0、消费者 3/3、W4 审计 P0=0 P1=0），mtpfs 的 R36 前置条件满足。
R35 二进制核验已于 2026-10-15 真机完成：libmtp/1.1.21、libfuse/2.9.9、
glib/2.84.0.1、libusb/1.0.27 四条全量 download（不带 --only-recipe）全部 rc=0。

## 构建设计（见 conanfile.py 文档字符串）
- tarball 自带 2012 configure（无 AC_CANONICAL_HOST、无 config.guess）→
  不传 --build/--host，靠 CC/CFLAGS/LDFLAGS 驱动。
- PKG_CHECK_MODULES 依赖发现：PkgConfigDeps 生成 glib 组件 .pc 与 libmtp.pc
  （libmtp 发布配方 pkg_config_name="libmtp"，其 Requires 链连带 libusb-1.0.pc）；
  libfuse 配方无 pkg_config_name 属性 → generators_folder 手写 fuse.pc
  （abiword-plugin-* 手写 .pc 先例；W0 时期曾一并手写 libmtp.pc，libmtp
  发布后删除以免覆盖依赖包真实 .pc）；链接闭包由 AutotoolsDeps 聚合提供。
- E011: configure 内联 sed umask 077→022（libfuse 2.9.9 先例）。
- E386: SHELL=/bin/sh + unset CONFIG_SHELL（termrec §12.38① 先例）。

## 真机第 1 轮验证结果（2026-10-15，MateBook）

预检：origin/feat/mtpfs-1.1=274621e71 与 Windows 交接 SHA 一致；分支基于
main=7d1f961b7，净 diff 8 文件全在本目录；L0j `conan list "mtpfs/*" -r=ohpcd`
无同版本（0 匹配）。

预期问题逐项结论：
1. libmtp 包缺失——已解除（见 W0）。
2. libfuse 2.9.9 静态库链接 mtpfs：**链接期新发现 E085**——libfuse.a 引用
   pthread_cancel/pthread_setcancelstate 而 OHOS SDK 链接期 libc.so 不导出
   （sysroot llvm-nm 实测无符号）；真机运行期 /system/lib64/libc.so 有导出
   （pthread_cancel=T、pthread_setcancelstate=W）→ conanfile 在 OHOS 下加
   `-Wl,--unresolved-symbols=ignore-all`（-z undefs 等价）留待运行期解析；
   探针程序真机实测 setcancelstate rc=0、pthread_join ok。不用 E085 空桩
   方案：空桩会让 fuse_stop_cleanup_thread 的 pthread_join 永等（卸载挂死），
   运行期有真实实现时"由系统提供"（libfuse 归档 notes 口径）语义更正确。
3. 2012 老代码 + clang 15：无隐式声明阻塞告警，1 条 -Wreturn-type 非 Werror；
   FUSE_USE_VERSION=22 与 libfuse 2.9.9 头文件兼容（编译/链接通过）。
4. glib 2.84 弃用告警：51 条 -Wdeprecated-declarations（GStaticMutex/
   g_static_mutex_get_mutex_impl → GMutex/g_mutex_lock 提示，含
   -W#pragma-messages），符合预期非阻塞；g_thread 系列保留可用。
5. snapshot.debian.org 源真机可达（conan create 源下载成功）。

**预期外新发现——conftest errno 127 伪装（libmtp D3 同款）**：首跑 conan
create 在 "checking whether we are cross compiling" 报 "cannot run C
compiled programs"（E064 报错形态）；config.log 实证为 `Error loading
shared library libgio-2.0.so.0 ... $?=127`——OHOS musl 忽略 DT_RUNPATH，
conftest 链着 AutotoolsDeps 注入的 glib/libusb 共享库运行期找不到。按
libmtp/1.1.21 同款在 generate() 注入依赖包 libdirs 到 LD_LIBRARY_PATH 后
conftest 本机跑通，无需 --host（E064 禁令保持）。知识图谱命中 E064/E085。

E011/E386 实证：解包源 configure:4765/4770 已为 `umask 022`（sed 生效）；
profile [buildenv] 注入 CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash，
配方 tc 环境 unset CONFIG_SHELL + SHELL=/bin/sh 在后层覆盖，configure/make
全程无 getcwd 类失败。

测试：conan create rc=0（内联 test_package 一并执行）；conan test 独立复验
rc=0——#1 `mtpfs --help` exit 0（输出 "Listing raw device(s) No raw devices
found"）；#2 timeout 30 包裹 `mtpfs /nonexistent-target` rc=0（{0,1,255}
接受集内）无挂死；终行 ALL TESTS PASSED。

**L1e 修复（R34 破坏性反向验证抓出 test.sh 真实缺陷）**：初版
`mtpfs --help && echo OK` 在 set -e 下左侧失败被豁免（经典 && 短路陷阱，
脚本不退出继续跑）；#2 仅拒绝 124——bin/ 被移走后 127（命令不存在）也被
当"无设备"接受，测试与包无实质依赖被 L1e 正确拦截（W3 第 1 次 finish 失败
原因）。加固：command -v 前置断言产物存在；两条用例均断言真实 mtpfs 设备
枚举输出 "Listing raw device(s)"（mtpfs.c main 自有文本，假包无此输出）；
rc 集合收紧 {0,1,255}，126/127/139 显式拒绝。L2 skip（mtpfs 无 --version
且 L2 直跑二进制无 conanrun 的 LD_LIBRARY_PATH，glib 共享库找不到）为
动态链接包的已知容忍项，不影响 W3 通过（libmtp 第 7 轮同形态）。

## 上游测试
- 上游**零测试**（无 tests/、无 make check、无 TESTS 声明）→ 依据
  TEST_QUALITY_SPEC 补充 test_package：--help 冒烟 + 无设备路径行为验证
  （不挂死断言）。挂载/数据面在无 /dev/fuse、无 MTP 硬件环境不可达，
  属 OHOS 能力边界，写明而非谎报。
---

**编译结束**: 2026-10-15 11:46
**最终状态**: built
