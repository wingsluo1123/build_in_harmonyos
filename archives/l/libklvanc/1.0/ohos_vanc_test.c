/*
 * ohos_vanc_test.c — HarmonyOS 专项测试 (libklvanc 1.0)
 *
 * 调用当前库 libklvanc 的公开 API 并验证 OHOS 平台行为：
 *   1. 验证运行平台为 HarmonyOS (uname syscall)
 *   2. klvanc_context_create / klvanc_context_destroy 生命周期
 *   3. klvanc_checksum_calculate 校验和算法在 OHOS 上正确
 *   4. klvanc_packet_parse 解析构造的 VANC 数据行
 */
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/utsname.h>

#include <libklvanc/vanc.h>
#include <libklvanc/vanc-checksum.h>

static int fails = 0;

#define CHECK(cond, msg) do { \
    if (cond) { printf("  [PASS] %s\n", msg); } \
    else { printf("  [FAIL] %s\n", msg); fails++; } \
} while (0)

int main(void)
{
    struct utsname uts;

    printf("=== libklvanc 1.0 HarmonyOS 专项测试 ===\n");

    /* 1. OHOS 平台验证 */
    if (uname(&uts) == 0) {
        printf("  uname: sysname=%s machine=%s release=%s\n",
               uts.sysname, uts.machine, uts.release);
        CHECK(strcmp(uts.sysname, "HarmonyOS") == 0,
              "运行平台为 HarmonyOS (uname sysname)");
        CHECK(strcmp(uts.machine, "aarch64") == 0 ||
              strcmp(uts.machine, "arm64") == 0,
              "运行架构为 aarch64/arm64");
    } else {
        printf("  [FAIL] uname() 失败\n");
        fails++;
    }

    /* 2. 上下文生命周期 */
    {
        struct klvanc_context_s *ctx = NULL;
        int rc = klvanc_context_create(&ctx);
        CHECK(rc == 0 && ctx != NULL,
              "klvanc_context_create 成功返回非空上下文");
        if (ctx) {
            rc = klvanc_context_destroy(ctx);
            CHECK(rc == 0, "klvanc_context_destroy 成功");
        }
    }

    /* 3. VANC 校验和算法（SMPTE 291 标准位运算） */
    {
        /* 构造 VANC 用户数据字：ADF(000 3ff 3ff) 之后的 payload 字 */
        uint16_t words[6] = { 0x0100, 0x0200, 0x0400, 0x0800, 0x1000, 0x2000 };
        uint16_t sum1 = klvanc_checksum_calculate(words, 6);
        /* 手动验证: 逐字累加并 & 0x01ff */
        uint16_t expect = 0;
        for (int i = 0; i < 6; i++) {
            expect += words[i];
            expect &= 0x01ff;
        }
        expect |= ((~expect & 0x0100) << 1);
        printf("  checksum: klvanc=%04x expect=%04x\n", sum1, expect);
        CHECK(sum1 == expect, "klvanc_checksum_calculate 与 SMPTE 291 期望一致");
    }

    /* 4. VANC 包解析 */
    {
        struct klvanc_context_s *ctx = NULL;
        unsigned short words[] = {
            0x000, 0x3ff, 0x3ff,              /* ADF */
            0x101, 0x02, 0x0f,               /* DID=0x101 SDID=0x02 DC=0x0f (AFD) */
            0x000, 0x000, 0x000, 0x000, 0x000, 0x000, 0x000, 0x000, 0x000,
            0x000, 0x000, 0x000, 0x000, 0x000, 0x000, 0x000
        };
        int rc;

        if (klvanc_context_create(&ctx) == 0 && ctx) {
            rc = klvanc_packet_parse(ctx, 9, words,
                                     sizeof(words) / sizeof(words[0]));
            printf("  packet_parse: rc=%d (成功解析帧数)\n", rc);
            /* klvanc_packet_parse 返回成功解析的 VANC 帧数（>=1 即解析成功） */
            CHECK(rc > 0, "klvanc_packet_parse 成功解析构造 VANC 行");
            klvanc_context_destroy(ctx);
        } else {
            printf("  [FAIL] 解析前置 context 创建失败\n");
            fails++;
        }
    }

    printf("============================\n");
    if (fails == 0) {
        printf("HarmonyOS 专项测试: ALL PASSED\n");
        return 0;
    }
    printf("HarmonyOS 专项测试: %d FAILED\n", fails);
    return 1;
}
