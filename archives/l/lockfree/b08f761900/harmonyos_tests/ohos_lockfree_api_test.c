/*
 * HarmonyOS 专项测试 — lockfree b08f761900 (aarch64-linux-ohos)
 *
 * 独立于 test_package 的鸿蒙特有测试入口（自有源文件、自有构建目标、自有运行入口）。
 *
 * 验证的鸿蒙/OHOS 平台行为：
 *   1. C99 LF_CAS2 16 字节双字 CAS（r01 补丁：x86 cmpxchg16b 内联汇编 →
 *      __atomic_compare_exchange_n 作用于 __int128，且 struct lf_pointer 强制
 *      16 字节对齐）在 aarch64 上正确完成交换且不触发 SIGBUS —— 通过 lffifo
 *      无锁队列连续 push/pop 压测实证（每次 push/pop 都执行 CAS2）。
 *   2. magicq（SPSC ring buffer）经 mirrorbuf.c（r01 补丁：临时文件遵循
 *      $TMPDIR 而非只读 /tmp）在 OHOS 上可用 —— 在设置 TMPDIR 的环境下
 *      magicq_init 成功即证明 mirrorbuf 写路径可写。
 *
 * 全部断言可失败：CHECK 失败打印原文并返回非零退出码。
 * 不引入任何平台条件编译宏（无 __OHOS__ 等），走 POSIX/标准 C99 单一路径。
 */
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <sched.h>

#include "magicq.h"
#include "rbq.h"
#include "lffifo.h"

#define copyu64(from, to) (((to)[0]) = ((from)[0]))
#define sched_yield_(a) sched_yield()

MAGICQ_PROTOTYPE(magicq, uint64_t, copyu64);
RBQ_PROTOTYPE(rbq, uint64_t, copyu64, sched_yield_);

static int n_assert = 0;
#define CHECK(cond) do { n_assert++; if (!(cond)) { \
    printf("FAIL: %s (line %d)\n", #cond, __LINE__); \
    printf("RESULT: %d assertions passed before failure\n", n_assert - 1); \
    return 1; } } while (0)

static int test_cas2_lffifo_roundtrip(void)
{
    /* lffifo 无锁队列：每次 push/pop 均执行 CAS2（16 字节双字 CAS）。
     * 若 aarch64 上 16 字节 CAS 未对齐或实现错误，将触发 SIGBUS 或断言失败。 */
    lffifo_t fifo;
    const int n = 2000;
    CHECK(lffifo_init(&fifo, 12));

    for (int i = 1; i <= n; ++i) {
        CHECK(lffifo_push(&fifo, (void *)(intptr_t)i));
    }
    CHECK(lffifo_size(&fifo) == (size_t)n);

    for (int i = 1; i <= n; ++i) {
        void *v = lffifo_pop(&fifo);
        CHECK(v == (void *)(intptr_t)i);
    }
    CHECK(lffifo_empty(&fifo));

    lffifo_free(&fifo);
    return 0;
}

static int test_magicq_tmpdir_roundtrip(void)
{
    /* magicq（SPSC）依赖 mirrorbuf_create；r01 补丁后临时文件写 $TMPDIR
     * （OHOS /tmp 为只读 erofs）。magicq_init 成功即证明写路径可用。 */
    magicq_t q;
    uint64_t val;
    CHECK(magicq_init(&q, 16));          /* bsiz=512KB，满足 64K 倍数要求 */

    val = 42;
    CHECK(magicq_push(&q, (uint64_t *)(&val)));
    CHECK(!magicq_empty(&q));
    CHECK(magicq_pop(&q, &val));
    CHECK(val == 42);
    CHECK(magicq_empty(&q));

    magicq_free(&q);
    return 0;
}

static int test_rbq_roundtrip(void)
{
    /* MPMC ring buffer：CAS/FAA 内建（__sync）路径。 */
    rbq_t r;
    uint64_t val;
    CHECK(rbq_init(&r, 8));

    val = 7;
    CHECK(rbq_push(&r, (uint64_t *)(&val)));
    CHECK(!rbq_empty(&r));
    CHECK(rbq_pop(&r, &val));
    CHECK(val == 7);
    CHECK(rbq_empty(&r));

    rbq_free(&r);
    return 0;
}

int main(void)
{
    const char *tmpdir = getenv("TMPDIR");
    printf("lockfree harmonyos test: TMPDIR=%s\n", tmpdir ? tmpdir : "(unset)");
    printf("lockfree harmonyos test: start\n");

    if (test_cas2_lffifo_roundtrip() != 0) {
        return 1;
    }
    printf("lockfree harmonyos test: lffifo CAS2 roundtrip OK\n");

    if (test_magicq_tmpdir_roundtrip() != 0) {
        return 1;
    }
    printf("lockfree harmonyos test: magicq TMPDIR roundtrip OK\n");

    if (test_rbq_roundtrip() != 0) {
        return 1;
    }
    printf("lockfree harmonyos test: rbq roundtrip OK\n");

    printf("lockfree harmonyos test: PASS (%d assertions)\n", n_assert);
    return 0;
}
