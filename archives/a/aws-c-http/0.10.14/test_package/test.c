#include <aws/http/http.h>
#include <aws/common/common.h>
#include <stdio.h>
int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    aws_common_library_init(allocator);
    aws_http_library_init(allocator);
    printf("aws-c-http library initialized: OK\n");
    aws_http_library_clean_up();
    printf("aws-c-http library cleaned up: OK\n");
    aws_common_library_clean_up();
    return 0;
}
