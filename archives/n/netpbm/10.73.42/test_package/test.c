/*
 * netpbm 消费者用例（真实调用被测包的 API，非空壳测试）：
 *   1. 用 libnetpbm 的 PAM 写接口生成一幅 PPM(P6) 图像；
 *   2. 用读接口回读，逐像素校验，确保库的读写路径都真正可用。
 * 覆盖符号：pm_init / pm_openw / pm_openr / pnm_writepaminit / pnm_writepamrow /
 *           pnm_allocpamrow / pnm_readpaminit / pnm_readpamrow / pnm_freepamrow / pm_close
 */
#include <stdio.h>
#include <string.h>

#include <netpbm/pam.h>
#include <netpbm/pm.h>

#define TEST_WIDTH 4
#define TEST_HEIGHT 3

static sample expected_red(int x) {
    return (sample)(x * 60);
}

int main(int argc, char **argv) {
    const char *path = (argc > 1) ? argv[1] : "sample.pam";
    struct pam out_pam, in_pam;
    tuple *row;
    FILE *fp;
    int x, y, failures = 0;

    pm_init("test_netpbm", 0);

    /* 1) 写出 PPM 图像 */
    fp = pm_openw(path);

    memset(&out_pam, 0, sizeof(out_pam));
    out_pam.size = sizeof(out_pam);
    out_pam.len = PAM_STRUCT_SIZE(tuple_type);
    out_pam.file = fp;
    out_pam.format = PPM_FORMAT;
    out_pam.height = TEST_HEIGHT;
    out_pam.width = TEST_WIDTH;
    out_pam.depth = 3;
    out_pam.maxval = 255;
    out_pam.bytes_per_sample = 1;

    pnm_writepaminit(&out_pam);

    row = pnm_allocpamrow(&out_pam);
    for (y = 0; y < TEST_HEIGHT; ++y) {
        for (x = 0; x < TEST_WIDTH; ++x) {
            row[x][PAM_RED_PLANE] = expected_red(x);
            row[x][PAM_GRN_PLANE] = (sample)(x + y);
            row[x][PAM_BLU_PLANE] = (sample)(255 - x);
        }
        pnm_writepamrow(&out_pam, row);
    }
    pnm_freepamrow(row);
    pm_close(fp);

    /* 2) 回读并校验尺寸与像素值 */
    fp = pm_openr(path);
    memset(&in_pam, 0, sizeof(in_pam));
    pnm_readpaminit(fp, &in_pam, PAM_STRUCT_SIZE(tuple_type));

    if (in_pam.width != TEST_WIDTH || in_pam.height != TEST_HEIGHT || in_pam.depth != 3) {
        fprintf(stderr, "尺寸校验失败: width=%d height=%d depth=%d\n",
                in_pam.width, in_pam.height, in_pam.depth);
        pm_close(fp);
        return 1;
    }

    row = pnm_allocpamrow(&in_pam);
    for (y = 0; y < TEST_HEIGHT; ++y) {
        pnm_readpamrow(&in_pam, row);
        for (x = 0; x < TEST_WIDTH; ++x) {
            if (row[x][PAM_RED_PLANE] != expected_red(x)) {
                fprintf(stderr, "像素校验失败 (%d,%d): R=%lu 期望=%lu\n",
                        x, y, (unsigned long)row[x][PAM_RED_PLANE],
                        (unsigned long)expected_red(x));
                ++failures;
            }
        }
    }
    pnm_freepamrow(row);
    pm_close(fp);

    if (failures) {
        return 1;
    }

    printf("libnetpbm 读写校验通过: %dx%d PPM -> %s\n", TEST_WIDTH, TEST_HEIGHT, path);
    return 0;
}
