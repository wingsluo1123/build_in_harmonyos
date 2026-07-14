#include <stdio.h>
#include <string.h>

/* Test: run spin -V and verify version string */
int main(void) {
    FILE *fp = popen("spin -V", "r");
    if (!fp) {
        fprintf(stderr, "Failed to run spin -V\n");
        return 1;
    }
    char buf[256];
    int found = 0;
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, "Spin Version 6.5.2") != NULL) {
            found = 1;
            break;
        }
    }
    pclose(fp);
    if (!found) {
        fprintf(stderr, "spin -V output unexpected\n");
        return 1;
    }
    printf("spin -V verified: %s", buf);
    return 0;
}
