/* test_package/test.c — json-glib consumer test.
 *
 * Verifies (compile+link) the public header closure and (runtime, when not
 * cross-building) that the shared library loads and a real JSON parse round
 * trip works:
 *   - json_parser_load_from_data on a JSON object literal
 *   - json_object_get_string_member reads back the value
 *   - json_generator_to_data serializes an object built with json_builder
 */
#include <json-glib/json-glib.h>
#include <glib.h>
#include <stdio.h>
#include <string.h>

#ifndef TARGET_SO
#define TARGET_SO "libjson-glib-1.0.so"
#endif

int main(void) {
    /* ---- 1. parse a JSON object and read a member ---- */
    const char *doc = "{ \"name\": \"harmony\", \"version\": 6 }";
    GError *err = NULL;
    JsonParser *parser = json_parser_new();
    if (!json_parser_load_from_data(parser, doc, -1, &err)) {
        fprintf(stderr, "json_parser_load_from_data failed: %s\n",
                err ? err->message : "?");
        g_clear_error(&err);
        g_object_unref(parser);
        return 2;
    }
    JsonNode *root = json_parser_get_root(parser);
    if (json_node_get_node_type(root) != JSON_NODE_OBJECT) {
        fprintf(stderr, "root is not an object\n");
        g_object_unref(parser);
        return 3;
    }
    JsonObject *obj = json_node_get_object(root);
    const gchar *name = json_object_get_string_member(obj, "name");
    if (name == NULL || strcmp(name, "harmony") != 0) {
        fprintf(stderr, "name mismatch: %s\n", name ? name : "(null)");
        g_object_unref(parser);
        return 4;
    }
    gint64 ver = json_object_get_int_member(obj, "version");
    if (ver != 6) {
        fprintf(stderr, "version mismatch: %lld\n", (long long)ver);
        g_object_unref(parser);
        return 5;
    }
    /* Copy the string before releasing the parser (the member points into
     * parser-owned memory that is freed on unref). */
    gchar *name_copy = g_strdup(name);
    g_object_unref(parser);

    /* ---- 2. build an object and serialize it ---- */
    JsonBuilder *b = json_builder_new();
    json_builder_begin_object(b);
    json_builder_set_member_name(b, "ok");
    json_builder_add_boolean_value(b, TRUE);
    json_builder_set_member_name(b, "count");
    json_builder_add_int_value(b, 42);
    json_builder_end_object(b);
    JsonNode *bn = json_builder_get_root(b);
    JsonGenerator *gen = json_generator_new();
    json_generator_set_root(gen, bn);
    gchar *out = json_generator_to_data(gen, NULL);
    if (out == NULL || strstr(out, "\"ok\"") == NULL || strstr(out, "42") == NULL) {
        fprintf(stderr, "generator output unexpected: %s\n", out ? out : "(null)");
        g_free(out);
        g_object_unref(gen);
        json_node_free(bn);
        g_object_unref(b);
        return 6;
    }
    printf("json-glib ok: parsed name=%s ver=%lld; built=%s\n",
           name_copy, (long long)ver, out);
    g_free(out);
    g_free(name_copy);
    g_object_unref(gen);
    json_node_free(bn);
    g_object_unref(b);
    return 0;
}
