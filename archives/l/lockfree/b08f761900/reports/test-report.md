# lockfree b08f761900 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 (OHOS 6.0)
- Clang 15.0.4
- Conan 2.29.1

## Verification

- `conan-verify lockfree b08f761900`: exit 0
- G1 (配方完整性): PASS
- G2 (conan create 干净构建): PASS
- G3 (系统同名库隔离 R26): PASS
- G4 (产物完整性): PASS
- L2 (平台功能矩阵 smoke): PASS
- L4 (静态安全扫描 checksec): PASS
- L5 (产物基线): PASS

## 上游测试申报（R51）

上游仓库不含 tests/ 目录、无 ctest/pytest 注册。可运行物为两个变体的基准程序
ffbench（性能测试，非断言型）。本机实测：C99 变体构建通过并运行输出正常；
C++11 变体本机构建通过（无 -latomic，-pthread 即可链接运行）。

## test_package

test_package 消费者测试 `test_lockfree` 真实调用库 API 并断言：

- magicq（SPSC ring buffer）：init/push/pop/empty/value 校验，4 项断言
- rbq（MPMC ring buffer）：init/push/pop/empty/value 校验，4 项断言
- lffifo（Michael Scott 无锁队列）：init/push/pop/empty 校验，4 项断言

- Test cases: 1（12 项断言）
- Passed: 1
- Failed: 0
- Skipped: 0

## 适配补丁

- 0001-C99-lffifo.h.patch: CAS2 从 x86 cmpxchg16b asm 改为可移植 __atomic
  __int128 实现（aarch64 无 cmpxchg16b；16 字节对齐要求与上游一致）
- 0002-C99-mirrorbuf.c.patch: 临时目录从硬编码 /tmp 改为遵循 TMPDIR
  （OHOS /tmp 为只读 erofs 挂载，E002）

## Result

The recipe was verified on an OpenHarmony aarch64 device and is eligible for
built status.
