#include <stdio.h>
#include <libwapcaplet/libwapcaplet.h>

int main(void) {
    lwc_string *str1 = NULL, *str2 = NULL, *str3 = NULL, *sub = NULL, *upper = NULL;
    bool result;
    int pass = 0, fail = 0;

    /* Test 1: Intern a string */
    if (lwc_intern_string("hello", 5, &str1) == lwc_error_ok) {
        pass++;
    } else {
        fail++;
    }

    /* Test 2: Interning same string returns same pointer */
    lwc_intern_string("hello", 5, &str2);
    if (str1 == str2) {
        pass++;
    } else {
        fail++;
    }

    /* Test 3: Different string returns different pointer */
    lwc_intern_string("world", 5, &str3);
    if (str1 != str3) {
        pass++;
    } else {
        fail++;
    }

    /* Test 4: Equality check */
    lwc_string_isequal(str1, str2, &result);
    if (result) {
        pass++;
    } else {
        fail++;
    }

    /* Test 5: Inequality check */
    lwc_string_isequal(str1, str3, &result);
    if (!result) {
        pass++;
    } else {
        fail++;
    }

    /* Test 6: Caseless comparison */
    lwc_intern_string("HELLO", 5, &upper);
    lwc_string_caseless_isequal(str1, upper, &result);
    if (result) {
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
