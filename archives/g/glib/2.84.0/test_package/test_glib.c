#include <glib.h>
#include <string.h>

int main(void) {
    g_autofree gchar *upper = g_ascii_strup("harmonyos", -1);
    g_autoptr(GHashTable) table = g_hash_table_new(g_str_hash, g_str_equal);

    if (strcmp(upper, "HARMONYOS") != 0) {
        return 1;
    }

    g_hash_table_insert(table, "glib", "2.84.0");
    if (strcmp(g_hash_table_lookup(table, "glib"), "2.84.0") != 0) {
        return 2;
    }

    g_print("glib consumer passed\n");
    return 0;
}
