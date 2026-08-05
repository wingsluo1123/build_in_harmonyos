#include <avro.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* Create a simple string schema */
    avro_schema_t schema;
    if (avro_schema_from_json_literal("\"string\"", &schema) != 0) {
        fprintf(stderr, "Failed to parse schema: %s\n", avro_strerror());
        return 1;
    }

    /* Create a datum from the schema */
    avro_value_iface_t *iface = avro_generic_class_from_schema(schema);
    if (iface == NULL) {
        fprintf(stderr, "Failed to create value interface: %s\n", avro_strerror());
        return 1;
    }

    avro_value_t value;
    if (avro_generic_value_new(iface, &value) != 0) {
        fprintf(stderr, "Failed to create value: %s\n", avro_strerror());
        return 1;
    }

    /* Set the string value */
    const char *test_str = "Hello, Avro!";
    if (avro_value_set_string(&value, test_str) != 0) {
        fprintf(stderr, "Failed to set string: %s\n", avro_strerror());
        return 1;
    }

    /* Read it back */
    const char *read_str = NULL;
    size_t str_len = 0;
    if (avro_value_get_string(&value, &read_str, &str_len) != 0) {
        fprintf(stderr, "Failed to get string: %s\n", avro_strerror());
        return 1;
    }

    printf("Schema: string\n");
    printf("Written: %s\n", test_str);
    printf("Read:    %s (len=%zu)\n", read_str, str_len);

    /* Verify round-trip */
    int result = (strcmp(test_str, read_str) == 0) ? 0 : 1;

    /* Clean up */
    avro_value_decref(&value);
    avro_value_iface_decref(iface);
    avro_schema_decref(schema);

    if (result == 0) {
        printf("PASS: Avro string round-trip successful\n");
    } else {
        printf("FAIL: String mismatch\n");
    }
    return result;
}
