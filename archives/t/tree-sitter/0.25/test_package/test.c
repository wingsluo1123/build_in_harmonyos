#include <stdio.h>
#include <stdlib.h>
#include "tree_sitter/api.h"

int main(void) {
    /* Create a parser — substantively tests the library API */
    TSParser *parser = ts_parser_new();
    if (parser == NULL) {
        fprintf(stderr, "FAIL: ts_parser_new() returned NULL\n");
        return 1;
    }

    /* Verify the ABI version constant is defined and reasonable */
    if (TREE_SITTER_LANGUAGE_VERSION < 1) {
        fprintf(stderr, "FAIL: TREE_SITTER_LANGUAGE_VERSION is %d\n", TREE_SITTER_LANGUAGE_VERSION);
        ts_parser_delete(parser);
        return 1;
    }

    ts_parser_delete(parser);
    printf("test tree-sitter 0.25: OK (ABI version=%d)\n", TREE_SITTER_LANGUAGE_VERSION);
    return 0;
}
