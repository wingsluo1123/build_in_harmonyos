/*
 * test_libespeak_ng.c — libespeak-ng 1.51.0 实质功能测试（R34）
 *
 * 使用 espeak_Initialize + espeak_SetSynthCallback + espeak_Synth 真实合成
 * 一段英文语音，通过 SynthCallback 回调收集 16-bit PCM 采样，写出 WAV 文件，
 * 并校验：
 *   1. espeak_Initialize 返回非负句柄；
 *   2. 回调收到非零样本数（真实音频数据被生成）；
 *   3. WAV 文件大小 > 100 字节（含 RIFF/WAVE 头 + PCM 数据）。
 *
 * 关键 API（espeak-ng 1.51 speak_lib.h）：
 *   - espeak_Initialize(AUDIO_OUTPUT_RETRIEVAL, 0, NULL, options)
 *   - espeak_SetSynthCallback(t_espeak_callback)   // short* wav, int numsamples
 *   - espeak_Synthesize / espeak_Synth 均可；这里用 espeak_Synth
 *   - espeak_Synchronize() 等待合成管线结束
 *
 * 这证明被测包的 TTS 合成管线被真实调用并产出有效音频（非 print-only 空壳）。
 */
#include <espeak-ng/speak_lib.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static short *g_audio = NULL;
static size_t g_audio_len = 0;   /* 样本数 */
static size_t g_audio_cap = 0;

/* SynthCallback：espeak-ng 每生成一段音频即调用；拼接收集 */
static int synth_cb(short *wav, int numsamples, espeak_EVENT *events)
{
    (void)events;
    if (numsamples <= 0)
        return 0;
    if (g_audio_len + (size_t)numsamples > g_audio_cap) {
        size_t newcap = g_audio_cap ? g_audio_cap * 2 : 65536;
        while (newcap < g_audio_len + (size_t)numsamples)
            newcap *= 2;
        short *nb = realloc(g_audio, newcap * sizeof(short));
        if (!nb) {
            fprintf(stderr, "FAIL: realloc(%zu)\n", newcap);
            return -1;
        }
        g_audio = nb;
        g_audio_cap = newcap;
    }
    memcpy(g_audio + g_audio_len, wav, (size_t)numsamples * sizeof(short));
    g_audio_len += (size_t)numsamples;
    return 0; /* 0 = 继续合成 */
}

int main(void)
{
    const char *out_path = "test_libespeak_ng.wav";
    static const char text[] = "Hello world, this is eSpeak NG on HarmonyOS.";
    int ret;
    FILE *fp;

    /* 1) 初始化合成引擎，AUDIO_OUTPUT_RETRIEVAL 模式（不播放，仅检索波形） */
    ret = espeak_Initialize(AUDIO_OUTPUT_RETRIEVAL, 0, NULL,
                            espeakINITIALIZE_PHONEME_EVENTS);
    if (ret < 0) {
        fprintf(stderr, "FAIL: espeak_Initialize returned %d\n", ret);
        return 1;
    }
    printf("espeak_Initialize -> handle %d\n", ret);

    espeak_SetSynthCallback(synth_cb);

    /* 2) 设置语音（en-us 必须存在于 espeak-ng-data；若缺则用默认语音） */
    ret = espeak_SetVoiceByName("en-us");
    if (ret != EE_OK) {
        fprintf(stderr, "WARN: espeak_SetVoiceByName(en-us) = %d, use default\n", ret);
    }

    /* 3) 合成文本（异步，音频经回调收集） */
    ret = espeak_Synth(text, (size_t)strlen(text) + 1, 0, POS_CHARACTER, 0,
                       espeakCHARS_AUTO, NULL, NULL);
    if (ret != EE_OK) {
        fprintf(stderr, "FAIL: espeak_Synth returned %d\n", ret);
        espeak_Terminate();
        return 2;
    }
    printf("espeak_Synth -> EE_OK\n");

    /* 4) 等待合成管线结束 */
    espeak_Synchronize();
    espeak_Terminate();

    if (g_audio_len == 0) {
        fprintf(stderr, "FAIL: no audio samples collected (g_audio_len=0)\n");
        free(g_audio);
        return 3;
    }
    printf("collected %zu audio samples\n", g_audio_len);

    /* 5) 写出 44 字节 RIFF 头 + PCM 数据 */
    fp = fopen(out_path, "wb");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot open %s\n", out_path);
        free(g_audio);
        return 4;
    }
    {
        /* 默认 22050 Hz 单声道 16-bit；espeak 以 22050 输出（除非改参数） */
        unsigned int samplerate = 22050;
        unsigned short nch = 1;
        unsigned short bits = 16;
        unsigned int byte_rate = samplerate * (unsigned int)nch * bits / 8;
        unsigned short align = (unsigned short)(nch * bits / 8);
        unsigned int data_size = (unsigned int)(g_audio_len * sizeof(short));
        unsigned int total = 36 + data_size;

        fwrite("RIFF", 1, 4, fp);
        fwrite(&total, 4, 1, fp);
        fwrite("WAVE", 1, 4, fp);
        fwrite("fmt ", 1, 4, fp);
        {
            unsigned int chunk = 16;
            unsigned short pcm = 1;
            fwrite(&chunk, 4, 1, fp);
            fwrite(&pcm, 2, 1, fp);
            fwrite(&nch, 2, 1, fp);
            fwrite(&samplerate, 4, 1, fp);
            fwrite(&byte_rate, 4, 1, fp);
            fwrite(&align, 2, 1, fp);
            fwrite(&bits, 2, 1, fp);
        }
        fwrite("data", 1, 4, fp);
        fwrite(&data_size, 4, 1, fp);
        fwrite(g_audio, sizeof(short), g_audio_len, fp);
    }
    fclose(fp);

    /* 6) 校验 WAV 非空 */
    {
        long sz = 0;
        fp = fopen(out_path, "rb");
        if (!fp) {
            fprintf(stderr, "FAIL: cannot reopen %s\n", out_path);
            free(g_audio);
            return 5;
        }
        fseek(fp, 0, SEEK_END);
        sz = ftell(fp);
        fclose(fp);
        if (sz < 100) {
            fprintf(stderr, "FAIL: WAV too small (%ld bytes)\n", sz);
            free(g_audio);
            return 6;
        }
        printf("WAV size = %ld bytes (>= 100) -> OK\n", sz);
    }

    free(g_audio);
    printf("TEST PASSED\n");
    return 0;
}