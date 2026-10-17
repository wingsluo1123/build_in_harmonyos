#include <stdio.h>
#include <string.h>
#include <tcd.h>

int main(void) {
    /* Test ret_date: converts YYYYMMDD integer to "YYYY-MM-DD" string */
    NV_CHAR *date = ret_date(20201016);
    if (!date || strcmp(date, "2020-10-16") != 0) {
        fprintf(stderr, "ret_date failed: got '%s'\n", date ? date : "(null)");
        return 1;
    }

    /* Test ret_time: converts +/-HHMM integer to "+/-HH:MM" string */
    NV_CHAR *time = ret_time(530);
    if (!time || strcmp(time, "+05:30") != 0) {
        fprintf(stderr, "ret_time failed: got '%s'\n", time ? time : "(null)");
        return 1;
    }

    /* Test ret_date with 0 (should return "NULL") */
    NV_CHAR *null_date = ret_date(0);
    if (!null_date || strcmp(null_date, "NULL") != 0) {
        fprintf(stderr, "ret_date(0) failed: got '%s'\n", null_date ? null_date : "(null)");
        return 1;
    }

    printf("libtcd 2.2.7 API test passed: ret_date, ret_time OK\n");
    return 0;
}
