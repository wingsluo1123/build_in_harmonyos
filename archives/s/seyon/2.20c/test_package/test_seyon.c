/*
 * test_seyon.c — seyon 2.20c consumer test (R34).
 *
 * Links the packaged static library libseyon.a and calls seyon's real yacc
 * script parser ParseThis() (SeParse.c / SeParse.h).  This exercises the
 * package's linkable API without needing an X display.
 *
 * ParseThis(line, callback) parses one seyon command-language line and invokes
 * the callback with:
 *   code 1 -> function name (arg = the name)
 *   code 2 -> one argument   (arg = the argument)
 *   code 3 -> end of a function call
 *   code 4 -> parse error    (arg = message)
 * (grammar actions in SeParse.y).
 *
 * NOTE: the scanner writes back into the line buffer (scUngetChar in
 * SeScan.c), so the input MUST be a mutable buffer -- a string literal lives
 * in read-only memory and segfaults.
 */
#include <stdio.h>
#include <string.h>

#include <seyon/SeParse.h>

#define MAXF 16
static char funcs[MAXF][64];
static int nfunc = 0;
static int nargs = 0;
static int ncalls = 0;
static int nerr = 0;

static void callback(int code, char *arg)
{
    if (code == 1) {
        if (nfunc < MAXF)
            snprintf(funcs[nfunc], sizeof(funcs[0]), "%s", arg ? arg : "");
        nfunc++;
    } else if (code == 2) {
        nargs++;
    } else if (code == 3) {
        ncalls++;
    } else if (code == 4) {
        nerr++;
    }
}

int main(void)
{
    /* mutable buffer: ParseThis/scUngetChar writes back into it */
    char line[] = "dial(5551234, 9600);";

    ParseThis(line, (void (*)()) callback);

    if (nerr != 0) {
        printf("FAIL: parser reported %d error(s)\n", nerr);
        return 1;
    }
    if (nfunc != 1 || strcmp(funcs[0], "dial") != 0) {
        printf("FAIL: expected function 'dial', got '%s' (%d funcs)\n",
               nfunc ? funcs[0] : "(none)", nfunc);
        return 1;
    }
    if (nargs != 2) {
        printf("FAIL: expected 2 arguments, got %d\n", nargs);
        return 1;
    }
    if (ncalls != 1) {
        printf("FAIL: expected 1 completed call, got %d\n", ncalls);
        return 1;
    }

    printf("PASS: ParseThis parsed 'dial(5551234, 9600);' -> "
           "func=%s args=%d calls=%d\n", funcs[0], nargs, ncalls);
    return 0;
}
