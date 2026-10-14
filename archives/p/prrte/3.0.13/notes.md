# prrte 3.0.13 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-28
- 编译器: clang/clang++ (15.0.4, OHOS SDK 26.0.0.18)
- 状态: built

## 适配摘要

prrte（PMIx Reference RunTime Environment，Open MPI 的进程管理运行时）3.0.13
是主程序适配。上游 release 发行包
（https://github.com/openpmix/prrte/releases/download/v3.0.13/prrte-3.0.13.tar.gz，
sha256=81c27025182a26e90b0bb6aa67929a9313186fbd43964fc6d8734ce5cecd00ae）
含预生成 configure 与 config/oac 子模块，无需 autogen。

依赖：pmix/5.0.11（4.2.4≤v<6.0.0）、hwloc/2.14.0（≥1.11.0）、
libevent/2.1.12（≥2.0.21），全部已发布至 ohpcd 制品仓。

## 编译步骤

```bash
# conan 配方驱动（最终交付）
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# 结果：configure + make 成功，产物 prte/prte_info/prted/prun/pterm + libprrte.so.3.0.13
# test_package：HMBS_TEST_PACKAGE_RESULT: total=6 passed=6（全绿、无编译警告）
```

配方要点：
- PkgConfigDeps 为 pmix/hwloc/libevent 重新生成 prefix 正确的 .pc
  （conan 发布包内 .pc 是 relocatable 的 prefix=/，直接 pkg-config 会输出
  -I//include 导致头文件找不到）
- 修补生成的 pmix.pc 追加 `-I${includedir}/pmix`（PRTE_CHECK_PMIX 需
  src/util/pmix_argv.h，该头位于 include/pmix/ 子目录）
- 不向 configure 传 --with-pmix/--with-hwloc（会强制读包内 prefix=/
  错误 .pc），改经 PKG_CONFIG_PATH 解析；libevent 用 --with-libevent
  （其探测为直接路径头文件检查，安全）
- 环境 CPPFLAGS 前置 libevent include：OHOS 宿主的
  $HOME/usr/local/include 里存在 libev 兼容 event.h（同名遮蔽 libevent），
  不前置时 event_get_signal 宏被当作外部符号、链接报 undefined reference
- 构建/测试进程 LD_LIBRARY_PATH 前置 SDK llvm/lib（含 ABI 匹配的
  libxml2.so.16），避免 host lld 启动失败（与 abseil/abr2gbr 同类）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 无法识别 HarmonyOS | autotools 2021-01 脚本无 aarch64-unknown-linux-ohos 支持 | 复用 pmix 0001/0002 补丁（E007/E072） |
| 2 | config.status mktemp -d 失败 | HMDFS 下 umask 077 创建 0700 目录所有者不可写（E011） | configure umask 077→022（复用 pmix 0003 方案） |
| 3 | lld 启动失败 xmlFreeDoc symbol not found | 环境 LD_LIBRARY_PATH 遮蔽 SDK ABI 匹配 libxml2.so.16 | 配方 generate() 前置 SDK llvm/lib |
| 4 | undefined symbol: rindex | OHOS libc 无 BSD 遗留函数 rindex | plm_ssh_module.c rindex→strrchr |
| 5 | pmix.h 找不到 / -I//include | conan 包 .pc relocatable prefix=/ | PkgConfigDeps 重生成 + pmix.pc 补 include/pmix |
| 6 | event_get_signal 未定义 | usr/local libev 兼容 event.h 遮蔽 libevent 头 | CPPFLAGS 前置 libevent include |
| 7 | test_package host cmake 崩溃 | host cmake 需要 SDK libc++/libxml2，被环境遮蔽 | test_package 改纯 clang 编译 + SDK llvm/lib 前置 |

## 源码修改（补丁）与配方文件

- patches/0001-config-guess-ohos.patch — config.guess 识别 HarmonyOS
- patches/0002-config-sub-ohos.patch — config.sub 接受 ohos OS
- patches/0003-configure-umask.patch — configure/config.status umask 077→022
- patches/0004-plm-ssh-strrchr.patch — rindex→strrchr（plm_ssh_module.c）
- conanfile.py / conandata.yml / test_package/ / commands.json / manifest.yaml

## 依赖版本

- pmix/5.0.11（VERSION 限制 4.2.4 ≤ v < 6.0.0）
- hwloc/2.14.0（VERSION 限制 ≥1.11.0）
- libevent/2.1.12（VERSION 限制 ≥2.0.21）

## 验证结果

```bash
# conan create 全流程（build + package + test_package）
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# test_package 断言（6/6 全绿）：
#   - test_prrte 版本宏断言 4/4（PRTE_VERSION_MAJOR/MINOR/RELEASE/NUMERIC_VERSION）
#   - prte_info --all 输出 "PRTE: 3.0.13"
#   - 包布局：include/prte.h、include/prte_version.h、lib/libprrte.so、bin/prte_info
```

上游 prrte 3.0.13 无注册测试用例（104 个 Makefile.am 无 TESTS/check_PROGRAMS、
源码包无 test 目录、CI 无 make check 钩子），以 test_package 消费者测试补足
（6 断言 100% 通过，含版本宏端到端链接验证与 prte_info 真实运行）。

## 知识复盘

全部候选为 REUSED_EXISTING 或 VERSION_LOCAL：
- config.guess/config.sub OHOS → E007/E072
- umask 077→022 → E011
- rindex→strrchr → 草稿库已有大量同模式草稿（irqbalance/cconv/rdma-core/motif）
- .pc relocatable prefix=/ → E348/E355 已覆盖 PkgConfigDeps 机制
- SDK lld libxml2.so.16 → abseil/abr2gbr 归档方案族
- libevent 头遮蔽 / test_package 纯 clang → 本机环境/版本局部