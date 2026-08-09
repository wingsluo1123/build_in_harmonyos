#include <aws/io/io.h>
#include <aws/common/common.h>
#include <stdio.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    aws_common_library_init(allocator);
    aws_io_library_init(allocator);

    printf("aws-c-io library initialized: OK\n");
    aws_io_library_clean_up();
    printf("aws-c-io library cleaned up: OK\n");
    aws_common_library_clean_up();
    return 0;
}
