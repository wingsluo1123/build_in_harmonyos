/* test_package/test.c — Consumer-side test for jansson 2.15.0 (R34 compliant)
 *
 * This test actually exercises the jansson API: creates a JSON object,
 * adds integer/string members, serializes to string, parses it back,
 * and verifies the values.  If the library is broken or missing, the
 * assertions will fail.
 */
#include <jansson.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int main(void) {
    /* 1. Build a JSON object */
    json_t *root = json_object();
    if (!root) {
        fprintf(stderr, "FAIL: json_object() returned NULL\n");
        return 1;
    }

    /* 2. Add members */
    json_object_set_new(root, "name", json_string("jansson-test"));
    json_object_set_new(root, "version", json_integer(215));
    json_object_set_new(root, "nested", json_pack("{s:s}", "key", "value"));

    /* 3. Serialize */
    char *dump = json_dumps(root, JSON_INDENT(2));
    if (!dump) {
        fprintf(stderr, "FAIL: json_dumps() returned NULL\n");
        json_decref(root);
        return 1;
    }

    /* 4. Parse back and verify */
    json_error_t error;
    json_t *parsed = json_loads(dump, 0, &error);
    if (!parsed) {
        fprintf(stderr, "FAIL: json_loads() error: %s\n", error.text);
        free(dump);
        json_decref(root);
        return 1;
    }

    json_t *name = json_object_get(parsed, "name");
    json_t *ver  = json_object_get(parsed, "version");
    if (!json_is_string(name) || strcmp(json_string_value(name), "jansson-test") != 0) {
        fprintf(stderr, "FAIL: name mismatch\n");
        free(dump);
        json_decref(parsed);
        json_decref(root);
        return 1;
    }
    if (!json_is_integer(ver) || json_integer_value(ver) != 215) {
        fprintf(stderr, "FAIL: version mismatch\n");
        free(dump);
        json_decref(parsed);
        json_decref(root);
        return 1;
    }

    printf("test jansson 2.15.0: OK\n");
    printf("JSON dump:\n%s\n", dump);

    free(dump);
    json_decref(parsed);
    json_decref(root);
    return 0;
}
