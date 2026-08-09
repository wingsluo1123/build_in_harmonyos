#include <aws/auth/auth.h>
#include <aws/common/common.h>
#include <stdio.h>
int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    aws_common_library_init(allocator);
    aws_auth_library_init(allocator);
    printf("aws-c-auth library initialized: OK\n");
    aws_auth_library_clean_up();
    printf("aws-c-auth library cleaned up: OK\n");
    aws_common_library_clean_up();
    return 0;
}
