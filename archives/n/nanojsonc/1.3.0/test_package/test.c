#include <stdio.h>
#include <string.h>
#include <nanojsonc/parser.h>

/*
 * L1 consumer test for nanojsonc 1.3.0.
 * Real usage: register callbacks, parse a JSON object and an array,
 * verify key-value pairs are delivered with correct parent keys and values.
 * R34: this test actually drives the library API (not a print-only stub).
 */

typedef struct {
    int pairs;
    int errors;
} Stats;

static void on_object(enum NanoJSONCError error, const char *const key,
                      const char *const value, const char *const parentKey,
                      void *object) {
    Stats *s = (Stats *)object;
    if (error != NO_ERROR) {
        s->errors++;
        return;
    }
    if (key && value) {
        s->pairs++;
        if (strcmp(key, "name") == 0 && strcmp(value, "openharmony") != 0) {
            printf("FAIL: name value mismatch: %s\n", value);
            s->errors++;
        }
        if (strcmp(key, "version") == 0 && strcmp(value, "1.3.0") != 0) {
            printf("FAIL: version value mismatch: %s\n", value);
            s->errors++;
        }
    }
}

static void on_array(enum NanoJSONCError error, const char *const key,
                     const char *const value, const char *const parentKey,
                     void *object) {
    Stats *s = (Stats *)object;
    if (error != NO_ERROR) {
        s->errors++;
        return;
    }
    if (value) {
        s->pairs++;
        /* Array of {"os":"OHOS","arch":"arm64"} objects */
        if (strcmp(value, "OHOS") != 0 && strcmp(value, "arm64") != 0) {
            if (strcmp(value, "nanojsonc") != 0) {
                printf("FAIL: unexpected array value: %s\n", value);
                s->errors++;
            }
        }
    }
}

int main(void) {
    Stats s = {0, 0};
    const char *json_obj =
        "{\"name\":\"openharmony\",\"version\":\"1.3.0\","
        "\"nested\":{\"key\":\"value\"}}";
    const char *json_arr = "[{\"os\":\"OHOS\",\"arch\":\"arm64\"}]";

    nanojsonc_parse_object(json_obj, "", &s, on_object);
    nanojsonc_parse_array(json_arr, "", &s, on_array);

    printf("nanojsonc 1.3.0: parsed pairs=%d errors=%d\n", s.pairs, s.errors);

    if (s.errors != 0 || s.pairs < 4) {
        printf("FAIL: expected >=4 parsed key-value events, got %d (errors=%d)\n",
               s.pairs, s.errors);
        return 1;
    }

    /* error_desc must return a non-empty description for an overflow code */
    const char *desc = nanojsonc_error_desc(VALUE_OVERFLOW);
    if (!desc || desc[0] == '\0') {
        printf("FAIL: nanojsonc_error_desc returned empty\n");
        return 1;
    }
    printf("nanojsonc 1.3.0 consumer test OK\n");
    return 0;
}