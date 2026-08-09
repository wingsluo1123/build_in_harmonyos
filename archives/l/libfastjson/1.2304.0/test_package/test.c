#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libfastjson/json.h>

int main(void) {
    /* Parse a JSON string */
    struct json_object *obj = json_tokener_parse("{\"key\":\"value\",\"num\":42}");
    if (!obj) {
        fprintf(stderr, "json_tokener_parse failed\n");
        return 1;
    }

    /* Get string value */
    struct json_object *val = json_object_object_get(obj, "key");
    if (!val) {
        fprintf(stderr, "json_object_object_get failed for 'key'\n");
        json_object_put(obj);
        return 1;
    }
    const char *str = json_object_get_string(val);
    if (!str || strcmp(str, "value") != 0) {
        fprintf(stderr, "unexpected string value: %s\n", str ? str : "(null)");
        json_object_put(obj);
        return 1;
    }

    /* Get int value */
    struct json_object *num = json_object_object_get(obj, "num");
    if (!num) {
        fprintf(stderr, "json_object_object_get failed for 'num'\n");
        json_object_put(obj);
        return 1;
    }
    int n = json_object_get_int(num);
    if (n != 42) {
        fprintf(stderr, "unexpected int value: %d\n", n);
        json_object_put(obj);
        return 1;
    }

    /* Create a new JSON object */
    struct json_object *new_obj = json_object_new_object();
    json_object_object_add(new_obj, "name", json_object_new_string("test"));
    const char *json_str = json_object_to_json_string(new_obj);
    if (!json_str) {
        fprintf(stderr, "json_object_to_json_string failed\n");
        json_object_put(obj);
        json_object_put(new_obj);
        return 1;
    }

    printf("libfastjson test: OK (parsed key=%s num=%d, created %s)\n", str, n, json_str);

    json_object_put(obj);
    json_object_put(new_obj);
    return 0;
}
