#include <pg_query.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* Test pg_query_parse: parse a simple SQL query */
    PgQueryParseResult result = pg_query_parse("SELECT 1");
    if (result.error) {
        fprintf(stderr, "Error: %s\n", result.error->message);
        pg_query_free_parse_result(result);
        return 1;
    }
    if (result.parse_tree == NULL || strlen(result.parse_tree) == 0) {
        fprintf(stderr, "Error: parse_tree is empty\n");
        pg_query_free_parse_result(result);
        return 1;
    }
    printf("parse_tree length: %zu\n", strlen(result.parse_tree));
    pg_query_free_parse_result(result);
    return 0;
}
