/*
 * test_package/test.c — coturn 4.5.2 消费者视角测试
 *
 * 验证 libturnclient 的 STUN/TURN 消息 API 可正确链接和调用。
 * 使用 _str 系列 API (原始字节缓冲区接口) 进行测试：
 *   1. 创建 STUN BINDING 请求并验证消息类型
 *   2. 创建 TURN ALLOCATE 请求并验证消息类型
 *   3. 验证 STUN 消息长度解析
 */
#include <turn/client/ns_turn_msg.h>
#include <stdio.h>
#include <string.h>

#define BUF_SIZE 2048

int main(void) {
    uint8_t buf[BUF_SIZE];
    size_t len = 0;
    int failures = 0;

    /* ── 测试 1: 创建 STUN BINDING 请求 ── */
    memset(buf, 0, BUF_SIZE);
    len = 0;
    stun_init_request_str(STUN_METHOD_BINDING, buf, &len);

    if (len == 0) {
        fprintf(stderr, "FAIL: stun_init_request_str(BINDING) produced empty message\n");
        failures++;
    }

    /* 验证是合法的 STUN 命令消息 */
    if (!stun_is_command_message_str(buf, len)) {
        fprintf(stderr, "FAIL: BINDING request not recognized as STUN command message\n");
        failures++;
    }

    /* 验证是请求类型 (非响应/指示) */
    if (!stun_is_request_str(buf, len)) {
        fprintf(stderr, "FAIL: BINDING request not recognized as request type\n");
        failures++;
    }

    /* 验证方法 = BINDING */
    uint16_t method = stun_get_method_str(buf, len);
    if (method != STUN_METHOD_BINDING) {
        fprintf(stderr, "FAIL: BINDING method=%u, expected %u\n", method, STUN_METHOD_BINDING);
        failures++;
    }

    /* ── 测试 2: 创建 TURN ALLOCATE 请求 ── */
    memset(buf, 0, BUF_SIZE);
    len = 0;
    stun_init_request_str(STUN_METHOD_ALLOCATE, buf, &len);

    if (len == 0) {
        fprintf(stderr, "FAIL: stun_init_request_str(ALLOCATE) produced empty message\n");
        failures++;
    }

    if (!stun_is_command_message_str(buf, len)) {
        fprintf(stderr, "FAIL: ALLOCATE request not recognized as STUN command message\n");
        failures++;
    }

    method = stun_get_method_str(buf, len);
    if (method != STUN_METHOD_ALLOCATE) {
        fprintf(stderr, "FAIL: ALLOCATE method=%u, expected %u\n", method, STUN_METHOD_ALLOCATE);
        failures++;
    }

    /* ── 测试 3: 消息长度解析 ── */
    size_t msg_len = 0;
    int ret = stun_get_message_len_str(buf, len, 0, &msg_len);
    if (ret < 0 || msg_len != len) {
        fprintf(stderr, "FAIL: message length mismatch: parsed=%zu, actual=%zu, ret=%d\n",
                msg_len, len, ret);
        failures++;
    }

    /* ── 测试 4: 验证 BINDING 与 ALLOCATE 方法不同 ── */
    uint8_t bind_buf[BUF_SIZE];
    size_t bind_len = 0;
    stun_init_request_str(STUN_METHOD_BINDING, bind_buf, &bind_len);

    uint16_t bind_method = stun_get_method_str(bind_buf, bind_len);
    uint16_t alloc_method = stun_get_method_str(buf, len);
    if (bind_method == alloc_method) {
        fprintf(stderr, "FAIL: BINDING and ALLOCATE have same method value %u\n", bind_method);
        failures++;
    }

    if (failures > 0) {
        fprintf(stderr, "coturn 4.5.2 test: %d failure(s)\n", failures);
        return 1;
    }

    printf("coturn 4.5.2 test: STUN message API verified OK\n");
    printf("  - BINDING request: method=%u, len=%zu\n", bind_method, bind_len);
    printf("  - ALLOCATE request: method=%u, len=%zu\n", alloc_method, len);
    printf("  - Message length parsing: OK\n");
    return 0;
}
