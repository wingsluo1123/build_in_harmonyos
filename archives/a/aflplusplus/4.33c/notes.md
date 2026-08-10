# AFLplusplus 4.33c 鸿蒙 PC 适配笔记

## 构建策略

- **Makefile-based**: 使用 GNUmakefile 直接构建，无 autotools/cmake
- **仅构建核心工具**: afl-fuzz, afl-showmap, afl-tmin, afl-gotcpu, afl-analyze
- **跳过 LLVM/GCC 插件**: OHOS CI 无 LLVM/GCC-plugin-dev，跳过 afl-cc 和 instrumentation
- **NO_PYTHON=1**: CI 无 python3-config，禁用 Python 绑定
- **SYS=Linux**: 覆盖 uname 检测，确保 OHOS 获得 Linux 链接标志 (-ldl -lrt -lm)
- **TEST_MMAP=1**: 强制使用 mmap 共享内存（非 SysV shmget），更可移植

## 关键决策

| 决策 | 原因 |
|------|------|
| 自定义 package() 而非 make install | make install 尝试安装 afl-cc（需 LLVM 构建），文件不存在会失败 |
| 跳过 make tests | test-all.sh 需要 LLVM/GCC/QEMU/Frida/UniCorn——CI 均无 |
| 不补丁 GNUmakefile | 所有平台差异通过 make 命令行变量覆盖（SYS/PREFIX/NO_PYTHON） |
| 补丁 forkserver.h + sharedmem.h | OHOS libc 不隐式传递 POSIX 类型（uid_t/pid_t/mode_t），需显式 `#include <sys/types.h>` |

## 上游测试状态

上游完整测试套件（test/test-all.sh）依赖：
- LLVM + Clang（afl-cc + instrumentation）
- GCC plugin（gcc_mode）
- QEMU（qemu_mode）
- Frida（frida_mode）

OHOS CI 上以上均不可用。如需积分赛事的上游测试通过率数据，需在鸿蒙 PC 上手动运行：
```bash
cd $BUILD_SRC_DIR
make -f GNUmakefile tests NO_PYTHON=1 PREFIX=/ 2>&1 | tee test-results.log
```
预期：test-unittests.sh + test-basic.sh 通过；其他 skip/fail（缺依赖）。

## 平台适配说明

- OHOS 与 Linux ABI 兼容，设置 SYS=Linux 即可获得正确的编译/链接标志
- HMDFS /tmp 只读 (E002): afl-fuzz 默认输出到 /tmp，用户需设置 AFL_TMPDIR=$HOME/tmp
