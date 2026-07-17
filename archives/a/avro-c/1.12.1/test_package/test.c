/* test_package/test.c — Consumer-side test for avro-c 1.12.1 (R34 compliant)
 *
 * Exercises the avro C API: creates a schema, encodes/decodes data,
 * verifies round-trip integrity.
 */
#include <avro.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int main(void) {
    avro_set_error_callback(NULL, NULL);

    /* 1. Parse a schema */
    const char *schema_json =
        "{\"type\":\"record\",\"name\":\"test\","
        "\"fields\":["
        "{\"name\":\"name\",\"type\":\"string\"},"
        "{\"name\":\"age\",\"type\":\"int\"}"
        "]}";

    avro_schema_t schema;
    if (avro_schema_from_json_literal(schema_json, &schema) != 0) {
        fprintf(stderr, "FAIL: avro_schema_from_json_literal: %s\n", avro_strerror());
        return 1;
    }

    /* 2. Create a record value */
    avro_value_iface_t *iface = avro_generic_class_from_schema(schema);
    if (!iface) {
        fprintf(stderr, "FAIL: avro_generic_class_from_schema: %s\n", avro_strerror());
        avro_schema_decref(schema);
        return 1;
    }

    avro_value_t record;
    if (avro_generic_value_new(iface, &record) != 0) {
        fprintf(stderr, "FAIL: avro_generic_value_new: %s\n", avro_strerror());
        avro_value_iface_decref(iface);
        avro_schema_decref(schema);
        return 1;
    }

    /* 3. Set field values */
    avro_value_t name_val;

    if (avro_value_get_by_name(&record, "name", &name_val, NULL) != 0) {
        fprintf(stderr, "FAIL: get field 'name': %s\n", avro_strerror());
        avro_generic_value_free(iface, &record);
        avro_value_iface_decref(iface);
        avro_schema_decref(schema);
        return 1;
    }

    if (avro_value_set_string(&name_val, "jansson-test") != 0) {
        fprintf(stderr, "FAIL: set field 'name': %s\n", avro_strerror());
        avro_generic_value_free(iface, &record);
        avro_value_iface_decref(iface);
        avro_schema_decref(schema);
        return 1;
    }

    avro_value_t age_val;
    if (avro_value_get_by_name(&record, "age", &age_val, NULL) != 0) {
        fprintf(stderr, "FAIL: get field 'age': %s\n", avro_strerror());
        avro_generic_value_free(iface, &record);
        avro_value_iface_decref(iface);
        avro_schema_decref(schema);
        return 1;
    }
    if (avro_value_set_int(&age_val, 42) != 0) {
        fprintf(stderr, "FAIL: set field 'age': %s\n", avro_strerror());
        avro_generic_value_free(iface, &record);
        avro_value_iface_decref(iface);
        avro_schema_decref(schema);
        return 1;
    }

    /* 4. Serialize to memory */
    avro_writer_t writer = avro_memory_writer(NULL, 0);
    if (!writer) {
        fprintf(stderr, "FAIL: avro_memory_writer: %s\n", avro_strerror());
        avro_generic_value_free(iface, &record);
        avro_value_iface_decref(iface);
        avro_schema_decref(schema);
        return 1;
    }

    if (avro_value_write(writer, &record) != 0) {
        fprintf(stderr, "FAIL: avro_value_write: %s\n", avro_strerror());
        avro_writer_free(writer);
        avro_generic_value_free(iface, &record);
        avro_value_iface_decref(iface);
        avro_schema_decref(schema);
        return 1;
    }

    /* 5. Read back and verify */
    void *data;
    int64_t data_len;
    avro_memory_writer_get_buf(writer, &data, &data_len);

    avro_reader_t reader = avro_memory_reader(data, data_len);
    if (!reader) {
        fprintf(stderr, "FAIL: avro_memory_reader: %s\n", avro_strerror());
        avro_writer_free(writer);
        avro_generic_value_free(iface, &record);
        avro_value_iface_decref(iface);
        avro_schema_decref(schema);
        return 1;
    }

    avro_value_t record2;
    if (avro_generic_value_new(iface, &record2) != 0) {
        fprintf(stderr, "FAIL: avro_generic_value_new (record2): %s\n", avro_strerror());
        avro_reader_free(reader);
        avro_writer_free(writer);
        avro_generic_value_free(iface, &record);
        avro_value_iface_decref(iface);
        avro_schema_decref(schema);
        return 1;
    }
    if (avro_value_read(reader, &record2) != 0) {
        fprintf(stderr, "FAIL: avro_value_read: %s\n", avro_strerror());
        avro_reader_free(reader);
        avro_generic_value_free(iface, &record2);
        avro_generic_value_free(iface, &record);
        avro_value_iface_decref(iface);
        avro_schema_decref(schema);
        avro_writer_free(writer);
        return 1;
    }

    /* 6. Verify field values */
    int32_t age_out = 0;
    if (avro_value_get_by_name(&record2, "age", &age_val, NULL) != 0) {
        fprintf(stderr, "FAIL: get field 'age' from record2: %s\n", avro_strerror());
        avro_reader_free(reader);
        avro_generic_value_free(iface, &record2);
        avro_generic_value_free(iface, &record);
        avro_value_iface_decref(iface);
        avro_schema_decref(schema);
        avro_writer_free(writer);
        return 1;
    }
    if (avro_value_get_int(&age_val, &age_out) != 0) {
        fprintf(stderr, "FAIL: get int from age_val: %s\n", avro_strerror());
        avro_reader_free(reader);
        avro_generic_value_free(iface, &record2);
        avro_generic_value_free(iface, &record);
        avro_value_iface_decref(iface);
        avro_schema_decref(schema);
        avro_writer_free(writer);
        return 1;
    }

    const char *name_out = NULL;
    size_t name_len = 0;
    if (avro_value_get_by_name(&record2, "name", &name_val, NULL) != 0) {
        fprintf(stderr, "FAIL: get field 'name' from record2: %s\n", avro_strerror());
        avro_reader_free(reader);
        avro_generic_value_free(iface, &record2);
        avro_generic_value_free(iface, &record);
        avro_value_iface_decref(iface);
        avro_schema_decref(schema);
        avro_writer_free(writer);
        return 1;
    }
    if (avro_value_get_string(&name_val, &name_out, &name_len) != 0) {
        fprintf(stderr, "FAIL: get string from name_val: %s\n", avro_strerror());
        avro_reader_free(reader);
        avro_generic_value_free(iface, &record2);
        avro_generic_value_free(iface, &record);
        avro_value_iface_decref(iface);
        avro_schema_decref(schema);
        avro_writer_free(writer);
        return 1;
    }

    if (age_out != 42) {
        fprintf(stderr, "FAIL: age mismatch (got %d, expected 42)\n", age_out);
        avro_reader_free(reader);
        avro_generic_value_free(iface, &record2);
        avro_generic_value_free(iface, &record);
        avro_value_iface_decref(iface);
        avro_schema_decref(schema);
        avro_writer_free(writer);
        return 1;
    }

    if (strncmp(name_out, "jansson-test", 12) != 0) {
        fprintf(stderr, "FAIL: name mismatch (got %.*s, expected 'jansson-test')\n", (int)name_len, name_out);
        avro_reader_free(reader);
        avro_generic_value_free(iface, &record2);
        avro_generic_value_free(iface, &record);
        avro_value_iface_decref(iface);
        avro_schema_decref(schema);
        avro_writer_free(writer);
        return 1;
    }

    printf("test avro-c 1.12.1: OK (schema + record + serialize + deserialize verified)\n");

    avro_reader_free(reader);
    avro_generic_value_free(iface, &record2);
    avro_generic_value_free(iface, &record);
    avro_value_iface_decref(iface);
    avro_schema_decref(schema);
    avro_writer_free(writer);
    return 0;
}
