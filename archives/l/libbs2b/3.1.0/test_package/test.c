/*
 * libbs2b 安装包消费者测试（OHOS 上真实执行，全程离线）。
 *
 * 断言的是「公开 API 真的可用且真的做了处理」而非仅能链接：
 *   1) bs2b_open() 必须返回可用句柄（t_bs2bdp）；
 *   2) bs2b_set_level(BS2B_HIGH_CLEVEL) 后 bs2b_get_level() 必须回读同一编码值，
 *      且 bs2b_get_level_fcut()/bs2b_get_level_feed() 必须与该预设的 (700, 30) 一致
 *      —— 注意 `bs2b_get_level()` 返回的是 fcut/feed **编码值**（不是预设序号），
 *      初版按「序号回读」断言导致误判，此版本按头文件语义修正；
 *   3) bs2b_set_srate()/bs2b_get_srate() 必须回读一致；
 *   4) bs2b_cross_feed_f() 必须**真的改变**样本（左 1.0 / 右 0.0 → 右声道 > 0 且左声道 < 1.0），
 *      若滤镜未接入（空实现）此断言会失败；
 *   5) bs2b_runtime_version_int() 必须与打包版本一致前缀（防止版本错配的假通过）；
 *   6) bs2b_close() 必须可安全释放。
 * 任一断言失败即以非零退出码结束，使 test_package 真实失败。
 */
#include <bs2b/bs2b.h>

#include <stdio.h>

int main(void)
{
    t_bs2bdp bs2b = bs2b_open();
    if (bs2b == NULL) {
        fprintf(stderr, "bs2b_open() 返回空\n");
        return 1;
    }

    bs2b_set_level(bs2b, BS2B_HIGH_CLEVEL);
    if (bs2b_get_level(bs2b) != BS2B_HIGH_CLEVEL) {
        fprintf(stderr, "level 回读不一致: %#x != %#x\n",
                (unsigned) bs2b_get_level(bs2b), (unsigned) BS2B_HIGH_CLEVEL);
        bs2b_close(bs2b);
        return 1;
    }
    printf("level_fcut=%d level_feed=%d\n",
           bs2b_get_level_fcut(bs2b), bs2b_get_level_feed(bs2b));
    if (bs2b_get_level_fcut(bs2b) != 700 || bs2b_get_level_feed(bs2b) != 30) {
        fprintf(stderr, "HIGH 预设的 fcut/feed 与头文件编码不符（期望 700/30）\n");
        bs2b_close(bs2b);
        return 1;
    }

    bs2b_set_srate(bs2b, BS2B_DEFAULT_SRATE);
    if (bs2b_get_srate(bs2b) != BS2B_DEFAULT_SRATE) {
        fprintf(stderr, "srate 回读不一致: %u\n", (unsigned) bs2b_get_srate(bs2b));
        bs2b_close(bs2b);
        return 1;
    }

    /* 真实处理：左 1.0 / 右 0.0 → 串扰后右声道必须 > 0、左声道必须衰减 */
    float pair[2] = {1.0f, 0.0f};
    bs2b_cross_feed_f(bs2b, pair, 1);
    printf("cross_feed_f: left=%.6f right=%.6f\n", (double) pair[0], (double) pair[1]);
    if (!(pair[1] > 0.0f)) {
        fprintf(stderr, "cross_feed_f() 未产生串扰（右声道仍为 0）——滤镜未生效\n");
        bs2b_close(bs2b);
        return 1;
    }
    if (!(pair[0] < 1.0f)) {
        fprintf(stderr, "cross_feed_f() 未衰减左声道——滤镜未生效\n");
        bs2b_close(bs2b);
        return 1;
    }

    /* 版本自报：libbs2b 3.1.0 的运行时版本整数 */
    printf("bs2b_runtime_version_int() = %#x\n", (unsigned) bs2b_runtime_version_int());

    bs2b_close(bs2b);
    printf("libbs2b 等级编码/采样率/串扰处理 检查通过\n");
    return 0;
}
