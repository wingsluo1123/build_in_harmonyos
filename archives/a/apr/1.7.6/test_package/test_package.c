/* test_package.c — apr 1.7.6
 * Calls apr_initialize() and prints apr_version_string().
 */
#include <stdio.h>
#include <stdlib.h>
#include "apr.h"
#include "apr_general.h"
#include "apr_version.h"

int main(void)
{
    apr_status_t rv;
    rv = apr_initialize();
    if (rv != APR_SUCCESS) {
        fprintf(stderr, "apr_initialize() failed: %d\n", rv);
        return 1;
    }
    printf("APR version: %s\n", apr_version_string());
    apr_terminate();
    return 0;
}
