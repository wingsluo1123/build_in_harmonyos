#include <glib.h>
#include <json-glib/json-glib.h>
#include <jsonrpc-glib.h>

int main(void) {
    /* Test server creation */
    JsonrpcServer *server = jsonrpc_server_new();
    g_print("server=%p\n", (void *)server);

    /* Test message serialization */
    JsonNode *node = json_node_new(JSON_NODE_OBJECT);
    JsonObject *obj = json_object_new();
    json_object_set_string_member(obj, "jsonrpc", "2.0");
    json_object_set_int_member(obj, "id", 1);
    json_object_set_string_member(obj, "method", "test");
    json_node_take_object(node, obj);

    gchar *str = json_to_string(node, FALSE);
    g_print("message=%s\n", str);

    g_free(str);
    json_node_free(node);
    g_object_unref(server);
    return 0;
}
