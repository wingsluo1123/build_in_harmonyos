/* test_package 消费者测试 — 真实调用 lockfree 库 API（R34：禁止空壳测试）
 *
 * 覆盖 C99 变体三个核心数据结构:
 *   magicq  — SPSC ring buffer（依赖 liblockfree.a 的 mirrorbuf 符号）
 *   rbq     — MPMC ring buffer（CAS/FAA，__sync 内建）
 *   lffifo  — 无锁队列（single linked list，Michael Scott）
 */
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
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
    printf("FAIL: %s (line %d)\n", #cond, __LINE__); return 1; } } while (0)

int main(void)
{
    uint64_t val;
    fprintf(stderr, "marker: start\n");

    /* ---- SPSC magicq ----
     * 上游要求 bsiz 为 64K 倍数（mirror_buffer 双映射技巧），order 16 → 512KB。
     * 与上游基准 INIT(f)=magicq_init((f),16) 对齐。 */
    magicq_t q;
    fprintf(stderr, "marker: before magicq_init\n");
    CHECK(magicq_init(&q, 16));
    fprintf(stderr, "marker: after magicq_init\n");
    val = 42;
    fprintf(stderr, "marker: before magicq_push\n");
    CHECK(magicq_push(&q, (uint64_t *)(&val)));
    fprintf(stderr, "marker: after magicq_push\n");
    CHECK(!magicq_empty(&q));
    CHECK(magicq_pop(&q, &val));
    fprintf(stderr, "marker: after magicq_pop\n");
    CHECK(val == 42);
    CHECK(magicq_empty(&q));
    magicq_free(&q);
    fprintf(stderr, "marker: after magicq_free\n");

    /* ---- MPMC rbq ---- */
    rbq_t r;
    fprintf(stderr, "marker: before rbq_init\n");
    CHECK(rbq_init(&r, 4));
    fprintf(stderr, "marker: after rbq_init\n");
    val = 7;
    CHECK(rbq_push(&r, (uint64_t *)(&val)));
    fprintf(stderr, "marker: after rbq_push\n");
    CHECK(!rbq_empty(&r));
    CHECK(rbq_pop(&r, &val));
    fprintf(stderr, "marker: after rbq_pop\n");
    CHECK(val == 7);
    CHECK(rbq_empty(&r));
    rbq_free(&r);
    fprintf(stderr, "marker: after rbq_free\n");

    /* ---- lock-free queue (lffifo) ---- */
    lffifo_t fifo;
    fprintf(stderr, "marker: before lffifo_init\n");
    CHECK(lffifo_init(&fifo, 4));
    fprintf(stderr, "marker: after lffifo_init\n");
    CHECK(lffifo_push(&fifo, (void *)0x1234));
    fprintf(stderr, "marker: after lffifo_push\n");
    CHECK(!lffifo_empty(&fifo));
    CHECK(lffifo_pop(&fifo) == (void *)0x1234);
    fprintf(stderr, "marker: after lffifo_pop\n");
    lffifo_free(&fifo);
    fprintf(stderr, "marker: after lffifo_free\n");

    printf("test lockfree b08f761900: OK (%d checks)\n", n_assert);
    return 0;
}
