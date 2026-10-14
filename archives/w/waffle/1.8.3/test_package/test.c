/*
 * test_waffle.c — waffle 1.8.3 消费者真实调用测试
 *
 * 直接调用 waffle 公共 API，验证头文件包含、符号链接与核心库可运行性：
 *   - waffle_error_to_string / waffle_enum_to_string（字符串化）
 *   - waffle_attrib_list_length / get / get_with_default / update（属性列表核心逻辑）
 *
 * 说明：OHOS 适配构建末尾端 (GLX/Wayland/GBM/X11-EGL) 均禁用（HarmonyOS PC
 * 无对应窗口/图形子系统），故本测试不创建 GL context/display，专注验证与平台
 * 无关、始终生效的核心 API。
 *
 * 退出码 0 = 全部断言通过；非 0 = 失败。
 */
#include <stdio.h>
#include <string.h>

#include <waffle-1/waffle.h>

static int failures = 0;

#define CHECK(cond, msg)                                    \
    do {                                                    \
        if (!(cond)) {                                      \
            printf("FAIL: %s\n", (msg));                    \
            failures++;                                     \
        } else {                                            \
            printf("PASS: %s\n", (msg));                    \
        }                                                   \
    } while (0)

int main(void)
{
    /* 1-2. waffle_error_to_string 返回枚举名字符串 */
    CHECK(strcmp(waffle_error_to_string(WAFFLE_NO_ERROR), "WAFFLE_NO_ERROR") == 0,
          "waffle_error_to_string(WAFFLE_NO_ERROR) == \"WAFFLE_NO_ERROR\"");
    CHECK(strcmp(waffle_error_to_string(WAFFLE_ERROR_BAD_PARAMETER),
                 "WAFFLE_ERROR_BAD_PARAMETER") == 0,
          "waffle_error_to_string(BAD_PARAMETER) == \"WAFFLE_ERROR_BAD_PARAMETER\"");

    /* 3-4. waffle_enum_to_string 返回枚举名字符串 */
    CHECK(strcmp(waffle_enum_to_string(WAFFLE_DONT_CARE), "WAFFLE_DONT_CARE") == 0,
          "waffle_enum_to_string(WAFFLE_DONT_CARE) == \"WAFFLE_DONT_CARE\"");
    CHECK(strcmp(waffle_enum_to_string(WAFFLE_NONE), "WAFFLE_NONE") == 0,
          "waffle_enum_to_string(WAFFLE_NONE) == \"WAFFLE_NONE\"");

    /* 5. NULL 属性列表长度为 0 */
    CHECK(waffle_attrib_list_length(NULL) == 0,
          "waffle_attrib_list_length(NULL) == 0");

    /*
     * 属性列表：{WAFFLE_PLATFORM=0x1234, WAFFLE_CONTEXT_MAJOR_VERSION=0x5678,
     * 终止 0}。
     * 注意：不能用 WAFFLE_NONE 当第二个 value——WAFFLE_NONE==0 即属性列表的
     * 终止符（waffle_attrib_list_{length,get,get_with_default,update} 都以
     * 0 结尾），若放进 value 位置列表会在 index 2 提前终止，length 变成 1
     * 而非 2。这里改用非零的 WAFFLE_CONTEXT_MAJOR_VERSION 作第二个 key，
     * 使两对 key/value 均为非零，列表能完整走到末尾终止符。
     */
    int32_t list[] = {
        WAFFLE_PLATFORM, 0x1234,
        WAFFLE_CONTEXT_MAJOR_VERSION, 0x5678,
        0
    };

    /* 6. 长度为 2（两对 key/value） */
    CHECK(waffle_attrib_list_length(list) == 2,
          "waffle_attrib_list_length(2-pair list) == 2");

    /* 7. 读取存在的 key */
    int32_t v = 0;
    CHECK(waffle_attrib_list_get(list, WAFFLE_PLATFORM, &v) && v == 0x1234,
          "waffle_attrib_list_get(WAFFLE_PLATFORM) == 0x1234");

    /* 8. get_with_default 缺失 key 返回 false 且填 default */
    v = 0;
    CHECK(!waffle_attrib_list_get_with_default(list, 0x9999, &v, 42) && v == 42,
          "get_with_default(missing, default=42) -> false, v==42");

    /* 9. update 存在的 key 成功且生效 */
    CHECK(waffle_attrib_list_update(list, WAFFLE_PLATFORM, 0xABCD),
          "waffle_attrib_list_update(existing key) returns true");
    v = 0;
    CHECK(waffle_attrib_list_get(list, WAFFLE_PLATFORM, &v) && v == 0xABCD,
          "after update, WAFFLE_PLATFORM == 0xABCD");

    /* 10. update 不存在的 key 返回 false */
    CHECK(!waffle_attrib_list_update(list, 0x9999, 7),
          "waffle_attrib_list_update(missing key) returns false");

    if (failures == 0) {
        printf("ALL TESTS PASSED\n");
        return 0;
    }
    printf("%d TEST(S) FAILED\n", failures);
    return 1;
}
