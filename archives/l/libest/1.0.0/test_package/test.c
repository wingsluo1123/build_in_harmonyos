#include <stdio.h>
#include <string.h>
#include "est.h"

int main(void) {
    const char *version;
    int api_level;

    /* Exercise real libest public API: version + API level + logger init. */
    version = est_get_version();
    if (version == NULL || strcmp(version, "") == 0) {
        printf("test libest 1.0.0: FAIL (est_get_version empty)\n");
        return 1;
    }

    api_level = est_get_api_level();
    if (api_level <= 0) {
        printf("test libest 1.0.0: FAIL (est_get_api_level=%d)\n", api_level);
        return 1;
    }

    if (est_init_logger(EST_LOG_LVL_INFO, NULL) != EST_ERR_NONE) {
        printf("test libest 1.0.0: FAIL (est_init_logger)\n");
        return 1;
    }

    printf("test libest 1.0.0: OK (version=%s api_level=%d)\n", version, api_level);
    return 0;
}
