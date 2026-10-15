/* test_package/test.c — libxfce4util 4.20.1 消费者冒烟（上游无测试套件）
 *
 * 上游 4.20.1 tarball 无 test() 声明、无 tests/ 目录（N=0 审计声明），
 * 本消费者测试覆盖库的核心公开 API 面：
 *   1. 版本宏与 xfce_version_string()
 *   2. xfce_str_replace / xfce_utf8_strndup / xfce_utf8_remove_controls（字符串与 UTF-8）
 *   3. xfce_resource_dirs（资源查找路径非空）
 *   4. xfce_get_license_text（内置许可证文本）
 *   5. xfce_expand_variables（变量展开）
 *   6. XfceKiosk（GObject 派生类型系统 + kiosk 查询）
 */
#include <stdio.h>
#include <string.h>
#include <glib.h>
#include <libxfce4util/libxfce4util.h>

int main(void)
{
    int errors = 0;

    /* 1) 版本字符串 + 版本宏一致性 */
    const gchar *version = xfce_version_string();
    if (version == NULL || strlen(version) == 0) {
        fprintf(stderr, "FAIL: xfce_version_string()\n");
        errors++;
    } else {
        printf("OK: xfce_version_string() = %s\n", version);
    }
    if (libxfce4util_major_version != 4 || libxfce4util_minor_version != 20
        || libxfce4util_micro_version != 1) {
        fprintf(stderr, "FAIL: version macros %d.%d.%d\n",
                libxfce4util_major_version, libxfce4util_minor_version,
                libxfce4util_micro_version);
        errors++;
    } else {
        printf("OK: version macros 4.20.1\n");
    }
    if (!LIBXFCE4UTIL_CHECK_VERSION(4, 20, 1) || LIBXFCE4UTIL_CHECK_VERSION(4, 21, 0)) {
        fprintf(stderr, "FAIL: LIBXFCE4UTIL_CHECK_VERSION\n");
        errors++;
    } else {
        printf("OK: LIBXFCE4UTIL_CHECK_VERSION\n");
    }

    /* 2) 字符串 API */
    gchar *replaced = xfce_str_replace("hello world", "world", "ohos");
    if (replaced == NULL || strcmp(replaced, "hello ohos") != 0) {
        fprintf(stderr, "FAIL: xfce_str_replace -> %s\n", replaced ? replaced : "()");
        errors++;
    } else {
        printf("OK: xfce_str_replace\n");
    }
    g_free(replaced);

    gchar *dup = xfce_utf8_strndup("abc def", 3);
    if (dup == NULL || strcmp(dup, "abc") != 0) {
        fprintf(stderr, "FAIL: xfce_utf8_strndup\n");
        errors++;
    } else {
        printf("OK: xfce_utf8_strndup\n");
    }
    g_free(dup);

    /* "a" + 0x01 控制字符 + "b"（八进制转义避免 \x01b 被当作一个十六进制转义） */
    gchar ctrl[] = "a\001b";
    gchar *cleaned = xfce_utf8_remove_controls(ctrl, -1, NULL);
    if (cleaned == NULL || strcmp(cleaned, "a b") != 0) {
        fprintf(stderr, "FAIL: xfce_utf8_remove_controls\n");
        errors++;
    } else {
        printf("OK: xfce_utf8_remove_controls\n");
    }

    /* 3) 资源查找（DATA 目录列表非空） */
    gchar **dirs = xfce_resource_dirs(XFCE_RESOURCE_DATA);
    if (dirs == NULL || dirs[0] == NULL) {
        fprintf(stderr, "FAIL: xfce_resource_dirs empty\n");
        errors++;
    } else {
        printf("OK: xfce_resource_dirs (%s ...)\n", dirs[0]);
    }
    g_strfreev(dirs);

    /* 4) 内置许可证文本 */
    const gchar *lgpl = xfce_get_license_text(XFCE_LICENSE_TEXT_LGPL);
    if (lgpl == NULL || strstr(lgpl, "GNU") == NULL) {
        fprintf(stderr, "FAIL: xfce_get_license_text(LGPL)\n");
        errors++;
    } else {
        printf("OK: xfce_get_license_text(LGPL)\n");
    }

    /* 5) 变量展开 */
    const gchar *envp[] = { "USER=ohos-test", NULL };
    gchar *expanded = xfce_expand_variables("u=$USER", (gchar **) envp);
    if (expanded == NULL || strcmp(expanded, "u=ohos-test") != 0) {
        fprintf(stderr, "FAIL: xfce_expand_variables -> %s\n", expanded ? expanded : "()");
        errors++;
    } else {
        printf("OK: xfce_expand_variables\n");
    }
    g_free(expanded);

    /* 6) XfceKiosk（GObject 类型系统，g_object_new/unref 走 gobject 链路） */
    XfceKiosk *kiosk = xfce_kiosk_new("libxfce4util-smoke");
    if (kiosk == NULL) {
        fprintf(stderr, "FAIL: xfce_kiosk_new\n");
        errors++;
    } else {
        gboolean allowed = xfce_kiosk_query(kiosk, "SOME_CAPABILITY");
        printf("OK: xfce_kiosk_new + xfce_kiosk_query (=%s)\n",
               allowed ? "TRUE" : "FALSE");
        g_object_unref(kiosk);
    }

    if (errors == 0) {
        printf("PASS: libxfce4util 4.20.1 API smoke test OK\n");
        return 0;
    }
    fprintf(stderr, "FAIL: %d assertion(s) failed\n", errors);
    return 1;
}
