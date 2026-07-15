#include <stdio.h>
#include <string.h>
#include "mpack.h"

int main(void) {
    /* Test 1: pack and unpack a uint value */
    mpack_token_t tok = mpack_pack_uint(42);
    mpack_uintmax_t val = mpack_unpack_uint(tok);
    if (val != 42) {
        printf("FAIL: expected 42, got %llu\n", (unsigned long long)val);
        return 1;
    }

    /* Test 2: pack and unpack a large uint value */
    mpack_token_t tok2 = mpack_pack_uint(0x12345678);
    mpack_uintmax_t val2 = mpack_unpack_uint(tok2);
    if (val2 != 0x12345678) {
        printf("FAIL: expected 0x12345678, got %llu\n", (unsigned long long)val2);
        return 1;
    }

    /* Test 3: pack nil */
    mpack_token_t nil_tok = mpack_pack_nil();
    if (nil_tok.type != MPACK_TOKEN_NIL) {
        printf("FAIL: expected MPACK_TOKEN_NIL\n");
        return 1;
    }

    /* Test 4: pack and unpack boolean true */
    mpack_token_t bool_tok = mpack_pack_boolean(1);
    if (!mpack_unpack_boolean(bool_tok)) {
        printf("FAIL: expected true\n");
        return 1;
    }

    /* Test 5: pack and unpack boolean false */
    mpack_token_t bool_tok2 = mpack_pack_boolean(0);
    if (mpack_unpack_boolean(bool_tok2)) {
        printf("FAIL: expected false\n");
        return 1;
    }

    /* Test 6: pack array */
    mpack_token_t arr_tok = mpack_pack_array(3);
    if (arr_tok.type != MPACK_TOKEN_ARRAY || arr_tok.length != 3) {
        printf("FAIL: expected MPACK_TOKEN_ARRAY with length 3\n");
        return 1;
    }

    /* Test 7: pack map */
    mpack_token_t map_tok = mpack_pack_map(2);
    if (map_tok.type != MPACK_TOKEN_MAP || map_tok.length != 2) {
        printf("FAIL: expected MPACK_TOKEN_MAP with length 2\n");
        return 1;
    }

    printf("All libmpack tests passed\n");
    return 0;
}
