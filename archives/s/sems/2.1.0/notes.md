# sems 2.1.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 2.1.0 已全量移除 Makefile、迁移 CMake）
- 编译日期: 2026-10-15
- 编译器: clang/clang++ 15（OHOS SDK, aarch64-linux-ohos）
- 状态: built

## 上游信息
- 仓库: https://github.com/sems-server/sems
- tag: 2.1.0
- tarball: https://github.com/sems-server/sems/archive/refs/tags/2.1.0.tar.gz
  （HTTP 200，sha256 f16c28917f1b92e9ec963ca28abd4612282f610276a67fa4e6346d07cffb8756，本机独立校验一致）
- 唯一硬依赖: libevent/2.1.12（`find_package(Libevent2 REQUIRED)`，ohpcd 已发布，`conan download --only-recipe` 实测通过）
- 其余依赖（gsm/speex/openssl/hiredis/mysql++/zrtp/rtmp/libev 等）上游均为非 REQUIRED 探测，环境未提供即自动跳过

## 编译步骤

1. W0 依赖检查：`conan download libevent/2.1.12 -r=ohpcd --only-recipe` 成功（制品仓已有 binary）
2. USTC / 官方源取源码，sha256 校验一致
3. `conan create`（WSL 原生盘 `/root/sems-wt`，`-pr:h ohos-aarch64-wsl-xbuild -pr:b default`）
4. test_package：真实运行上游 sems_tests（11 suite / 204 断言）与 `sbin/sems -v` 冒烟

## 关闭项（保持 OHOS 包自包含）

| 开关 | 值 | 原因 |
|---|---|---|
| SEMS_USE_PYTHON | OFF | OHOS sysroot 无 Python 解释器（conf_auth/ivr/mailbox/pin_collect 随之排除） |
| SEMS_USE_ILBC | OFF | 关闭编解码器（不链接外置/内置 iLBC） |
| SEMS_USE_MONITORING | OFF | 不定义 -DUSE_MONITORING |
| EXCLUDE_APP_MODULES | `monitoring xmlrpc2di` | monitoring 的 Cargo/Rust 工具会产出 host 架构二进制（或 Python 包装脚本），对 aarch64 OHOS 包无意义；xmlrpc2di 捆绑的 xmlrpc++ 无条件 `#include <openssl/crypto.h>`（OHOS sysroot 无 openssl，上游 Linux 构建同样需要 libssl-dev），且该可选诊断模块 core 无代码引用 |

## 问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `use of undeclared identifier 'pthread_cancel'`（core/AmThread.cpp） | OHOS musl 无 pthread_cancel，符号也不在头文件里 | patches/0001：上游顶层 CMakeLists 增加 `check_symbol_exists(pthread_cancel "pthread.h" HAVE_PTHREAD_CANCEL)` 编译期能力探测；有符号走原 pthread_cancel，无符号退化为 `on_stop()` 协作式停止且不置 stopped。补丁不含任何平台条件宏（R8），能力探测对所有 libc 通用 |
| 2 | `fatal error: 'openssl/crypto.h' file not found`（apps/xmlrpc2di） | 捆绑 xmlrpc++ 的 XmlRpcSource.h 无条件 include openssl 头 | EXCLUDE_APP_MODULES 排除 xmlrpc2di（可选诊断模块） |
| 3 | core 以裸名 `event`/`event_pthreads` 链接、不引用 CMake 目标 | 上游 FindLibevent2.cmake 用变量探测 | patches/0002：core/CMakeLists.txt 注入 `${LIBEVENT2_INCLUDE_DIR}`/`${LIBEVENT2_LIB_DIR}` 并把裸名替换为 `${LIBEVENT2_LIBRARIES}`；generate() 把 LIBEVENT2_* 预设为 conan libevent 的绝对路径与静态归档（自包含） |
| 4 | 上游 install 目标使用绝对前缀 `/usr/local/...` | `${SEMS_*_PREFIX}` 默认绝对路径 | generate() 把 SEMS_EXEC_PREFIX/SEMS_CFG_PREFIX 设为 `.`、SEMS_AUDIO_PREFIX 设为 `lib`、SEMS_DOC_PREFIX 设为 `share/doc`，`cmake --install` 全部落在包目录内 |

## 上游测试用例申报表（R51 三步法）

- 清点：core/tests/ 11 个 fct.h suite，编译为单体 sems_tests（ctest 注册 1 项），
  断言级子测试合计 204（rfc3261_musts=88, rfc3261_parser=25, uriparser=15,
  amconfig=14, jsonarg=13, parser=13, auth=11, headers=10, extensions=8,
  replaces=5, sdp=2）
- 真实执行：配方构建 sems_tests 并随包分发（sbin/sems_tests）；
  test_package test() 第一步运行它（CI 原生 OHOS worker 直接执行）；
  本地交叉产物在 WSL 内用 qemu-aarch64 + OHOS guest rootfs 真实运行，实测
  `PASSED (204/204 tests in 0.197590s)`、退出码 0。命令：

  ```sh
  qemu-aarch64 -L /opt/ohos-guest \
    -E LD_PRELOAD=/opt/ohos-guest/lib/libbacktraceshim.so:/opt/ohos-guest/lib/libarc4shim.so:/opt/ohos-guest/lib/libfdchkshim.so:/opt/ohos-guest/lib/libchkfcnshim.so:/opt/ohos-guest/lib/libbtfdshim.so:/opt/ohos-guest/lib/libpcmchkshim.so:/opt/ohos-guest/lib/libmallinfo2shim.so \
    ./sems_tests
  ```
  （guest rootfs 的 stock musl 缺 backtrace/backtrace_symbols/arc4random/__fd_chk 等符号，
  须用 guest 自带 shim 预载；原生 OHOS 设备/CI 无此问题。注意 LD_PRELOAD 必须经 qemu 的
  `-E` 传给 guest，直接 export 会被宿主 x86_64 glibc ld.so 抢先尝试加载 aarch64 shim 而失败。）
- 补全测试：test_package/test_sems.sh 真实运行打包的 sbin/sems -v 并断言版本横幅；
  本地同样实测 `Sip Express Media Server (2.1.0 (aarch64/HarmonyOS))`、退出码 0。

## 源码修改

- CMakeLists.txt、core/AmThread.cpp（patches/0001：pthread_cancel 能力探测）
- core/CMakeLists.txt（patches/0002：注入 libevent 目录与静态归档）

---
**编译结束**: 2026-10-15
**最终状态**: built
