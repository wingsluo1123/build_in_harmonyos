#include <aws/compression/compression.h>
#include <aws/common/allocator.h>
#include <stdio.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        fprintf(stderr, "FAIL: aws_default_allocator returned NULL\n");
        return 1;
    }

    aws_compression_library_init(allocator);
    printf("PASS: aws_compression_library_init succeeded\n");

    aws_compression_library_clean_up();
    printf("PASS: aws-c-compression 0.3.2 test completed successfully\n");
    return 0;
}
