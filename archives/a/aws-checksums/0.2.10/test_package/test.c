#include <stdio.h>
#include <string.h>
#include <aws/checksums/checksums.h>
#include <aws/checksums/crc.h>
#include <aws/common/allocator.h>

int main(void) {
    /* Initialize aws-checksums library */
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        fprintf(stderr, "Failed to get default allocator\n");
        return 1;
    }
    aws_checksums_library_init(allocator);

    /* Test CRC32 computation */
    const char *test_data = "Hello, HarmonyOS!";
    int len = (int)strlen(test_data);
    uint32_t crc32 = aws_checksums_crc32((const uint8_t *)test_data, len, 0);
    uint32_t crc32c = aws_checksums_crc32c((const uint8_t *)test_data, len, 0);

    printf("Input: %s\n", test_data);
    printf("CRC32:  0x%08X\n", crc32);
    printf("CRC32C: 0x%08X\n", crc32c);

    /* Verify non-zero results (valid checksums are produced) */
    if (crc32 == 0 || crc32c == 0) {
        printf("FAIL: checksum should not be zero\n");
        aws_checksums_library_clean_up();
        return 1;
    }

    printf("test aws-checksums 0.2.10: OK\n");

    /* Clean up */
    aws_checksums_library_clean_up();
    return 0;
}
