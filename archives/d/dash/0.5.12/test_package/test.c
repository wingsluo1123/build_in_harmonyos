#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Test program for dash: verifies core shell functionality via system() */
int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <dash_bin>\n", argv[0]);
        return 1;
    }
    const char *dash = argv[1];
    char cmd[512];
    int rc;

    /* Test 1: arithmetic expansion */
    snprintf(cmd, sizeof(cmd), "\"%s\" -c \"test $((1+2)) -eq 3\"", dash);
    rc = system(cmd);
    if (rc != 0) { fprintf(stderr, "FAIL: arithmetic\n"); return 1; }

    /* Test 2: variable assignment and comparison */
    snprintf(cmd, sizeof(cmd), "\"%s\" -c \"x=hello; test \\\"$x\\\" = hello\"", dash);
    rc = system(cmd);
    if (rc != 0) { fprintf(stderr, "FAIL: variable\n"); return 1; }

    /* Test 3: if/then conditional */
    snprintf(cmd, sizeof(cmd), "\"%s\" -c \"if [ 1 -lt 2 ]; then exit 0; fi\"", dash);
    rc = system(cmd);
    if (rc != 0) { fprintf(stderr, "FAIL: conditional\n"); return 1; }

    /* Test 4: for loop */
    snprintf(cmd, sizeof(cmd), "\"%s\" -c \"n=0; for i in 1 2 3; do n=$((n+i)); done; test $n -eq 6\"", dash);
    rc = system(cmd);
    if (rc != 0) { fprintf(stderr, "FAIL: for loop\n"); return 1; }

    printf("All dash tests passed\n");
    return 0;
}
