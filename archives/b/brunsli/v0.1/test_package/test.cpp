#include <brunsli/jpeg_data.h>
#include <brunsli/brunsli_encode.h>
#include <cstdio>

int main() {
    /* Real API test: call GetMaximumBrunsliEncodedSize from brunslienc-static.
     * This function computes an upper bound on the brunsli-encoded size
     * of a JPEGData object. A default-constructed JPEGData represents
     * an empty image, so the result should be a valid size_t value. */
    brunsli::JPEGData jpg;
    size_t max_size = brunsli::GetMaximumBrunsliEncodedSize(jpg);
    printf("TEST PASSED: GetMaximumBrunsliEncodedSize returned %zu\n", max_size);
    return 0;
}
