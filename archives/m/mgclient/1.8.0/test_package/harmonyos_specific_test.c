/* harmonyos_specific_test.c — mgclient 1.8.0 鸿蒙特有测试
 *
 * 验证 mgclient 库在 HarmonyOS PC (aarch64) 平台上的真实行为：
 * 1. 库加载与版本 API：mg_client_version() 返回 1.8.0，证明共享库符号
 *    解析与动态加载在 OHOS 上正常。
 * 2. 值类型编解码往返：mg_value_make_integer/bool/string 构造与读取在
 *    OHOS 上可用（Bolt 协议编码/解码的基础）。
 * 3. TCP 连接失败错误路径：mg_connect 到本机未监听端口应优雅返回错误
 *    （而非崩溃/挂死），验证 OHOS TCP 栈错误路径与库的错误传播正确。
 *
 * 编译: clang -std=c11 -I<prefix>/include harmonyos_specific_test.c \
 *       -L<prefix>/lib -lmgclient -o harmonyos_specific_test
 * 运行: LD_LIBRARY_PATH=<prefix>/lib ./harmonyos_specific_test <host> <port>
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <mgclient.h>

static int failures = 0;

static void check(int cond, const char *what) {
    if (cond) {
        printf("  PASS: %s\n", what);
    } else {
        printf("  FAIL: %s\n", what);
        failures++;
    }
}

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: %s <host> <port>\n", argv[0]);
        return 2;
    }
    const char *host = argv[1];
    int port = atoi(argv[2]);

    printf("harmonyos_specific_test: mgclient %s on OHOS\n", mg_client_version());

    /* 1. 版本 API */
    check(strcmp(mg_client_version(), "1.8.0") == 0,
          "mg_client_version() == 1.8.0");

    /* 2. 值编解码往返 */
    mg_value *iv = mg_value_make_integer(123456789);
    check(iv != NULL && mg_value_get_type(iv) == MG_VALUE_TYPE_INTEGER &&
              mg_value_integer(iv) == 123456789,
          "integer value round-trip");
    mg_value_destroy(iv);

    mg_value *sv = mg_value_make_string("ohos-bolt-value");
    {
        const char *expect = "ohos-bolt-value";
        const mg_string *str = (sv != NULL && mg_value_get_type(sv) == MG_VALUE_TYPE_STRING)
                                   ? mg_value_string(sv) : NULL;
        check(sv != NULL && str != NULL &&
                  mg_string_size(str) == strlen(expect) &&
                  memcmp(mg_string_data(str), expect, mg_string_size(str)) == 0,
              "string value round-trip");
    }
    mg_value_destroy(sv);

    mg_value *bv = mg_value_make_bool(1);
    check(bv != NULL && mg_value_bool(bv) == 1, "bool value round-trip");
    mg_value_destroy(bv);

    /* 3. TCP 连接失败错误路径（目标端口通常无服务监听） */
    mg_session_params *params = mg_session_params_make();
    mg_session_params_set_host(params, host);
    mg_session_params_set_port(params, port);
    mg_session_params_set_username(params, "test");
    mg_session_params_set_password(params, "test");
    mg_session_params_set_sslmode(params, MG_SSLMODE_DISABLE);

    mg_session *session = NULL;
    int rc = mg_connect(params, &session);
    check(rc != 0, "mg_connect to closed port returns error (no crash)");
    if (rc == 0 && session != NULL) {
        mg_session_destroy(session);
    }
    mg_session_params_destroy(params);

    if (failures == 0) {
        printf("harmonyos_specific_test: ALL OK\n");
        return 0;
    }
    printf("harmonyos_specific_test: %d failure(s)\n", failures);
    return 1;
}