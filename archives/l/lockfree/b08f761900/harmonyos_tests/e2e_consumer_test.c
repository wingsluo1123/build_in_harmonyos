/*
 * HarmonyOS 专项测试 — lockfree b08f761900 完整端到端消费者用例 (R03, rule12)
 *
 * 独立于既有 4015 断言入口的新增入口（自有源文件、自有构建目标、自有运行入口）。
 * 本用例通过消费已 conan create 的 lockfree 包产物（liblockfree.a + 头文件）构建，
 * 实际调用锁定库的 API 跑通完整核心流程：
 *
 *   A. lffifo（Michael Scott 无锁 FIFO，C99 变体）跨线程生产→消费流水线：
 *      生产者线程按序推入 N 条带内容特征的数据（seq + 特征载荷 + 校验和），
 *      消费者（主线程）按 FIFO 顺序取出并逐字段校验内容与完整性；
 *      每次 push/pop 均执行 CAS2（aarch64 16 字节双字 CAS，r01 补丁路径）。
 *   B. magicq（SPSC ring buffer，依赖 mirrorbuf 双映射缓冲）完整流转：
 *      init → push 多条带内容特征数据 → pop（FIFO 顺序）→ 内容校验 → free，
 *      覆盖镜像缓冲写路径遵循 $TMPDIR 的鸿蒙平台行为。
 *
 * 两步均覆盖合格标准的 init/produce/consume/verify/cleanup 全流程。
 * 平台约束：临时文件仅用 $TMPDIR/$HOME/tmp（不得假定 /tmp 可写）；
 * 不引入任何平台条件编译宏（R8），走 POSIX/标准 C99 单一路径。
 */
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <sched.h>
#include <pthread.h>

#include "magicq.h"
#include "lffifo.h"

#define copyu64(from, to) (((to)[0]) = ((from)[0]))

MAGICQ_PROTOTYPE(magicq, uint64_t, copyu64);

#define E2E_N_ITEMS     4096    /* lffifo 跨线程流水线条数（< lffifo order=13 容量 8191） */
#define E2E_PAYLOAD_LEN 16      /* 每条数据的内容特征字节数 */

/* 带内容特征的端到端数据项：seq（顺序）+ 特征载荷 + 校验和 */
typedef struct {
    uint32_t     seq;
    uint8_t      payload[E2E_PAYLOAD_LEN];
    uint32_t     checksum;
} e2e_item_t;

static e2e_item_t g_items[E2E_N_ITEMS];   /* 生产者侧由测试自备的内容数据 */

static int n_e2e_checks = 0;
#define E2E_CHECK(cond) do { n_e2e_checks++; if (!(cond)) { \
    printf("FAIL: %s (line %d)\n", #cond, __LINE__); \
    printf("RESULT: %d e2e checks passed before failure\n", n_e2e_checks - 1); \
    return 1; } } while (0)

static uint32_t item_checksum(const e2e_item_t *item)
{
    uint32_t sum = item->seq;
    for (int i = 0; i < E2E_PAYLOAD_LEN; ++i) {
        sum = sum * 31u + item->payload[i];
    }
    return sum;
}

static void fill_item(e2e_item_t *item, uint32_t seq)
{
    item->seq = seq;
    for (int i = 0; i < E2E_PAYLOAD_LEN; ++i) {
        item->payload[i] = (uint8_t)((seq * 7u + (uint32_t)i * 13u) & 0xffu);
    }
    item->checksum = item_checksum(item);
}

static lffifo_t g_fifo;

static void *producer_thread(void *arg)
{
    (void)arg;
    for (uint32_t i = 0; i < E2E_N_ITEMS; ++i) {
        while (!lffifo_push(&g_fifo, &g_items[i])) {
            sched_yield();   /* 满则自旋让步，等待消费者取出 */
        }
    }
    return NULL;
}

/* 端到端用例 A：lffifo 跨线程生产→消费流水线，验证 FIFO 顺序与内容完整性 */
static int e2e_lffifo_cross_thread_pipeline(void)
{
    pthread_t prod;

    E2E_CHECK(lffifo_init(&g_fifo, 13));

    /* 生产侧：测试自备内容数据（seq + 特征载荷 + 校验和） */
    for (uint32_t i = 0; i < E2E_N_ITEMS; ++i) {
        fill_item(&g_items[i], i);
    }
    printf("e2e[A] produce: %d items prepared, payload=%d bytes\n", E2E_N_ITEMS, E2E_PAYLOAD_LEN);

    if (pthread_create(&prod, NULL, producer_thread, NULL) != 0) {
        printf("FAIL: pthread_create (line %d)\n", __LINE__);
        return 1;
    }

    /* 消费侧：主线程按 FIFO 顺序取出并逐字段校验内容与完整性 */
    for (uint32_t i = 0; i < E2E_N_ITEMS; ++i) {
        e2e_item_t *got;
        while ((got = (e2e_item_t *)lffifo_pop(&g_fifo)) == NULL) {
            sched_yield();   /* 空则自旋让步，等待生产者推入 */
        }
        E2E_CHECK(got->seq == i);                                  /* FIFO 顺序 */
        E2E_CHECK(memcmp(got->payload, g_items[i].payload,
                         E2E_PAYLOAD_LEN) == 0);                   /* 内容逐字节一致 */
        E2E_CHECK(got->checksum == item_checksum(got));            /* 完整性校验和 */
    }

    pthread_join(prod, NULL);
    printf("e2e[A] consume: %d items dequeued, FIFO order + content verified\n", E2E_N_ITEMS);

    E2E_CHECK(lffifo_empty(&g_fifo));
    lffifo_free(&g_fifo);   /* cleanup */
    printf("e2e[A] cleanup: lffifo freed\n");
    return 0;
}

/* 端到端用例 B：magicq（SPSC，mirrorbuf 双映射）完整 init→produce→consume→verify→cleanup */
static int e2e_magicq_full_flow(void)
{
    magicq_t q;
    uint64_t val;

    E2E_CHECK(magicq_init(&q, 16));            /* bsiz=512KB，满足 64K 倍数；初始化 */

    /* 生产侧：推入多条带内容特征的数据（值 = 序号，内容自备） */
    const uint32_t n = 256;
    for (uint32_t i = 0; i < n; ++i) {
        uint64_t v = (uint64_t)i * 1000u + (uint64_t)i;   /* 内容特征：i*1000+i */
        E2E_CHECK(magicq_push(&q, (uint64_t *)(&v)));
        printf("e2e[B] produce: pushed #%u => %llu\n",
               i, (unsigned long long)v);
    }
    printf("e2e[B] produce: %u items pushed into magicq\n", n);

    /* 消费侧：FIFO 顺序逐条取出并校验内容 */
    for (uint32_t i = 0; i < n; ++i) {
        E2E_CHECK(!magicq_empty(&q));
        E2E_CHECK(magicq_pop(&q, &val));
        printf("e2e[B] consume: pop #%u => %llu\n",
               i, (unsigned long long)val);
        E2E_CHECK(val == (uint64_t)i * 1000u + (uint64_t)i);   /* 内容与推入一致 */
    }
    E2E_CHECK(magicq_empty(&q));

    magicq_free(&q);   /* cleanup */
    printf("e2e[B] cleanup: magicq freed\n");
    return 0;
}

int main(void)
{
    const char *tmpdir = getenv("TMPDIR");
    printf("lockfree e2e consumer test: TMPDIR=%s\n", tmpdir ? tmpdir : "(unset)");
    printf("lockfree e2e consumer test: start\n");

    if (e2e_lffifo_cross_thread_pipeline() != 0) {
        return 1;
    }
    printf("lockfree e2e consumer test: lffifo cross-thread pipeline OK\n");

    if (e2e_magicq_full_flow() != 0) {
        return 1;
    }
    printf("lockfree e2e consumer test: magicq full flow OK\n");

    printf("lockfree e2e consumer test: PASS (%d e2e checks)\n", n_e2e_checks);
    return 0;
}