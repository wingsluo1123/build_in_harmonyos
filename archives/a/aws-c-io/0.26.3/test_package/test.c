#include <aws/common/allocator.h>
#include <aws/io/io.h>
#include <stdio.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        fprintf(stderr, "Failed to get default allocator\n");
        return 1;
    }
    aws_io_library_init(allocator);
    printf("test aws-c-io 0.26.3: OK\n");
    aws_io_library_clean_up();
    return 0;
}
