#include <stdio.h>

/* Forward-declare APIs to avoid header include issues (CMakeDeps include dir
 * propagation issue with transitive deps on OHOS conan). */
struct aws_allocator;
extern struct aws_allocator *aws_default_allocator(void);
extern void aws_http_library_init(struct aws_allocator *alloc);
extern void aws_http_library_clean_up(void);

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        fprintf(stderr, "FAIL: aws_default_allocator() returned NULL\n");
        return 1;
    }

    aws_http_library_init(allocator);
    printf("aws-c-http library initialized: OK\n");
    aws_http_library_clean_up();
    printf("aws-c-http library cleaned up: OK\n");
    return 0;
}
