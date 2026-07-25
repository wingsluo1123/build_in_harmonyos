/*
 * glib smoke test: GObject 类型系统 + GIO 文件操作 + GNetworkMonitor（netlink 关闭验证）
 *
 * 验证项:
 * 1. g_ascii_strup — libglib-2.0.a 字符串转换
 * 2. GHashTable 插入/查询 — libglib-2.0.a 数据结构
 * 3. g_object_new / g_type_from_name — libgobject-2.0.a 链接 + 类型系统初始化
 * 4. g_file_new_for_path — libgio-2.0.a 链接 + GFile 创建
 * 5. g_network_monitor_get_default — netlink 关闭后 GNetworkMonitor 仍可正常创建
 */

#include <glib.h>
#include <glib-object.h>
#include <gio/gio.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

static void test_glib_core(void) {
    /* 断言1: g_ascii_strup 字符串转换 */
    g_autofree gchar *upper = g_ascii_strup("harmonyos", -1);
    if (strcmp(upper, "HARMONYOS") != 0) {
        fprintf(stderr, "FAIL: g_ascii_strup expected HARMONYOS, got %s\n", upper);
        exit(1);
    }
    g_print("PASS: g_ascii_strup(\"harmonyos\") = \"%s\"\n", upper);

    /* 断言2: GHashTable 插入/查询 */
    g_autoptr(GHashTable) table = g_hash_table_new(g_str_hash, g_str_equal);
    g_hash_table_insert(table, "glib", "2.84.0");
    if (strcmp(g_hash_table_lookup(table, "glib"), "2.84.0") != 0) {
        fprintf(stderr, "FAIL: GHashTable lookup failed\n");
        exit(2);
    }
    g_print("PASS: GHashTable insert+lookup\n");
}

static void test_gobject_type_system(void) {
    /* 初始化 GObject 类型系统 */
    g_type_init();

    /* 断言3: g_type_from_name / g_object_new */
    GType t = g_type_from_name("GObject");
    if (t == 0) {
        fprintf(stderr, "FAIL: g_type_from_name(\"GObject\") returned 0\n");
        exit(3);
    }
    g_print("PASS: g_type_from_name(\"GObject\") = %lu\n", (unsigned long)t);

    GObject *obj = g_object_new(G_TYPE_OBJECT, NULL);
    if (obj == NULL) {
        fprintf(stderr, "FAIL: g_object_new(G_TYPE_OBJECT) returned NULL\n");
        exit(3);
    }
    g_print("PASS: g_object_new(G_TYPE_OBJECT) succeeded\n");
    g_object_unref(obj);
}

static void test_gio_file(void) {
    /* 断言4: g_file_new_for_path */
    GFile *file = g_file_new_for_path("/tmp/glib-smoke-test");
    if (file == NULL) {
        fprintf(stderr, "FAIL: g_file_new_for_path returned NULL\n");
        exit(4);
    }
    gchar *basename = g_file_get_basename(file);
    g_print("PASS: g_file_new_for_path -> basename = %s\n", basename);
    g_free(basename);
    g_object_unref(file);
}

static void test_gnetwork_monitor(void) {
    /*
     * 断言5: 验证 netlink 关闭补丁的副作用：
     * 即使 HAVE_NETLINK 被禁用，GNetworkMonitor 仍应可正常创建。
     * 补丁仅注释了 gnetworkmonitornetlink.c 的编译，
     * GNetworkMonitorBase 作为默认实现应仍然可用。
     */
    GNetworkMonitor *monitor = g_network_monitor_get_default();
    if (monitor == NULL) {
        fprintf(stderr, "FAIL: g_network_monitor_get_default returned NULL\n");
        exit(5);
    }
    if (!G_IS_NETWORK_MONITOR(monitor)) {
        fprintf(stderr, "FAIL: monitor is not a GNetworkMonitor\n");
        exit(5);
    }
    gboolean available = g_network_monitor_get_network_available(monitor);
    g_print("PASS: GNetworkMonitor created, network_available = %s\n", available ? "true" : "false");
}

int main(void) {
    g_print("=== glib smoke test: core + GObject + GIO + GNetworkMonitor ===\n");

    test_glib_core();
    test_gobject_type_system();
    test_gio_file();
    test_gnetwork_monitor();

    g_print("=== all 5 assertions passed ===\n");
    return 0;
}
