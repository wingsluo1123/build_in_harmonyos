#include <stdio.h>
#include <stdlib.h>
#include <libpq-fe.h>

int main(void) {
    int version = PQlibVersion();
    if (version <= 0) {
        fprintf(stderr, "ERROR: PQlibVersion() returned %d\n", version);
        return 1;
    }
    printf("libpq version: %d (PostgreSQL %d.%d)\n",
           version, version / 10000, (version / 100) % 100);
    return 0;
}
