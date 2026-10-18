/* 消费者用例：仅经公开头文件 <scsi/sg_lib.h> 使用 libsgutils2 的公开 API（R34）。
 *
 * 覆盖：库 API 版本串、ASC/ASCQ 码表、固定格式 sense 解码、hex2str 输出格式。
 * 断言值取自 1.49 实测输出，全部不依赖 SCSI 硬件。
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
    const char *ver = sg_lib_version();
    /* 固定格式 sense：0x70 当前错误，Sense key 0x5 (Illegal Request)，
       ASC/ASCQ = 0x24/0x00 (Invalid field in cdb) */
    const uint8_t fixed_sense[18] = {0x70, 0x00, 0x05, 0x00, 0, 0, 0, 0,
                                     0,    0,    0,    0,    0x24, 0x00,
                                     0,    0,    0,    0};
    const uint8_t raw[4] = {0xde, 0xad, 0xbe, 0xef};

    /* 注意：sg_lib_version() 返回的是 sg_lib API 版本（形如 "3.19 20260717"），
       不是软件包版本 1.49；包版本由 conanfile 的 test() 用 CLI --version 校验 */
    check(NULL != ver && 0 == strncmp(ver, "3.19 ", 5) && strlen(ver) >= 13,
          "sg_lib_version() 形如 \"3.19 YYYYMMDD\"");

    memset(b, 0, sizeof(b));
    sg_get_asc_ascq_str(0x24, 0x00, (int)sizeof(b), b);
    check(NULL != strstr(b, "Invalid field in cdb"),
          "sg_get_asc_ascq_str(0x24,0x00) -> Invalid field in cdb");

    memset(b, 0, sizeof(b));
    sg_get_asc_ascq_str(0x29, 0x00, (int)sizeof(b), b);
    check(NULL != strstr(b, "Power on, reset"),
          "sg_get_asc_ascq_str(0x29,0x00) -> Power on, reset");

    memset(b, 0, sizeof(b));
    sg_get_sense_str("(fixed)", fixed_sense, (int)sizeof(fixed_sense), 0,
                     (int)sizeof(b), b);
    check(NULL != strstr(b, "Fixed format, current") &&
              NULL != strstr(b, "Sense key: Illegal Request"),
          "sg_get_sense_str(fixed sense) -> Fixed format + Illegal Request");

    memset(b, 0, sizeof(b));
    hex2str(raw, (int)sizeof(raw), "raw: ", 0, (int)sizeof(b), b);
    check(NULL != strstr(b, "de ad be ef"),
          "hex2str({de,ad,be,ef}) -> \"de ad be ef\"");

    if (failures) {
        printf("FAILED: %d 项断言失败\n", failures);
        return 1;
    }
    printf("ALL PASS: 5 项断言\n");
    return 0;
}
