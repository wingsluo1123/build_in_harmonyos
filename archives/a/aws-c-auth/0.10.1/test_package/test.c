#include <stdio.h>
#include <aws/common/allocator.h>
#include <aws/auth/auth.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        fprintf(stderr, "FAIL: aws_default_allocator() returned NULL\n");
        return 1;
    }

    aws_auth_library_init(allocator);
    printf("aws-c-auth library initialized successfully\n");

    aws_auth_library_clean_up();
    printf("aws-c-auth library cleaned up successfully\n");
    return 0;
}
