#include <stdio.h>

/* Forward-declare the aws-c-io API to avoid needing aws-c-common headers.
 * The test verifies that libaws-c-io.a links correctly and the library
 * functions are callable. */
struct aws_allocator;
extern struct aws_allocator *aws_default_allocator(void);
extern int aws_io_library_init(struct aws_allocator *allocator);
extern void aws_io_library_clean_up(void);

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        fprintf(stderr, "FAIL: aws_default_allocator() returned NULL\n");
        return 1;
    }
    aws_io_library_init(allocator);
    printf("aws-c-io library initialized: OK\n");
    aws_io_library_clean_up();
    printf("aws-c-io library cleaned up: OK\n");
    return 0;
}
