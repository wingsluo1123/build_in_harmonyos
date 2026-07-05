#include <stdio.h>
#include "db.h"

int main(void) {
    int major, minor, patch;
    db_version(&major, &minor, &patch);
    printf("berkeley-db4 version: %d.%d.%d\n", major, minor, patch);
    return 0;
}
