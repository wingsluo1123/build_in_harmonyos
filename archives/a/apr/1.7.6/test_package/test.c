#include <stdio.h>
#include <stdlib.h>
#include "apr.h"
#include "apr_general.h"
#include "apr_pools.h"
#include "apr_version.h"

int main(void) {
    apr_status_t rv;
    apr_pool_t *pool;

    rv = apr_initialize();
    if (rv != APR_SUCCESS) {
        fprintf(stderr, "apr_initialize() failed\n");
        return 1;
    }

    rv = apr_pool_create(&pool, NULL);
    if (rv != APR_SUCCESS) {
        fprintf(stderr, "apr_pool_create() failed\n");
        apr_terminate();
        return 1;
    }

    printf("apr version: %s\n", APR_VERSION_STRING);
    printf("test apr 1.7.6: OK\n");

    apr_pool_destroy(pool);
    apr_terminate();
    return 0;
}
