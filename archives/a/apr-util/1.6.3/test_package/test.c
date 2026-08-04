#include <apr.h>
#include <apr_general.h>
#include <apr_version.h>
#include <apr_pools.h>
#include <apu.h>
#include <apu_version.h>
#include <apr_buckets.h>
#include <stdio.h>

int main(void) {
    apr_status_t rv;
    apr_pool_t *pool;

    rv = apr_initialize();
    if (rv != APR_SUCCESS) {
        fprintf(stderr, "apr_initialize failed\n");
        return 1;
    }

    printf("APR version: %s\n", apr_version_string());
    printf("APR-util version: %s\n", apu_version_string());

    rv = apr_pool_create(&pool, NULL);
    if (rv != APR_SUCCESS) {
        fprintf(stderr, "apr_pool_create failed\n");
        apr_terminate();
        return 1;
    }

    apr_bucket_alloc_t *ba = apr_bucket_alloc_create(pool);
    if (!ba) {
        fprintf(stderr, "apr_bucket_alloc_create failed\n");
        apr_pool_destroy(pool);
        apr_terminate();
        return 1;
    }

    printf("Bucket allocator created successfully\n");
    apr_bucket_alloc_destroy(ba);
    apr_pool_destroy(pool);
    apr_terminate();
    printf("test apr-util: OK\n");
    return 0;
}
