/*
 * ohos_test.c — nibbleandahalf 0.0-git-c3d5edba42 HarmonyOS PC 专项用例
 *
 * 独立于上游自带测试（testbase64.c，随机数据字符串往返）与 test_package
 * 消费者用例（单字符串往返）。本用例在 OHOS aarch64 目标上通过已安装包的
 * 公开头文件 base64.h + libnaah64 链接运行，覆盖：
 *   - 二进制安全：含 \0 的原始二进制块往返（上游 main 只用 strlen 字符串）
 *   - 大块往返：16MB 非零二进制随机块
 *   - 完整性检测：base64integrity 正确拒绝坏 ASCII（"-!#$asdf*()_"）
 *   - 坏长度：非 4 倍数输入 unbase64 不崩溃、返回 NULL
 *
 * 编译：clang -I<prefix>/include ohos_test.c -L<prefix>/lib -lnaah64
 * 退出码：0=全部通过；1=任一断言失败。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "base64.h"

static int failures = 0;

static void check(int cond, const char* name) {
    if (cond) {
        printf("PASS: %s\n", name);
    } else {
        printf("FAIL: %s\n", name);
        failures++;
    }
}

static int roundtrip(const unsigned char* data, int len) {
    int encLen = 0, decLen = 0;
    char* enc = base64(data, len, &encLen);
    if (!enc || encLen <= 0) return 0;
    if (!base64integrity(enc, encLen)) { free(enc); return 0; }
    unsigned char* dec = unbase64(enc, encLen, &decLen);
    if (!dec || decLen != len) { free(enc); return 0; }
    int ok = memcmp(dec, data, (size_t)len) == 0;
    free(enc);
    free(dec);
    return ok;
}

int main(void) {
    printf("--- nibbleandahalf HarmonyOS PC 专项测试 ---\n");

    /* T1: 二进制安全 — 含 NUL 字节的原始块 */
    {
        unsigned char bin[] = {0x00, 0x01, 0x02, 0x7f, 0x80, 0xff, 0x00, 0x41,
                               0x00, 0xfe, 0x5a, 0x00, 0x00, 0x00, 0xc3, 0x10};
        check(roundtrip(bin, (int)sizeof(bin)), "T1 含NUL二进制块往返");
    }

    /* T2: 大块随机二进制 16MB 往返 */
    {
        const int len = 16 * 1024 * 1024;
        unsigned char* big = (unsigned char*)malloc((size_t)len);
        if (!big) { check(0, "T2 分配16MB"); }
        else {
            for (int i = 0; i < len; i++) big[i] = (unsigned char)(i * 31 + 7);
            check(roundtrip(big, len), "T2 16MB二进制往返");
            free(big);
        }
    }

    /* T3: base64integrity 拒绝坏 ASCII */
    {
        const char* bad = "-!#$asdf*()_";
        check(!base64integrity(bad, (int)strlen(bad)), "T3 坏ASCII被拒绝");
    }

    /* T4: 非4倍数坏长度 unbase64 安全拒绝（SAFEBASE64 路径返回 NULL，不崩溃） */
    {
        const char* badLen = "==";
        int outLen = -1;
        unsigned char* out = unbase64(badLen, (int)strlen(badLen), &outLen);
        check(out == NULL, "T4 坏长度输入安全拒绝（无崩溃）");
        free(out);
    }

    /* T5: 1 字节确定性往返（0x41 -> "QQ==" -> 0x41） */
    {
        unsigned char data[] = {0x41};
        int encLen = -1, decLen = -1;
        char* enc = base64(data, 1, &encLen);
        int ok = 0;
        if (enc && encLen == 4 && strcmp(enc, "QQ==") == 0 &&
            base64integrity(enc, encLen)) {
            unsigned char* dec = unbase64(enc, encLen, &decLen);
            ok = dec && decLen == 1 && dec[0] == 0x41;
            free(dec);
        }
        free(enc);
        check(ok, "T5 1字节确定性往返");
    }

    printf("--- nibbleandahalf OHOS 专项: %s ---\n",
           failures == 0 ? "ALL PASS" : "FAILED");
    return failures == 0 ? 0 : 1;
}
