/* 鸿蒙专项测试：OHOS(musl/aarch64) 下 sense 解码与错误类别映射语义一致性。
 *
 * 上游 ttesting/sg_sense_test.c 只覆盖固定格式；这里补两项对鸿蒙交叉编译特别相关的能力：
 *  1. 描述符格式（0x72/0x73）sense 解码——依赖 struct sg_scsi_sense_hdr 的位域布局
 *     与描述符链遍历，交叉编译/字节序差异会直接暴露；
 *  2. ASC/ASCQ → 错误类别映射（sg_err_category_sense / sg_get_category_sense_str），
 *     是下游 lsvpd 等消费者判定错误的实际路径。
 * 断言值取自 1.49 实测输出，两项都不依赖 SCSI 硬件。
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <scsi/sg_lib.h>

static int failures;

static void check(int cond, const char *what)
{
    printf("%s: %s\n", cond ? "PASS" : "FAIL", what);
    if (!cond)
        ++failures;
}

int main(void)
{
    char b[512];
    int cat;
    /* 描述符格式 sense(0x72)：当前错误、Sense key 0x3 (Medium Error)，
       ASC/ASCQ = 0x21/0x04 (Unaligned write command) */
    const uint8_t desc_sense[8] = {0x72, 0x03, 0x21, 0x04, 0, 0, 0, 0};
    /* 固定格式 sense(0x70)：Sense key 0x2 (Not Ready)，ASC/ASCQ = 0x04/0x02 */
    const uint8_t fixed_not_ready[18] = {0x70, 0x00, 0x02, 0x00, 0, 0, 0, 0,
                                         0,    0,    0,    0,    0x04, 0x02,
                                         0,    0,    0,    0};

    memset(b, 0, sizeof(b));
    sg_get_sense_str("(desc)", desc_sense, (int)sizeof(desc_sense), 0,
                     (int)sizeof(b), b);
    check(NULL != strstr(b, "Descriptor format, current") &&
              NULL != strstr(b, "Sense key: Medium Error") &&
              NULL != strstr(b, "Unaligned write command"),
          "描述符格式 sense(0x72) 解码出 Medium Error + Unaligned write command");

    memset(b, 0, sizeof(b));
    sg_get_sense_str("(notready)", fixed_not_ready, (int)sizeof(fixed_not_ready),
                     0, (int)sizeof(b), b);
    check(NULL != strstr(b, "Fixed format, current") &&
              NULL != strstr(b, "Sense key: Not Ready"),
          "固定格式 sense(0x70) 解码出 Not Ready");

    /* 错误类别映射：ASC/ASCQ 0x24/0x00 应归类为 Illegal request */
    {
        uint8_t sens[18];

        memset(sens, 0, sizeof(sens));
        sens[0] = 0x70;
        sens[2] = 0x05;
        sens[12] = 0x24;
        sens[13] = 0x00;
        cat = sg_err_category_sense(sens, (int)sizeof(sens));
        memset(b, 0, sizeof(b));
        check(5 == cat &&
                  NULL != strstr(sg_get_category_sense_str(cat, (int)sizeof(b),
                                                           b, 0),
                                 "Illegal request"),
              "sg_err_category_sense(24/00)==5 且映射为 \"Illegal request\"");
    }

    /* 空 sense 边界：不得越界/崩溃，返回可读串 */
    memset(b, 0, sizeof(b));
    sg_get_sense_str("(empty)", NULL, 0, 0, (int)sizeof(b), b);
    check(strlen(b) > 0, "sg_get_sense_str(NULL,0) 返回非空描述而非崩溃");

    if (failures) {
        printf("FAILED: %d 项断言失败\n", failures);
        return 1;
    }
    printf("ALL PASS: 4 项断言\n");
    return 0;
}
