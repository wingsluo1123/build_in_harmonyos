#include <stdio.h>
#include <stdlib.h>
#include <csv.h>

int main(void) {
    struct csv_parser parser;
    int ret = csv_init(&parser, 0);
    if (ret != 0) {
        fprintf(stderr, "Failed to initialize CSV parser\n");
        return 1;
    }
    csv_free(&parser);
    printf("test libcsv 3.0.3: OK\n");
    return 0;
}
