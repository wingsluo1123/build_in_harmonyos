#include <stdio.h>
#include <lv2/core/lv2.h>
#include <lv2/core/lv2_util.h>

int main(void) {
    /* Verify LV2_CORE_URI macro is accessible */
    const char* uri = LV2_CORE_URI;
    if (!uri || uri[0] == '\0') {
        fprintf(stderr, "LV2_CORE_URI is empty\n");
        return 1;
    }
    /* Call lv2_features_data with NULL to verify function linkage */
    const char* data = lv2_features_data(NULL, "http://example.org/nonexistent");
    if (data != NULL) {
        fprintf(stderr, "unexpected non-NULL result\n");
        return 1;
    }
    printf("lv2 API test: OK (%s)\n", uri);
    return 0;
}
