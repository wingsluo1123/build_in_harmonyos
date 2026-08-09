#include <aws/io/io.h>
#include <aws/common/allocator.h>
#include <stdio.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        fprintf(stderr, "FAIL: aws_default_allocator returned NULL\n");
        return 1;
    }

    aws_io_library_init(allocator);
    printf("PASS: aws_io_library_init succeeded\n");

    aws_io_library_clean_up();
    printf("PASS: aws-c-io 0.26.3 test completed successfully\n");
    return 0;
}
