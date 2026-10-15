#include <stdio.h>
#include <stdlib.h>
#include <libkdumpfile/kdumpfile.h>
#include <libkdumpfile/addrxlat.h>

int main(void) {
    kdump_ctx_t *ctx;
    addrxlat_ctx_t *axctx;
    int rc = 0;

    /* Create a libkdumpfile context and verify the API round-trips. */
    ctx = kdump_new();
    if (!ctx) {
        fprintf(stderr, "kdump_new() failed\n");
        return 1;
    }
    printf("kdump_new() OK: %s\n", kdump_strerror(KDUMP_OK));
    kdump_free(ctx);
    printf("kdump_free() OK\n");

    /* Create an addrxlat context (companion library, same package). */
    axctx = addrxlat_ctx_new();
    if (!axctx) {
        fprintf(stderr, "addrxlat_ctx_new() failed\n");
        return 1;
    }
    printf("addrxlat_ctx_new() OK\n");
    addrxlat_ctx_decref(axctx);
    printf("addrxlat_ctx_decref() OK\n");

    return rc;
}
