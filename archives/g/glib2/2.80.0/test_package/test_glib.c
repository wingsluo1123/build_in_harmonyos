#include <glib.h>
#include <glib-object.h>
#include <stdio.h>

int main(void) {
    GHashTable *table = NULL;
    GVariant *variant = NULL;
    GObject *object = NULL;
    gchar *text = g_strdup("hello glib");
    int result = 1;

    if (!g_str_has_prefix(text, "hello")) {
        fprintf(stderr, "FAIL: g_str_has_prefix\n");
        goto cleanup;
    }
    table = g_hash_table_new_full(g_str_hash, g_str_equal, g_free, g_free);
    g_hash_table_insert(table, g_strdup("key"), g_strdup("value"));
    if (g_hash_table_size(table) != 1) {
        fprintf(stderr, "FAIL: g_hash_table_size\n");
        goto cleanup;
    }
    variant = g_variant_ref_sink(g_variant_new_int32(42));
    if (g_variant_get_int32(variant) != 42) {
        fprintf(stderr, "FAIL: g_variant_get_int32\n");
        goto cleanup;
    }
    object = g_object_new(G_TYPE_OBJECT, NULL);
    if (!G_IS_OBJECT(object)) {
        fprintf(stderr, "FAIL: g_object_new / G_IS_OBJECT\n");
        goto cleanup;
    }
    printf("PASS: glib2 2.80.0 string/hash-table/GVariant/GObject consumer test\n");
    result = 0;

cleanup:
    if (object != NULL) g_object_unref(object);
    if (variant != NULL) g_variant_unref(variant);
    if (table != NULL) g_hash_table_unref(table);
    g_free(text);
    return result;
}
