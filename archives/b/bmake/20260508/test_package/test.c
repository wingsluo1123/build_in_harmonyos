#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    /* Run bmake -r -V MAKE_VERSION to verify the binary works */
    const char *cmd = "bmake -r -V MAKE_VERSION";
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        perror("popen");
        return 1;
    }

    char buf[128] = {0};
    if (fgets(buf, sizeof(buf), fp) == NULL) {
        fprintf(stderr, "FAIL: bmake produced no output\n");
        pclose(fp);
        return 1;
    }
    pclose(fp);

    /* Check that the version string is non-empty and matches expected pattern */
    size_t len = strlen(buf);
    while (len > 0 && (buf[len-1] == '\n' || buf[len-1] == '\r')) {
        buf[--len] = '\0';
    }
    if (len == 0) {
        fprintf(stderr, "FAIL: bmake version string is empty\n");
        return 1;
    }

    printf("test bmake %s: OK\n", buf);
    return 0;
}