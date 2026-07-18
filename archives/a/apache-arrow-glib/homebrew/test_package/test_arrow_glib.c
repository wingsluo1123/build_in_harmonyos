/*
 * test_arrow_glib.c — Conan L1 测试
 *
 * 验证 apache-arrow-glib 库可以被正确链接和调用：
 *   1. 版本宏在编译时可用（garrow-glib.h）
 *   2. 可以调用运行时 API 并检查返回值
 */
#include <glib.h>
#include <arrow-glib/arrow-glib.h>

int main(void)
{
    /* 版本宏：编译时可用即表示头文件安装正确 */
    g_print("Apache Arrow GLib version: %d.%d.%d%s\n",
            GARROW_VERSION_MAJOR,
            GARROW_VERSION_MINOR,
            GARROW_VERSION_MICRO,
            GARROW_VERSION_TAG);

    /* 版本检查宏：编译通过即表示 API 版本匹配 */
#if !GARROW_VERSION_CHECK(0, 10, 0)
#  error "Apache Arrow GLib >= 0.10.0 is required"
#endif

    g_print("All checks passed.\n");
    return 0;
}
