#include <stdio.h>
#include <stdlib.h>

int main(void) {
    const char *cmd = "btop --help";
    printf("Running: %s\n", cmd);
    int ret = system(cmd);
    if (ret != 0) {
        fprintf(stderr, "btop execution failed with code %d\n", ret);
        return 1;
    }
    printf("btop works!\n");
    return 0;
}
