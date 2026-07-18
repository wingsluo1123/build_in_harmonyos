/*
 * test_arrow_glib.c — Conan L1 测试
 *
 * 验证 apache-arrow-glib 库可以被正确链接和运行时调用：
 *   1. 创建 GArrowBooleanArrayBuilder（运行时对象）
 *   2. 验证 GObject 类型系统正确识别该对象
 *   3. 清理资源
 *
 * R34: 本测试必须调用被测包的运行时 API，禁止空壳测试。
 */
#include <glib.h>
#include <arrow-glib/arrow-glib.h>

int main(void)
{
    /* 运行时 API 调用：创建 BooleanArrayBuilder */
    GArrowBooleanArrayBuilder *builder = garrow_boolean_array_builder_new();

    /* 验证对象创建成功且类型正确 */
    if (!builder) {
        g_print("FAIL: garrow_boolean_array_builder_new() returned NULL\n");
        return 1;
    }
    if (!GARROW_IS_ARRAY_BUILDER(builder)) {
        g_print("FAIL: object is not a GArrowArrayBuilder\n");
        g_object_unref(builder);
        return 2;
    }
    if (!GARROW_IS_BOOLEAN_ARRAY_BUILDER(builder)) {
        g_print("FAIL: object is not a GArrowBooleanArrayBuilder\n");
        g_object_unref(builder);
        return 3;
    }

    g_print("OK: GArrowBooleanArrayBuilder created and type-checked\n");

    /* 清理 */
    g_object_unref(builder);
    return 0;
}
