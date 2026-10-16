/*
 * test_package for minicsv — consumer-view test.
 * Parses a real CSV buffer through the packaged minicsv_parse_line() API and
 * verifies escaped/empty/multi-line row handling, plus minicsv_trim_cols().
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "minicsv.h"

static int
check_row(char *buf, size_t expect_cols)
{
    char  *cols[16];
    char  *r = buf;
    size_t cols_count = 0;

    r = minicsv_parse_line(r, cols, &cols_count, 16);
    if (cols_count != expect_cols) {
        fprintf(stderr, "FAIL: expected %zu cols, got %zu\n", expect_cols, cols_count);
        return 1;
    }
    return 0;
}

int
main(void)
{
    char  *cols[16];
    char   buf[] = "first,line,has,\"comas,\"\"escaped\"\" characters\",and,\"multiple\r\nlines\"\r\n"
                   "second,line,\"has\",,empty,,,,columns\r\nremainder";
    char  *r = buf;
    size_t cols_count;

    r = minicsv_parse_line(r, cols, &cols_count, 16);
    if (cols_count != 6) {
        fprintf(stderr, "FAIL row1: expected 6 cols, got %zu\n", cols_count);
        return 1;
    }
    if (strcmp(cols[3], "comas,\"escaped\" characters") != 0) {
        fprintf(stderr, "FAIL row1 col3: [%s]\n", cols[3]);
        return 1;
    }
    if (check_row(r, 9) != 0) {
        return 1;
    }
    /* trim columns with surrounding whitespace */
    {
        char  *trim_cols[4];
        char   trim_buf[] = "  a  ,b , c ";
        size_t trim_count = 0;
        minicsv_parse_line(trim_buf, trim_cols, &trim_count, 4);
        minicsv_trim_cols(trim_cols, trim_count);
        if (strcmp(trim_cols[0], "a") != 0 || strcmp(trim_cols[1], "b") != 0 ||
            strcmp(trim_cols[2], "c") != 0) {
            fprintf(stderr, "FAIL trim: [%s][%s][%s]\n", trim_cols[0], trim_cols[1], trim_cols[2]);
            return 1;
        }
    }
    printf("test_minicsv: OK (row1=6 cols, row2=9 cols, escaped/empty/multi-line/trim verified)\n");
    return 0;
}
