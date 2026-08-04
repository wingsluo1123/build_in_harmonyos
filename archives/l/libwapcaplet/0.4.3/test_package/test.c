#include <stdio.h>
#include <libwapcaplet/libwapcaplet.h>

int main(void) {
    lwc_string *str1 = NULL, *str2 = NULL, *str3 = NULL, *sub = NULL, *upper = NULL;
    bool result = false;
    int pass = 0, fail = 0;

    /* Test 1: Intern a string */
    if (lwc_intern_string("hello", 5, &str1) == lwc_error_ok) {
        pass++;
    } else {
        fail++;
    }

    /* Test 2: Interning same string returns same pointer */
    if (lwc_intern_string("hello", 5, &str2) != lwc_error_ok) {
        fail++;
    } else if (str1 == str2) {
        pass++;
    } else {
        fail++;
    }

    /* Test 3: Different string returns different pointer */
    if (lwc_intern_string("world", 5, &str3) != lwc_error_ok) {
        fail++;
    } else if (str1 != str3) {
        pass++;
    } else {
        fail++;
    }

    /* Test 4: Equality check */
    if (lwc_string_isequal(str1, str2, &result) == lwc_error_ok && result) {
        pass++;
    } else {
        fail++;
    }

    /* Test 5: Inequality check */
    if (lwc_string_isequal(str1, str3, &result) == lwc_error_ok && !result) {
        pass++;
    } else {
        fail++;
    }

    /* Test 6: Caseless comparison */
    if (lwc_intern_string("HELLO", 5, &upper) != lwc_error_ok) {
        fail++;
    } else if (lwc_string_caseless_isequal(str1, upper, &result) == lwc_error_ok && result) {
        pass++;
    } else {
        fail++;
    }

    /* Test 7: Substring */
    if (lwc_intern_substring(str1, 1, 3, &sub) == lwc_error_ok) {
        if (lwc_string_length(sub) == 3) {
            pass++;
        } else {
            fail++;
        }
    } else {
        fail++;
    }

    /* Cleanup: release all interned strings */
cleanup:
    if (sub) lwc_string_unref(sub);
    if (upper) lwc_string_unref(upper);
    if (str3) lwc_string_unref(str3);
    if (str2) lwc_string_unref(str2);
    if (str1) lwc_string_unref(str1);

    if (fail > 0) {
        printf("FAIL: %d tests failed\n", fail);
        return 1;
    }
    printf("All %d tests passed\n", pass);
    return 0;
}
