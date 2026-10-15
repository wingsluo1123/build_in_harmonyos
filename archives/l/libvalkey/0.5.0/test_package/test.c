#include <stdio.h>
#include <string.h>
#include <valkey/valkey.h>

/* 消费者验证（R34/PF3）：实际链接 libvalkey 并调用公共解析 API。
   不依赖运行中的 valkey-server：直接向 valkeyReader 投喂 RESP2
   简单字符串 "+PONG\r\n"，验证库的协议解析能力。 */
int main(void) {
    valkeyReader *reader = valkeyReaderCreate();
    if (!reader) {
        fprintf(stderr, "FAIL: valkeyReaderCreate returned NULL\n");
        return 1;
    }

    const char *resp = "+PONG\r\n";
    if (valkeyReaderFeed(reader, resp, strlen(resp)) != VALKEY_OK) {
        fprintf(stderr, "FAIL: valkeyReaderFeed failed\n");
        valkeyReaderFree(reader);
        return 1;
    }

    void *reply = NULL;
    if (valkeyReaderGetReply(reader, &reply) != VALKEY_OK || reply == NULL) {
        fprintf(stderr, "FAIL: valkeyReaderGetReply returned no reply\n");
        valkeyReaderFree(reader);
        return 1;
    }

    valkeyReply *r = (valkeyReply *)reply;
    /* RESP2 "+PONG\r\n" 简单字符串在 libvalkey 中解析为 STATUS 类型 */
    if (r->type != VALKEY_REPLY_STATUS || r->len != 4 ||
        strncmp(r->str, "PONG", 4) != 0) {
        fprintf(stderr, "FAIL: unexpected reply (type=%d len=%lld str=%s)\n",
                r->type, (long long)r->len, r->str ? r->str : "(null)");
        freeReplyObject(reply);
        valkeyReaderFree(reader);
        return 1;
    }

    printf("libvalkey consumer test: PASSED (RESP2 simple string parsed, len=%lld)\n",
           (long long)r->len);
    freeReplyObject(reply);
    valkeyReaderFree(reader);
    return 0;
}