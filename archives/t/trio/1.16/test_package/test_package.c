#include <stdio.h>
#include <string.h>
#include "triop.h"
#include "trio.h"

int main() {
    char buf[256];
    trio_snprintf(buf, sizeof(buf), "trio test: %d + %d = %d", 1, 2, 3);
    if (strstr(buf, "trio test: 1 + 2 = 3")) {
        printf("trio test OK: %s\n", buf);
        return 0;
    }
    printf("trio test FAIL: %s\n", buf);
    return 1;
}
