#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <lv2/core/lv2.h>
#include <lv2/core/lv2_util.h>

int main(void) {
    /* Verify LV2_CORE_URI macro is accessible */
    const char* uri = LV2_CORE_URI;
    if (!uri || uri[0] == '\0') {
        fprintf(stderr, "LV2_CORE_URI is empty\n");
        return 1;
    }
    /* Call lv2_features_data with NULL to verify function linkage.
     * Returns NULL when the feature list is empty (no matching feature). */
    const char* data = lv2_features_data(NULL, "http://example.org/nonexistent");
    if (data != NULL) {
        fprintf(stderr, "unexpected non-NULL result from lv2_features_data\n");
        return 1;
    }
    printf("lv2 API test: OK (%s)\n", uri);
    return 0;
}
