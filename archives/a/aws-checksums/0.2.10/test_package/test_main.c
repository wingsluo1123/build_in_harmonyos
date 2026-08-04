#include <aws/checksums/checksums.h>
#include <aws/checksums/crc.h>
#include <aws/common/common.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* Initialize aws-checksums library (requires aws-c-common allocator) */
    struct aws_allocator *allocator = aws_default_allocator();
    aws_checksums_library_init(allocator);

    /* Compute CRC32 of "hello world" */
    const char *data = "hello world";
    int len = (int)strlen(data);
    uint32_t crc = aws_checksums_crc32((const uint8_t *)data, len, 0);
    printf("CRC32(\"%s\") = 0x%08x\n", data, crc);

    /* Verify CRC32 result is non-zero (basic sanity check) */
    if (crc == 0) {
        fprintf(stderr, "FAIL: CRC32 returned 0 (unexpected)\n");
        aws_checksums_library_clean_up();
        return 1;
    }

    printf("OK: aws-checksums 0.2.10 test passed\n");

    aws_checksums_library_clean_up();
    return 0;
}
