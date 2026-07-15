#include <pg_query.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* Test 1: Parse a simple SQL query */
    PgQueryParseResult parse_result = pg_query_parse("SELECT 1");
    if (parse_result.error) {
        fprintf(stderr, "FAIL: parse error: %s\n", parse_result.error->message);
        pg_query_free_parse_result(parse_result);
        return 1;
    }
    if (parse_result.parse_tree == NULL || strlen(parse_result.parse_tree) == 0) {
        fprintf(stderr, "FAIL: parse tree is empty\n");
        pg_query_free_parse_result(parse_result);
        return 1;
    }
    printf("PASS: pg_query_parse returned parse tree (len=%zu)\n", strlen(parse_result.parse_tree));
    pg_query_free_parse_result(parse_result);

    /* Test 2: Normalize a query */
    PgQueryNormalizeResult norm_result = pg_query_normalize("SELECT * FROM users WHERE id = 123");
    if (norm_result.error) {
        fprintf(stderr, "FAIL: normalize error: %s\n", norm_result.error->message);
        pg_query_free_normalize_result(norm_result);
        return 1;
    }
    printf("PASS: pg_query_normalize returned normalized query\n");
    pg_query_free_normalize_result(norm_result);

    /* Test 3: Fingerprint */
    PgQueryFingerprintResult fp_result = pg_query_fingerprint("SELECT 1");
    if (fp_result.error) {
        fprintf(stderr, "FAIL: fingerprint error: %s\n", fp_result.error->message);
        pg_query_free_fingerprint_result(fp_result);
        return 1;
    }
    printf("PASS: pg_query_fingerprint returned fingerprint\n");
    pg_query_free_fingerprint_result(fp_result);

    printf("All tests passed!\n");
    return 0;
}
