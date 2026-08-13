/* ffms2 test_package：ffms2 API 真调用验证（R34 要求实际调用而非仅 dlsym）
 *
 * 断言清单（4 条）：
 *   1. FFMS_GetVersion() major == 5            —— 库加载 + 版本正确
 *   2. FFMS_SetLogLevel/GetLogLevel 往返一致   —— 日志 API 可用
 *   3. FFMS_CreateIndexer 不存在文件返回 NULL   —— 错误路径可调用 + 链接完整
 *   4. FFMS_DestroyVideoSource(NULL) 不崩溃     —— 空指针安全
 */
#include <stdio.h>
#include <string.h>

/* ffms2 public API header */
#include <ffms.h>

int main(void) {
    /* FFMS_Init: initialise the library (both args 0 for current ABI).
     * Returns void per ffms.h — no return value to check. */
    FFMS_Init(0, 0);

    /* 1. FFMS_GetVersion: verify the library is loaded and returns 5.0.x */
    int ver = FFMS_GetVersion();
    int major = (ver >> 24) & 0xFF;
    int minor = (ver >> 16) & 0xFF;

    if (major != 5) {
        fprintf(stderr, "FAIL: expected ffms2 major version 5, got %d\n", major);
        return 1;
    }
    printf("ffms2 version: %d.%d.%d (raw=0x%08X)\n",
           major, minor, (ver >> 8) & 0xFF, ver);

    /* 2. FFMS_GetLogLevel / FFMS_SetLogLevel: verify log-level round-trip */
    int orig_level = FFMS_GetLogLevel();
    FFMS_SetLogLevel(0);
    int new_level = FFMS_GetLogLevel();
    if (new_level != 0) {
        fprintf(stderr, "FAIL: SetLogLevel(0) did not take effect, got %d\n", new_level);
        return 1;
    }
    FFMS_SetLogLevel(orig_level);

    /* 3. FFMS_CreateIndexer: attempt to create an indexer on a non-existent
       file — this exercises the error-handling path (returns NULL with
       an error message) rather than succeeding, proving the API is
       callable and the library is properly linked. */
    FFMS_ErrorInfo err;
    char errbuf[1024];
    memset(&err, 0, sizeof(err));
    err.BufferSize = sizeof(errbuf);
    err.Buffer = errbuf;

    FFMS_Indexer *indexer = FFMS_CreateIndexer("/dev/null/nonexistent", &err);
    if (indexer != NULL) {
        fprintf(stderr, "FAIL: CreateIndexer unexpectedly succeeded\n");
        return 1;
    }
    printf("CreateIndexer error (expected): %s\n",
           (err.Buffer && err.Buffer[0]) ? err.Buffer : "(no message)");

    /* 4. FFMS_DestroyVideoSource(NULL): null-pointer safety — must not crash */
    FFMS_DestroyVideoSource(NULL);

    printf("All ffms2 API tests passed.\n");
    return 0;
}
