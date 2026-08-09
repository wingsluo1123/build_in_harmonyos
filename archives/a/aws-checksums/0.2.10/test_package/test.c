#include <aws/checksums/checksums.h>
#include <aws/checksums/crc.h>
#include <aws/common/common.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    aws_common_library_init(allocator);
    aws_checksums_library_init(allocator);

    const uint8_t data[] = "Hello, OHOS!";
    uint32_t crc = aws_checksums_crc32(data, (int)strlen((const char *)data), 0);
    printf("CRC32 of 'Hello, OHOS!' = 0x%08x\n", crc);

    if (crc == 0) {
        fprintf(stderr, "FAIL: CRC32 returned 0 for non-empty input\n");
        aws_checksums_library_clean_up();
        aws_common_library_clean_up();
        return 1;
    }

    printf("aws-checksums library test: OK\n");
    aws_checksums_library_clean_up();
    aws_common_library_clean_up();
    return 0;
}
