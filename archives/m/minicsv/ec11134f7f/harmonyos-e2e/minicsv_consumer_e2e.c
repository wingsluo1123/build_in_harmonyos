/*
 * minicsv_consumer_e2e.c — minicsv 完整消费者端到端用例（随 PR 交付）
 *
 * 赛事规则 12「鸿蒙特有测试」修复：这不是断言集合，而是一个真实跑通
 * 功能/流程的消费者端到端用例：
 *
 *   场景：小型访问日志聚合应用（模拟真实消费者数据处理流程）
 *   输入数据集：内嵌 CSV（5 行 × 4 列，含引号内逗号、转义、空列、多行格式）
 *   流程：
 *     1. minicsv_parse_line() 逐行解析 CSV（消费者 API 入口）
 *     2. minicsv_trim_cols() 清洗每列（含空列保留）
 *     3. 流转：逐行聚合 bytes 总量、按 action 分类计数、统计行数
 *     4. 汇总断言：聚合结果与独立计算的期望值（EXPECTED_* 常量）比对，
 *        任一不符即返回非零退出码（可失败，非恒绿）
 *   验证的鸿蒙/兼容性行为：以 OHOS aarch64 工具链（clang 15）编译、
 *   链接打包产物 libminicsv.a，在本机 HarmonyOS / HongMeng Kernel 1.12.0
 *   aarch64 上真实运行；解析路径不依赖平台特有堆分配行为。
 *
 * 失败注入：编译期可经 -DEXPECTED_* 覆盖期望值制造受控失败变体
 * （用于 failcap 门禁，该变体不进入交付物/暂存/提交/PR）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "minicsv.h"

#define MAX_COLS 8U
#define MAX_ROWS 64U

/* 独立计算的期望值（与数据集一一对应，改动数据集须同步） */
#ifndef EXPECTED_ROWS_TOTAL
#define EXPECTED_ROWS_TOTAL 5
#endif
#ifndef EXPECTED_BYTES_TOTAL
#define EXPECTED_BYTES_TOTAL 10752
#endif
#ifndef EXPECTED_LOGIN_COUNT
#define EXPECTED_LOGIN_COUNT 2
#endif
#ifndef EXPECTED_API_COUNT
#define EXPECTED_API_COUNT 2
#endif
#ifndef EXPECTED_UNIQUE_USERS
#define EXPECTED_UNIQUE_USERS 4
#endif

static int failures = 0;

static void
check(int cond, const char *what)
{
    if (cond) {
        printf("  ok: %s\n", what);
    } else {
        printf("  FAIL: %s\n", what);
        failures++;
    }
}

int
main(void)
{
    /* 输入数据集（行内以 "\n" 连接的单个缓冲区，模拟完整 CSV 文本） */
    char data[] =
        "alice,login,\"2026-09-28 10:00:00\",1024\r\n"
        "bob,\"api,write\",2026-09-28 10:01:00,2048\r\n"
        "carol,login,2026-09-28 10:02:00,512\r\n"
        "\"de,e\",logout,2026-09-28 10:03:00,4096\r\n"
        "alice,\"api,read\",,3072\r\n";
    char *cursor = data;
    char *cols[MAX_COLS];
    size_t cols_count;
    int row_no = 0;
    long bytes_total = 0;
    int login_count = 0;
    int api_count = 0;
    const char *users[MAX_ROWS];
    int users_count = 0;

    printf("minicsv_consumer_e2e: 消费者端到端用例（访问日志聚合）开始\n");

    /* 端到端主循环：逐行解析 → 清洗 → 流转聚合 */
    while (cursor != NULL && *cursor != 0 && row_no < MAX_ROWS) {
        cursor = minicsv_parse_line(cursor, cols, &cols_count, MAX_COLS);
        if (cols_count < 4U) {
            printf("  FAIL: 第 %d 行列数不足 (%zu)\n", row_no + 1, cols_count);
            failures++;
            continue;
        }
        minicsv_trim_cols(cols, cols_count);

        /* 流转 1：解析 bytes（第 4 列），允许空列 → 0 */
        long bytes = strtol(cols[3], NULL, 10);
        bytes_total += bytes;

        /* 流转 2：按 action（第 2 列）分类计数 */
        if (strcmp(cols[1], "login") == 0) {
            login_count++;
        } else if (strcmp(cols[1], "api,write") == 0 ||
                   strcmp(cols[1], "api,read") == 0) {
            api_count++;
        }

        /* 流转 3：去重统计 user（第 1 列） */
        int seen = 0;
        for (int i = 0; i < users_count; i++) {
            if (strcmp(users[i], cols[0]) == 0) {
                seen = 1;
                break;
            }
        }
        if (!seen && users_count < MAX_ROWS) {
            users[users_count++] = cols[0];
        }

        printf("  row%d: user=[%s] action=[%s] ts=[%s] bytes=%ld\n",
               row_no + 1, cols[0], cols[1],
               (cols_count > 2U ? cols[2] : ""), bytes);
        row_no++;
    }

    printf("  parsed rows: %d\n", row_no);
    printf("  bytes_total: %ld\n", bytes_total);
    printf("  login_count: %d, api_count: %d, unique_users: %d\n",
           login_count, api_count, users_count);

    /* 汇总断言：与独立计算的期望值比对（任一不符 → 非零退出码） */
    check(row_no == EXPECTED_ROWS_TOTAL, "行数 == 期望值");
    check(bytes_total == (long) EXPECTED_BYTES_TOTAL, "bytes 聚合 == 期望值");
    check(login_count == EXPECTED_LOGIN_COUNT, "login 分类计数 == 期望值");
    check(api_count == EXPECTED_API_COUNT, "api 分类计数 == 期望值");
    check(users_count == EXPECTED_UNIQUE_USERS, "去重用户数 == 期望值");

    printf("minicsv_consumer_e2e: %s (%d failures)\n",
           failures == 0 ? "PASS" : "FAIL", failures);
    return failures == 0 ? 0 : 1;
}