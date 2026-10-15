#include <stdio.h>
#include <string.h>
#include <inttypes.h>

#include <mgclient.h>

/* 真实调用 mgclient API：版本、值构造/读取、字符串编解码往返。 */
static int run_checks(void) {
    int failures = 0;

    const char *version = mg_client_version();
    if (version == NULL || strcmp(version, "1.8.0") != 0) {
        fprintf(stderr, "FAIL: mg_client_version() = %s, expected 1.8.0\n",
                version ? version : "(null)");
        failures++;
    } else {
        printf("OK: mg_client_version() = %s\n", version);
    }

    /* 构造整数值并读回 */
    mg_value *v = mg_value_make_integer(42);
    if (v == NULL || mg_value_get_type(v) != MG_VALUE_TYPE_INTEGER ||
        mg_value_integer(v) != 42) {
        fprintf(stderr, "FAIL: integer value round-trip\n");
        failures++;
    } else {
        printf("OK: mg_value integer round-trip = %" PRId64 "\n",
               mg_value_integer(v));
    }
    mg_value_destroy(v);

    /* 构造字符串并读回（mg_string 为长度定界缓冲，用 size 定界比较） */
    mg_value *s = mg_value_make_string("ohos-mgclient-test");
    if (s == NULL || mg_value_get_type(s) != MG_VALUE_TYPE_STRING) {
        fprintf(stderr, "FAIL: string value creation\n");
        failures++;
    } else {
        const mg_string *str = mg_value_string(s);
        const char *expect = "ohos-mgclient-test";
        if (str == NULL || mg_string_size(str) != strlen(expect) ||
            memcmp(mg_string_data(str), expect, mg_string_size(str)) != 0) {
            fprintf(stderr, "FAIL: string value content\n");
            failures++;
        } else {
            printf("OK: mg_value string round-trip = '%s' (len=%u)\n",
                   mg_string_data(str), mg_string_size(str));
        }
    }
    mg_value_destroy(s);

    /* 构造 bool 并读回 */
    mg_value *b = mg_value_make_bool(1);
    if (b == NULL || mg_value_bool(b) != 1) {
        fprintf(stderr, "FAIL: bool value round-trip\n");
        failures++;
    } else {
        printf("OK: mg_value bool round-trip = %d\n", mg_value_bool(b));
    }
    mg_value_destroy(b);

    return failures;
}

int main(void) {
    printf("mgclient consumer test (libmgclient %s)\n", mg_client_version());
    int rc = run_checks();
    if (rc == 0) {
        printf("mgclient test_package: ALL OK\n");
        return 0;
    }
    fprintf(stderr, "mgclient test_package: %d failure(s)\n", rc);
    return 1;
}