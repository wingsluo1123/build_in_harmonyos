/*
 * test_package/picotts_engine_contract.c
 *
 * libttspico 消费者契约测试 —— 真实调用被测包公共 API，端到端完成一次
 * 文本到语音（TTS）合成，并对返回的 PCM 数据做实质断言。
 *
 * 覆盖的公共 API（picoapi.h）：
 *   pico_initialize / pico_terminate
 *   pico_loadResource / pico_unloadResource / pico_getResourceName
 *   pico_createVoiceDefinition / pico_addResourceToVoiceDefinition /
 *   pico_releaseVoiceDefinition
 *   pico_newEngine / pico_disposeEngine
 *   pico_putTextUtf8 / pico_getData
 *
 * 该测试实质依赖被测包：
 *   - 链接必须命中 libttspico（删掉产物 lib/ 后链接失败，L1e 反向验证）
 *   - 头文件必须来自被测包 include/（删掉 include/ 后编译失败）
 *   - 运行必须真实加载包内 share/pico/lang 的语音资源（删掉资源后非 0 退出）
 *   - PCM 输出字节数 > 0 才判定合成成功（空壳实现必然失败）
 *
 * 语音资源目录由 argv[1] 显式传入（包内 share/pico/lang 的绝对路径），
 * 因为上游 pico2wave 的 picolangdir 是编译期常量，而库 API 允许显式指定。
 *
 * 用法: ./picotts_engine_contract <lingware_dir>
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <picoapi.h>

/* 上游 pico2wave.c 使用的内存池规模（字节） */
#define PICO_MEM_SIZE 2500000
/* 单次取数据的缓冲区（上游 MAX_OUTBUF_SIZE 同值） */
#define OUTBUF_SIZE 16384

#define VOICE_NAME "PicoVoice"
#define TA_FILE "en-US_ta.bin"
#define SG_FILE "en-US_lh0_sg.bin"

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

int main(int argc, char **argv)
{
    const char *lingware_dir = NULL;
    char ta_path[4096];
    char sg_path[4096];

    void *mem_area = NULL;
    pico_System pico_system = NULL;
    pico_Resource ta_resource = NULL;
    pico_Resource sg_resource = NULL;
    pico_Engine pico_engine = NULL;

    pico_Retstring ta_resource_name;
    pico_Retstring sg_resource_name;
    pico_Retstring message;

    pico_Status status;
    pico_Int16 bytes_sent = 0;
    pico_Int16 bytes_recv = 0;
    pico_Int16 data_type = 0;
    pico_Int16 observed_data_type = 0;
    int outbuf[OUTBUF_SIZE / (int) sizeof(int)];
    long total_bytes = 0;

    const char *text = "Hello world. Pico text to speech on HarmonyOS.";
    const pico_Char *cursor;
    size_t text_remaining;
    int same_data_type = 1;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <lingware_dir>\n", argv[0]);
        return 2;
    }
    lingware_dir = argv[1];

    if (snprintf(ta_path, sizeof(ta_path), "%s/%s", lingware_dir, TA_FILE)
            >= (int) sizeof(ta_path)
        || snprintf(sg_path, sizeof(sg_path), "%s/%s", lingware_dir, SG_FILE)
            >= (int) sizeof(sg_path)) {
        fprintf(stderr, "lingware path too long\n");
        return 2;
    }

    /* ── 1. 资源文件确实随包分发 ───────────────────────────────── */
    {
        FILE *probe = fopen(ta_path, "rb");
        check(probe != NULL, "packaged lingware en-US_ta.bin is readable");
        if (probe != NULL) {
            fclose(probe);
        }
        probe = fopen(sg_path, "rb");
        check(probe != NULL, "packaged lingware en-US_lh0_sg.bin is readable");
        if (probe != NULL) {
            fclose(probe);
        }
    }

    /* ── 2. 系统初始化 ─────────────────────────────────────────── */
    mem_area = malloc(PICO_MEM_SIZE);
    check(mem_area != NULL, "pico memory pool allocated");
    if (mem_area == NULL) {
        goto done;
    }

    status = pico_initialize(mem_area, PICO_MEM_SIZE, &pico_system);
    check(status == PICO_OK, "pico_initialize() returns PICO_OK");
    if (status != PICO_OK) {
        pico_getSystemStatusMessage(NULL, status, message);
        fprintf(stderr, "pico_initialize failed: %s\n", message);
        goto done;
    }
    check(pico_system != NULL, "pico_initialize() yields a system handle");

    /* ── 3. 加载语音资源 ───────────────────────────────────────── */
    status = pico_loadResource(pico_system, (const pico_Char *) ta_path,
                               &ta_resource);
    check(status == PICO_OK, "pico_loadResource(ta) returns PICO_OK");
    if (status != PICO_OK) {
        pico_getSystemStatusMessage(pico_system, status, message);
        fprintf(stderr, "loadResource(ta) failed: %s\n", message);
        goto done;
    }

    status = pico_loadResource(pico_system, (const pico_Char *) sg_path,
                               &sg_resource);
    check(status == PICO_OK, "pico_loadResource(sg) returns PICO_OK");
    if (status != PICO_OK) {
        pico_getSystemStatusMessage(pico_system, status, message);
        fprintf(stderr, "loadResource(sg) failed: %s\n", message);
        goto done;
    }

    status = pico_getResourceName(pico_system, ta_resource, ta_resource_name);
    check(status == PICO_OK, "pico_getResourceName(ta) returns PICO_OK");
    check(status == PICO_OK && ta_resource_name[0] != '\0',
          "ta resource exposes a non-empty resource name");

    status = pico_getResourceName(pico_system, sg_resource, sg_resource_name);
    check(status == PICO_OK, "pico_getResourceName(sg) returns PICO_OK");
    check(status == PICO_OK && sg_resource_name[0] != '\0',
          "sg resource exposes a non-empty resource name");

    /* ── 4. 语音定义 ───────────────────────────────────────────── */
    status = pico_createVoiceDefinition(pico_system,
                                        (const pico_Char *) VOICE_NAME);
    check(status == PICO_OK, "pico_createVoiceDefinition() returns PICO_OK");

    status = pico_addResourceToVoiceDefinition(
        pico_system, (const pico_Char *) VOICE_NAME,
        (const pico_Char *) ta_resource_name);
    check(status == PICO_OK,
          "pico_addResourceToVoiceDefinition(ta) returns PICO_OK");

    status = pico_addResourceToVoiceDefinition(
        pico_system, (const pico_Char *) VOICE_NAME,
        (const pico_Char *) sg_resource_name);
    check(status == PICO_OK,
          "pico_addResourceToVoiceDefinition(sg) returns PICO_OK");

    /* ── 5. 引擎 ───────────────────────────────────────────────── */
    status = pico_newEngine(pico_system, (const pico_Char *) VOICE_NAME,
                            &pico_engine);
    check(status == PICO_OK, "pico_newEngine() returns PICO_OK");
    if (status != PICO_OK) {
        pico_getSystemStatusMessage(pico_system, status, message);
        fprintf(stderr, "newEngine failed: %s\n", message);
        goto done;
    }
    check(pico_engine != NULL, "pico_newEngine() yields an engine handle");

    /* ── 6. 合成：投喂文本并回收 PCM ──────────────────────────── */
    cursor = (const pico_Char *) text;
    text_remaining = strlen(text) + 1; /* 含结尾 '\0' 以结束输入 */

    while (text_remaining > 0) {
        status = pico_putTextUtf8(pico_engine, cursor,
                                  (pico_Int16) text_remaining, &bytes_sent);
        if (status != PICO_OK) {
            pico_getSystemStatusMessage(pico_system, status, message);
            fprintf(stderr, "pico_putTextUtf8 failed (%d): %s\n", status,
                    message);
            check(0, "pico_putTextUtf8() returns PICO_OK");
            goto done;
        }
        check(bytes_sent > 0, "pico_putTextUtf8() consumes at least one byte");
        if (bytes_sent <= 0) {
            goto done;
        }
        text_remaining -= (size_t) bytes_sent;
        cursor += bytes_sent;

        do {
            bytes_recv = 0;
            data_type = 0;
            status = pico_getData(pico_engine, (void *) outbuf, OUTBUF_SIZE,
                                  &bytes_recv, &data_type);
            if (status != PICO_STEP_BUSY && status != PICO_STEP_IDLE) {
                pico_getSystemStatusMessage(pico_system, status, message);
                fprintf(stderr, "pico_getData failed (%d): %s\n", status,
                        message);
                check(0, "pico_getData() returns BUSY or IDLE");
                goto done;
            }
            if (bytes_recv > 0) {
                total_bytes += bytes_recv;
                if (observed_data_type == 0) {
                    observed_data_type = data_type;
                } else if (observed_data_type != data_type) {
                    same_data_type = 0;
                }
            }
        } while (status == PICO_STEP_BUSY);
    }

    check(total_bytes > 0,
          "TTS synthesis produced a non-empty PCM stream");
    check(observed_data_type == PICO_DATA_PCM_16BIT,
          "returned samples are 16-bit PCM (PICO_DATA_PCM_16BIT)");
    check(same_data_type == 1,
          "data type stays stable across the whole synthesis");
    check(total_bytes % 2 == 0,
          "16-bit PCM stream length is an even number of bytes");
    printf("INFO: synthesized %ld bytes of PCM\n", total_bytes);

done:
    /* ── 7. 资源回收（逆序）───────────────────────────────────── */
    if (pico_engine != NULL) {
        status = pico_disposeEngine(pico_system, &pico_engine);
        check(status == PICO_OK, "pico_disposeEngine() returns PICO_OK");
    }
    if (pico_system != NULL) {
        status = pico_releaseVoiceDefinition(pico_system,
                                            (const pico_Char *) VOICE_NAME);
        check(status == PICO_OK,
              "pico_releaseVoiceDefinition() returns PICO_OK");
    }
    if (sg_resource != NULL) {
        status = pico_unloadResource(pico_system, &sg_resource);
        check(status == PICO_OK, "pico_unloadResource(sg) returns PICO_OK");
    }
    if (ta_resource != NULL) {
        status = pico_unloadResource(pico_system, &ta_resource);
        check(status == PICO_OK, "pico_unloadResource(ta) returns PICO_OK");
    }
    if (pico_system != NULL) {
        status = pico_terminate(&pico_system);
        check(status == PICO_OK, "pico_terminate() returns PICO_OK");
    }
    free(mem_area);

    printf("\nCONTRACT: %d assertions, %d failed\n", g_assertions, g_failures);
    if (g_failures != 0) {
        printf("CONTRACT-FAILED\n");
        return 1;
    }
    printf("CONTRACT-OK\n");
    return 0;
}
