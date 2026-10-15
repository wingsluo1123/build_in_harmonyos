# libtwirc 0.1.2 适配笔记

## 编译环境
- 构建系统: custom（上游无 configure/Makefile，手写 build-shared/build-static 脚本直接调用编译器）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang）
- 目标平台: HarmonyOS PC aarch64（os=OHOS, arch=armv8, profile: ci/conan/profiles/ohos-aarch64）
- 状态: built

## 编译步骤

源码结构：`src/libtwirc.c` 顶部 `#include` 了 `libtwirc_cmds.c`、`libtwirc_util.c`、`libtwirc_evts.c`，
因此上游只编译单一翻译单元 `libtwirc.c` 即可得到完整库。探索阶段验证：

```bash
# 静态 + 共享分别验证
clang -c -fPIC -o obj/libtwirc.o src/libtwirc.c
clang -shared obj/libtwirc.o -o lib/libtwirc.so
# 消费者链接验证（无网络 API 冒烟）
clang -I src smoke.c lib/libtwirc.so -o smoke && LD_LIBRARY_PATH=lib ./smoke
# 输出: libtwirc smoke OK last_error=0
```

conanfile.py 内 build() 使用 Conan Toolchain conf（tools.build:compiler_executables）取编译器，
不依赖 shell 环境变量（R33）；shared 时仅链接 libc。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成 autotools 模板 | 误判构建系统 | 手写 custom 配方：直接调用 clang 编译单一 TU |

## 源码修改

无补丁（patches/ 为空）。上游源码零修改，仅新增 Conan 配方与消费者测试。

## 依赖版本

无第三方编译依赖；运行时仅依赖系统 libc。

## 验证结果

```bash
# 上游测试（R51 清点）：上游无 tests/ 目录、无 ctest/make check 注册项（README 自述 "not unit-tested yet"）
# 消费者冒烟：twirc_init/twirc_get_last_error/twirc_is_connected/twirc_kill 断言 3 项
```

## 注意事項

- 上游明确为 Linux-only 的 Twitch IRC 客户端库，使用 epoll（sys/epoll.h），在 OHOS 上由 libc 提供。
- 无网络依赖的 API 可完整离线验证；connect/loop 类 API 需要真实 Twitch IRC 服务，不作为本地门禁阻塞项。
---

**编译结束**: 2026-09-27 19:15
**最终状态**: built
