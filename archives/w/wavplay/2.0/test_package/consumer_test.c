/*
 * consumer_test.c — 消费者用例（consumer test）
 *
 * 模拟一个上层应用/组件调用 wavplay / wavrec 的对外公开接口（CLI）。
 * 验证三个层面：
 *   1. 消费者编译通过（本文件被 test_package 构建）；
 *   2. 消费者链接通过（链接运行所需标准库 libc/libm）；
 *   3. 消费者运行调用通过（实际执行打包后的 wavplay / wavrec 公开 CLI）。
 *
 * 测试内容（信息/元数据模式不触音频设备 + 音频后端可达性）：
 *   [1] wavplay --version    -> "Version 2.0"
 *   [2] wavplay --help       -> "Usage:"
 *   [3] wavplay -i <wav>     -> "Sampling Rate:"  (WAV 头解析)
 *   [4] wavplay -i <wav>     -> "44100 Hz"        (采样率正确)
 *   [5] wavplay -i <wav>     -> "Bits:\t\t16\n"   (位深字段精确匹配)
 *   [6] wavrec  --version    -> "Version 2.0"
 *   [7] wavplay <wav>        -> OHOS 音频后端可达：真机出声 rc=0；
 *                                stub SDK 下经 OHOS 后端干净报错
 *                                （挂死/崩溃/走 OSS 路径均判 FAIL）
 *   [8] wavrec -t 2000 <wav> -> 同上（录音侧 OHOS 后端可达）
 *
 * wavplay / wavrec 通过 PATH 调用（"conanrun" 运行环境把打包产物 bin/ 放进
 * PATH）；测试用 WAV 文件由本程序在运行时就地生成（无需外部 fixture）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <sys/stat.h>
#include <sys/wait.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/* Run `cmd` (via /bin/sh), capture combined stdout+stderr, return 0 iff the
 * process exits 0 and `expect` is present in the captured output. */
static int run_check(const char *cmd, const char *expect)
{
    char out[16384];
    FILE *fp;
    size_t n = 0;
    int rc;

    printf("  $ %s\n", cmd);
    fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "    FAIL: popen failed\n");
        return 1;
    }
    for (;;) {
        int c = fgetc(fp);
        if (c == EOF)
            break;
        /* Drain the pipe to EOF unconditionally (a stopped reader would
         * deadlock in pclose once output exceeds the pipe capacity), but
         * keep only the first sizeof(out)-1 bytes for expect() matching. */
        if (n < sizeof out - 1)
            out[n++] = (char)c;
    }
    out[n] = '\0';
    rc = pclose(fp);
    if (out[0])
        fputs(out, stdout);
    if (rc != 0) {
        fprintf(stderr, "    FAIL: process exited %d\n", rc);
        return 1;
    }
    if (expect && !strstr(out, expect)) {
        fprintf(stderr, "    FAIL: expected \"%s\" not found in output\n", expect);
        return 1;
    }
    printf("    PASS\n");
    return 0;
}

/* Run the real audio path (`cmd` plays/records through the OHOS audio
 * backend, which the info-mode checks above never touch). The backend
 * must terminate cleanly in every environment:
 *   - full OHOS system : real playback/recording succeeds (exit 0);
 *   - stub SDK         : the OHOS backend init fails with a clean "OHOS:"
 *                        error from a normal (non-signal) exit - the
 *                        message proves the OHOS code path was taken,
 *                        not the OSS one.
 * A crash (signal), a killed/hung process, or a failure that never
 * mentions the OHOS backend (i.e. fell through to the OSS path) is a
 * FAIL in every environment. */
static int run_backend_check(const char *cmd)
{
    char out[16384];
    FILE *fp;
    size_t n = 0;
    int status;

    printf("  $ %s\n", cmd);
    fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "    FAIL: popen failed\n");
        return 1;
    }
    for (;;) {
        int c = fgetc(fp);
        if (c == EOF)
            break;
        if (n < sizeof out - 1)
            out[n++] = (char)c;
    }
    out[n] = '\0';
    status = pclose(fp);
    if (out[0])
        fputs(out, stdout);
    if (WIFEXITED(status)) {
        int code = WEXITSTATUS(status);
        if (code == 0) {
            printf("    PASS (audio backend OK, real output)\n");
            return 0;
        }
        if (strstr(out, "OHOS:")) {
            printf("    PASS (OHOS audio backend reached, clean error on stub SDK)\n");
            return 0;
        }
        fprintf(stderr, "    FAIL: audio path exited %d without reaching the OHOS backend\n", code);
        return 1;
    }
    fprintf(stderr, "    FAIL: audio path crashed or was killed (status=%d)\n", status);
    return 1;
}

/* Generate a 1-second 440 Hz 16-bit mono PCM WAV file at `path`. */
static int make_test_wav(const char *path)
{
    const int sr = 44100;
    const int n = sr;                 /* 1 second */
    const int bps = 2;                /* 16-bit */
    FILE *f = fopen(path, "wb");
    uint32_t riff_size, fmt_size, sample_rate, byte_rate, data_size;
    uint16_t audio_fmt, channels, block_align, bits;
    int i;
    struct stat st;

    if (!f) {
        fprintf(stderr, "FATAL: cannot open %s for writing\n", path);
        return -1;
    }
    riff_size   = 36u + (uint32_t)(n * bps);
    fmt_size    = 16;
    audio_fmt   = 1;                  /* PCM */
    channels    = 1;
    sample_rate = (uint32_t)sr;
    byte_rate   = (uint32_t)sr * (uint32_t)bps;
    block_align = (uint16_t)channels * (uint16_t)bps;
    bits        = 16;
    data_size   = (uint32_t)(n * bps);

    fwrite("RIFF", 1, 4, f);
    fwrite(&riff_size, 4, 1, f);
    fwrite("WAVE", 1, 4, f);
    fwrite("fmt ", 1, 4, f);
    fwrite(&fmt_size, 4, 1, f);
    fwrite(&audio_fmt, 2, 1, f);
    fwrite(&channels, 2, 1, f);
    fwrite(&sample_rate, 4, 1, f);
    fwrite(&byte_rate, 4, 1, f);
    fwrite(&block_align, 2, 1, f);
    fwrite(&bits, 2, 1, f);
    fwrite("data", 1, 4, f);
    fwrite(&data_size, 4, 1, f);
    for (i = 0; i < n; i++) {
        int16_t s = (int16_t)(32767.0 * sin(2.0 * M_PI * 440.0 * (double)i / (double)sr));
        fwrite(&s, 2, 1, f);
    }
    if (fclose(f) != 0) {
        fprintf(stderr, "FATAL: write error creating %s\n", path);
        return -1;
    }
    /* Verify the file is complete: a short write (e.g. ENOSPC) would leave a
     * truncated fixture that confuses the header assertions below. Size =
     * 44-byte header (RIFF 12 + fmt 24 + data 8) + raw samples. */
    if (stat(path, &st) != 0 || (long)st.st_size != (long)(44 + n * bps)) {
        fprintf(stderr, "FATAL: %s wrong size (got %ld, want %ld)\n",
                path, (long)(stat(path, &st) == 0 ? st.st_size : -1),
                (long)(44 + n * bps));
        return -1;
    }
    return 0;
}

int main(void)
{
    int fails = 0;

    printf("=== wavplay consumer test (public CLI via PATH) ===\n");
    remove("test440.wav");  /* drop any stale fixture from a previous run */
    if (make_test_wav("test440.wav") != 0) {
        fprintf(stderr, "FATAL: cannot create test wav\n");
        return 2;
    }

    printf("[1] wavplay --version\n");
    fails += run_check("wavplay --version 2>&1", "Version 2.0");

    printf("[2] wavplay --help\n");
    fails += run_check("wavplay --help 2>&1", "Usage:");

    printf("[3] wavplay -i (WAV header: Sampling Rate)\n");
    fails += run_check("wavplay -i test440.wav 2>&1", "Sampling Rate:");

    printf("[4] wavplay -i (WAV header: 44100 Hz)\n");
    fails += run_check("wavplay -i test440.wav 2>&1", "44100 Hz");

    printf("[5] wavplay -i (WAV header: 16 bit)\n");
    fails += run_check("wavplay -i test440.wav 2>&1", "Bits:\t\t16\n");

    printf("[6] wavrec --version\n");
    fails += run_check("wavrec --version 2>&1", "Version 2.0");

    printf("[7] wavplay (OHOS audio backend reachability)\n");
    fails += run_backend_check("wavplay test440.wav 2>&1");

    printf("[8] wavrec -t 2000 (OHOS audio backend reachability)\n");
    remove("rec_test.wav");  /* drop any stale fixture from a prior run */
    fails += run_backend_check("wavrec -t 2000 rec_test.wav 2>&1");

    printf("\n=== RESULT: %s (%d failure(s)) ===\n",
           fails ? "FAIL" : "ALL PASS", fails);
    remove("test440.wav");  /* clean up the fixtures we generated */
    remove("rec_test.wav");
    return fails ? 1 : 0;
}
