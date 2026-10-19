/*
 * test.c — libespeak-ng 1.51.0 基础功能测试（R34 实质 API 调用）
 *
 * 验证被测包 libespeak-ng 库可被链接、espeak_Initialize 可正常初始化
 * TTS 引擎（AUDIO_OUTPUT_RETRIEVAL 模式）并成功终止。这是对 "库可用 +
 * 引擎可初始化" 的最小子集验证（非 print-only 空壳）。
 */
#include <espeak-ng/speak_lib.h>

#include <stdio.h>

int main(void)
{
    int ret = espeak_Initialize(AUDIO_OUTPUT_RETRIEVAL, 0, NULL,
                                espeakINITIALIZE_PHONEME_EVENTS);
    if (ret < 0) {
        fprintf(stderr, "FAIL: espeak_Initialize returned %d\n", ret);
        return 1;
    }
    printf("espeak_Initialize -> handle %d (OK)\n", ret);
    espeak_Terminate();
    printf("espeak_Terminate OK\n");
    printf("TEST PASSED\n");
    return 0;
}