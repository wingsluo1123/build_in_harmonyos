#include <aws/sdkutils/sdkutils.h>
#include <aws/common/common.h>
#include <stdio.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    aws_common_library_init(allocator);
    aws_sdkutils_library_init(allocator);

    printf("aws-c-sdkutils library initialized: OK\n");
    aws_sdkutils_library_clean_up();
    printf("aws-c-sdkutils library cleaned up: OK\n");
    aws_common_library_clean_up();
    return 0;
}
