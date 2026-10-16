#include <stdio.h>
#include <stdlib.h>
#include <libklvanc/vanc.h>

int main(void) {
    struct klvanc_context_s *ctx = NULL;
    int rc = klvanc_context_create(&ctx);
    if (rc != 0) {
        fprintf(stderr, "klvanc_context_create failed: %d\n", rc);
        return 1;
    }
    if (ctx == NULL) {
        fprintf(stderr, "klvanc_context_create returned NULL context\n");
        return 1;
    }
    /* Real API usage: context dump exercises internal parser state */
    klvanc_context_dump(ctx);
    rc = klvanc_context_destroy(ctx);
    if (rc != 0) {
        fprintf(stderr, "klvanc_context_destroy failed: %d\n", rc);
        return 1;
    }
    printf("libklvanc 1.0 test: OK (context create/dump/destroy)\n");
    return 0;
}