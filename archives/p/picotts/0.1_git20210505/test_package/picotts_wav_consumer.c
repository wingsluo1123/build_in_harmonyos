/*
 * test_package/picotts_wav_consumer.c
 *
 * HarmonyOS PC 消费者端到端用例（完整流程，非纯断言）：
 *
 *   文本 → libttspico 合成 → 落盘 16kHz/单声道/16-bit PCM WAV → 重新读取该 WAV
 *   并解析 RIFF/WAVE 容器校验其真实可用
 *
 * 与 picotts_engine_contract.c 的区别：本条用例**产出真实制品文件**（.wav），
 * 属于"跑通功能/流程"的消费者用例：它必须真正写出一个能被 WAV 容器规范解析的
 * 文件，任何一步（合成/写盘/容器封装）失效都会让校验失败。
 *
 * OHOS 侧特有约束（由 test_package/conanfile.py 负责）：
 *   - 新编译出的消费者 ELF 必须先用 binary-sign-tool 自签名才能在 OHOS 上执行，
 *     所以本用例运行的是一份 self-signed 副本；
 *   - 输出 WAV 必须落在可写目录（OHOS 根为只读，测试用
 *     /data/storage/el2/base/cache 下的沙箱目录）。
 *
 * 用法: ./picotts_wav_consumer <lingware_dir> <out.wav>
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <picoapi.h>

#define PICO_MEM_SIZE 2500000
#define OUTBUF_SIZE 16384
#define VOICE_NAME "PicoVoice"
#define SAMPLE_RATE 16000
#define CHANNELS 1
#define BITS_PER_SAMPLE 16
#define WAV_HEADER_SIZE 44

static int g_assertions = 0;
static int g_failures = 0;

static void check(int condition, const char *what)
{
    g_assertions++;
    if (condition) {
        printf("PASS %d: %s\n", g_assertions, what);
    } else {
        g_failures++;
        printf("FAIL %d: %s\n", g_assertions, what);
    }
}

static void put_le32(uint8_t *dst, uint32_t value)
{
    dst[0] = (uint8_t) (value & 0xff);
    dst[1] = (uint8_t) ((value >> 8) & 0xff);
    dst[2] = (uint8_t) ((value >> 16) & 0xff);
    dst[3] = (uint8_t) ((value >> 24) & 0xff);
}

static void put_le16(uint8_t *dst, uint16_t value)
{
    dst[0] = (uint8_t) (value & 0xff);
    dst[1] = (uint8_t) ((value >> 8) & 0xff);
}

static uint32_t get_le32(const uint8_t *src)
{
    return (uint32_t) src[0] | ((uint32_t) src[1] << 8)
           | ((uint32_t) src[2] << 16) | ((uint32_t) src[3] << 24);
}

static uint16_t get_le16(const uint8_t *src)
{
    return (uint16_t) ((uint16_t) src[0] | ((uint16_t) src[1] << 8));
}

/* 写 44 字节标准 PCM WAV 头（data 大小留到合成结束再回填） */
static void build_wav_header(uint8_t *header, uint32_t data_bytes)
{
    uint32_t byte_rate = SAMPLE_RATE * CHANNELS * (BITS_PER_SAMPLE / 8);
    uint16_t block_align = (uint16_t) (CHANNELS * (BITS_PER_SAMPLE / 8));

    memcpy(header + 0, "RIFF", 4);
    put_le32(header + 4, 36 + data_bytes);
    memcpy(header + 8, "WAVE", 4);
    memcpy(header + 12, "fmt ", 4);
    put_le32(header + 16, 16);              /* PCM fmt chunk size */
    put_le16(header + 20, 1);               /* audio format = PCM */
    put_le16(header + 22, CHANNELS);
    put_le32(header + 24, SAMPLE_RATE);
    put_le32(header + 28, byte_rate);
    put_le16(header + 32, block_align);
    put_le16(header + 34, BITS_PER_SAMPLE);
    memcpy(header + 36, "data", 4);
    put_le32(header + 40, data_bytes);
}

int main(int argc, char **argv)
{
    const char *lingware_dir;
    const char *wav_path;
    char ta_path[4096];
    char sg_path[4096];

    void *mem_area = NULL;
    pico_System system = NULL;
    pico_Resource ta_resource = NULL;
    pico_Resource sg_resource = NULL;
    pico_Engine engine = NULL;
    pico_Retstring ta_name;
    pico_Retstring sg_name;
    pico_Retstring message;
    pico_Status status;

    const char *text = "HarmonyOS PC end to end text to speech consumer test.";
    const pico_Char *cursor;
    size_t remaining;
    pico_Int16 bytes_sent = 0;
    pico_Int16 bytes_recv = 0;
    pico_Int16 data_type = 0;
    int same_data_type = 1;
    int outbuf[OUTBUF_SIZE / (int) sizeof(int)];
    uint32_t pcm_bytes = 0;

    FILE *wav = NULL;
    uint8_t header[WAV_HEADER_SIZE];
    uint8_t parsed[WAV_HEADER_SIZE];
    long file_size = 0;

    if (argc < 3) {
        fprintf(stderr, "usage: %s <lingware_dir> <out.wav>\n", argv[0]);
        return 2;
    }
    lingware_dir = argv[1];
    wav_path = argv[2];

    if (snprintf(ta_path, sizeof(ta_path), "%s/en-US_ta.bin", lingware_dir)
            >= (int) sizeof(ta_path)
        || snprintf(sg_path, sizeof(sg_path), "%s/en-US_lh0_sg.bin", lingware_dir)
            >= (int) sizeof(sg_path)) {
        fprintf(stderr, "lingware path too long\n");
        return 2;
    }

    /* ── 1. 系统与资源 ─────────────────────────────────────────── */
    mem_area = malloc(PICO_MEM_SIZE);
    check(mem_area != NULL, "allocated pico memory pool");
    if (mem_area == NULL) {
        goto done;
    }
    status = pico_initialize(mem_area, PICO_MEM_SIZE, &system);
    check(status == PICO_OK, "pico_initialize() returns PICO_OK");
    if (status != PICO_OK) {
        goto done;
    }
    status = pico_loadResource(system, (const pico_Char *) ta_path, &ta_resource);
    check(status == PICO_OK, "loaded en-US text-analysis resource");
    status = pico_loadResource(system, (const pico_Char *) sg_path, &sg_resource);
    check(status == PICO_OK, "loaded en-US signal-generation resource");
    if (ta_resource == NULL || sg_resource == NULL) {
        goto done;
    }
    check(pico_getResourceName(system, ta_resource, ta_name) == PICO_OK
              && ta_name[0] != '\0',
          "ta resource name resolved");
    check(pico_getResourceName(system, sg_resource, sg_name) == PICO_OK
              && sg_name[0] != '\0',
          "sg resource name resolved");
    check(pico_createVoiceDefinition(system, (const pico_Char *) VOICE_NAME)
              == PICO_OK,
          "created voice definition");
    check(pico_addResourceToVoiceDefinition(
              system, (const pico_Char *) VOICE_NAME,
              (const pico_Char *) ta_name) == PICO_OK,
          "attached ta resource to voice");
    check(pico_addResourceToVoiceDefinition(
              system, (const pico_Char *) VOICE_NAME,
              (const pico_Char *) sg_name) == PICO_OK,
          "attached sg resource to voice");
    status = pico_newEngine(system, (const pico_Char *) VOICE_NAME, &engine);
    check(status == PICO_OK && engine != NULL, "created TTS engine");
    if (engine == NULL) {
        goto done;
    }

    /* ── 2. 合成并落盘真实 WAV（消费者流程）────────────────────── */
    wav = fopen(wav_path, "wb");
    check(wav != NULL, "opened output WAV for writing");
    if (wav == NULL) {
        goto done;
    }
    build_wav_header(header, 0);
    check(fwrite(header, 1, WAV_HEADER_SIZE, wav) == WAV_HEADER_SIZE,
          "wrote placeholder WAV header");

    cursor = (const pico_Char *) text;
    remaining = strlen(text) + 1;
    while (remaining > 0) {
        status = pico_putTextUtf8(engine, cursor, (pico_Int16) remaining,
                                  &bytes_sent);
        if (status != PICO_OK || bytes_sent <= 0) {
            pico_getSystemStatusMessage(system, status, message);
            fprintf(stderr, "pico_putTextUtf8 failed (%d): %s\n", status, message);
            check(0, "pico_putTextUtf8() consumed input");
            goto done;
        }
        remaining -= (size_t) bytes_sent;
        cursor += bytes_sent;
        do {
            bytes_recv = 0;
            data_type = 0;
            status = pico_getData(engine, (void *) outbuf, OUTBUF_SIZE,
                                  &bytes_recv, &data_type);
            if (status != PICO_STEP_BUSY && status != PICO_STEP_IDLE) {
                pico_getSystemStatusMessage(system, status, message);
                fprintf(stderr, "pico_getData failed (%d): %s\n", status, message);
                check(0, "pico_getData() returned BUSY or IDLE");
                goto done;
            }
            if (bytes_recv > 0) {
                if (data_type != PICO_DATA_PCM_16BIT) {
                    same_data_type = 0;
                }
                if (fwrite(outbuf, 1, (size_t) bytes_recv, wav)
                        != (size_t) bytes_recv) {
                    check(0, "wrote PCM samples to WAV");
                    goto done;
                }
                pcm_bytes += (uint32_t) bytes_recv;
            }
        } while (status == PICO_STEP_BUSY);
    }
    check(pcm_bytes > 0, "synthesis produced a non-empty PCM stream");
    check(same_data_type == 1, "engine returned 16-bit PCM throughout");

    /* 回填真实 data 大小 */
    build_wav_header(header, pcm_bytes);
    rewind(wav);
    check(fwrite(header, 1, WAV_HEADER_SIZE, wav) == WAV_HEADER_SIZE,
          "patched WAV header with real data size");
    check(fclose(wav) == 0, "closed output WAV");
    wav = NULL;

    /* ── 3. 重新读取并解析容器（消费者侧校验）──────────────────── */
    wav = fopen(wav_path, "rb");
    check(wav != NULL, "re-opened produced WAV for validation");
    if (wav == NULL) {
        goto done;
    }
    check(fread(parsed, 1, WAV_HEADER_SIZE, wav) == WAV_HEADER_SIZE,
          "read back 44-byte WAV header");
    if (fseek(wav, 0, SEEK_END) == 0) {
        file_size = ftell(wav);
    }
    check(file_size == (long) (WAV_HEADER_SIZE + pcm_bytes),
          "file size matches header + PCM payload");
    check(memcmp(parsed + 0, "RIFF", 4) == 0, "container is RIFF");
    check(memcmp(parsed + 8, "WAVE", 4) == 0, "form type is WAVE");
    check(memcmp(parsed + 12, "fmt ", 4) == 0, "fmt chunk present");
    check(get_le16(parsed + 20) == 1, "audio format is linear PCM");
    check(get_le16(parsed + 22) == CHANNELS, "mono (1 channel)");
    check(get_le32(parsed + 24) == SAMPLE_RATE, "sample rate is 16000 Hz");
    check(get_le16(parsed + 34) == BITS_PER_SAMPLE, "16 bits per sample");
    check(memcmp(parsed + 36, "data", 4) == 0, "data chunk present");
    check(get_le32(parsed + 40) == pcm_bytes,
          "data chunk size equals written PCM bytes");
    check(get_le32(parsed + 4) == 36 + pcm_bytes, "RIFF size field consistent");

done:
    if (wav != NULL) {
        fclose(wav);
    }
    if (engine != NULL) {
        pico_disposeEngine(system, &engine);
    }
    if (system != NULL) {
        pico_releaseVoiceDefinition(system, (const pico_Char *) VOICE_NAME);
        if (sg_resource != NULL) {
            pico_unloadResource(system, &sg_resource);
        }
        if (ta_resource != NULL) {
            pico_unloadResource(system, &ta_resource);
        }
        pico_terminate(&system);
    }
    free(mem_area);

    printf("\nWAV-CONSUMER: %d assertions, %d failed, %u PCM bytes -> %s\n",
           g_assertions, g_failures, pcm_bytes, wav_path);
    if (g_failures != 0) {
        printf("WAV-CONSUMER-FAILED\n");
        return 1;
    }
    printf("WAV-CONSUMER-OK\n");
    return 0;
}
