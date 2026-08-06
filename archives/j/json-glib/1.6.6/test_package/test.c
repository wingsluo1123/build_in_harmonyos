#include <json-glib/json-glib.h>
#include <stdio.h>

int main(void) {
    /* Parse a simple JSON string using json-glib API */
    GError *error = NULL;
    JsonParser *parser = json_parser_new();

    const char *json_str = "{\"name\":\"test\",\"value\":42}";
    gboolean ok = json_parser_load_from_data(parser, json_str, -1, &error);
    if (!ok) {
        fprintf(stderr, "Failed to parse JSON: %s\n", error ? error->message : "unknown");
        g_clear_error(&error);
        g_object_unref(parser);
        return 1;
    }

    JsonNode *root = json_parser_get_root(parser);
    JsonObject *obj = json_node_get_object(root);
    const gchar *name = json_object_get_string_member(obj, "name");
    gint value = json_object_get_int_member(obj, "value");

    if (g_strcmp0(name, "test") != 0 || value != 42) {
        fprintf(stderr, "Unexpected values: name=%s value=%d\n", name, value);
        g_object_unref(parser);
        return 1;
    }

    printf("json-glib test passed: name=%s, value=%d\n", name, value);

    g_object_unref(parser);
    return 0;
}
