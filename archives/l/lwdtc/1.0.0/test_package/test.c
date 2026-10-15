/*
 * test_package for lwdtc 1.0.0 — 消费者视角真实 API 测试 (R34)
 *
 * 调用被测库真实 API：
 *   - lwdtc_cron_parse：解析 7 字段 cron 表达式
 *   - lwdtc_cron_is_valid_for_time：按已知时刻校验匹配/不匹配
 *   - lwdtc_cron_next：从当前时间计算下一次触发
 */
#include <stdio.h>
#include <string.h>
#include <time.h>
#include "lwdtc/lwdtc.h"

int main(void) {
    lwdtc_cron_ctx_t ctx;
    time_t now, next;
    struct tm tmv;
    int fails = 0;

    /* 7-field cron: sec min hour mday mon wday year — every minute at second 30 */
    if (lwdtc_cron_parse(&ctx, "30 * * * * * *") != lwdtcOK) {
        printf("FAIL: lwdtc_cron_parse\n");
        return 1;
    }

    /* 已知时刻校验：2026-09-21 12:34:30 (Monday) 秒=30 应匹配 */
    memset(&tmv, 0, sizeof(tmv));
    tmv.tm_year = 2026 - 1900; tmv.tm_mon = 8; tmv.tm_mday = 21;
    tmv.tm_hour = 12; tmv.tm_min = 34; tmv.tm_sec = 30; tmv.tm_isdst = -1;
    if (lwdtc_cron_is_valid_for_time(&tmv, &ctx) != lwdtcOK) {
        printf("FAIL: valid(30s)\n");
        fails++;
    }
    tmv.tm_sec = 31;
    if (lwdtc_cron_is_valid_for_time(&tmv, &ctx) == lwdtcOK) {
        printf("FAIL: valid(31s) should not match\n");
        fails++;
    }

    /* 下一次触发必须严格晚于当前时间 */
    now = time(NULL);
    if (lwdtc_cron_next(&ctx, now, &next) != lwdtcOK) {
        printf("FAIL: lwdtc_cron_next\n");
        fails++;
    } else if (next <= now) {
        printf("FAIL: next <= now\n");
        fails++;
    }

    if (fails == 0) {
        printf("lwdtc test_package: PASS (parse + valid + next)\n");
        return 0;
    }
    printf("lwdtc test_package: FAIL (%d failures)\n", fails);
    return 1;
}
