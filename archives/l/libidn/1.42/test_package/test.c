#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <idna.h>

int main(void) {
    char *output = NULL;
    int rc;
    rc = idna_to_ascii_8z("raksmorgas.example.org", &output, 0);
    if (rc != IDNA_SUCCESS) {
        fprintf(stderr, "idna_to_ascii_8z failed: %s\n", idna_strerror(rc));
        return 1;
    }
    printf("ASCII domain: %s\n", output);
    if (output) free(output);
    printf("test libidn 1.42: OK\n");
    return 0;
}
