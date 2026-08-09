#include <aws/s3/s3.h>
#include <aws/common/common.h>
#include <stdio.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    aws_common_library_init(allocator);
    aws_s3_library_init(allocator);

    printf("aws-c-s3 library initialized: OK\n");
    aws_s3_library_clean_up();
    printf("aws-c-s3 library cleaned up: OK\n");
    aws_common_library_clean_up();
    return 0;
}
