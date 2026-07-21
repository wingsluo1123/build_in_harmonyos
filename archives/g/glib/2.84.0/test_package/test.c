#include <glib.h>
#include <glib-object.h>
#include <stdio.h>

/* R40: glib 是系统底层库，需验证核心功能而非仅 version() */

static void test_glib_basic(void) {
    /* glib string utilities */
    gchar *str = g_strdup("hello");
    g_assert_cmpstr(str, ==, "hello");
    g_free(str);

    /* glib container (GList) */
    GList *list = NULL;
    list = g_list_append(list, "a");
    list = g_list_append(list, "b");
    g_assert_cmpint(g_list_length(list), ==, 2);
    g_assert_cmpstr(list->data, ==, "a");
    g_assert_cmpstr(g_list_last(list)->data, ==, "b");
    g_list_free(list);

    /* glib hash table */
    GHashTable *ht = g_hash_table_new(g_str_hash, g_str_equal);
    g_hash_table_insert(ht, "key1", "val1");
    g_assert_cmpstr(g_hash_table_lookup(ht, "key1"), ==, "val1");
    g_hash_table_destroy(ht);
}

static void test_gobject_type_system(void) {
    /* gobject type system — glib 的核心子系统 */
    g_assert_cmpint(G_TYPE_FUNDAMENTAL(G_TYPE_OBJECT), ==, G_TYPE_OBJECT);
    g_assert_cmpstr(g_type_name(G_TYPE_OBJECT), ==, "GObject");

    /* GObject type instantiation */
    GObject *obj = g_object_new(G_TYPE_OBJECT, NULL);
    g_assert_nonnull(obj);
    g_assert(G_IS_OBJECT(obj));

    /* Reference counting */
    g_object_ref(obj);
    g_assert_cmpint(obj->ref_count, ==, 2);
    g_object_unref(obj);
    g_object_unref(obj);
}

int main(void) {
    /* glib+gobject 核心功能验证 (R40) */
    test_glib_basic();
    test_gobject_type_system();

    printf("glib version: %d.%d.%d\n",
           GLIB_MAJOR_VERSION,
           GLIB_MINOR_VERSION,
           GLIB_MICRO_VERSION);
    printf("glib test: PASS\n");
    return 0;
}
