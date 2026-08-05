#include <stdio.h>

/* Forward-declare the aws-c-compression API to avoid needing aws-c-common headers.
 * The test verifies that libaws-c-compression.a links correctly. */
struct aws_allocator;
extern struct aws_allocator *aws_default_allocator(void);
extern void aws_compression_library_init(struct aws_allocator *allocator);
extern void aws_compression_library_clean_up(void);

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        fprintf(stderr, "FAIL: aws_default_allocator() returned NULL\n");
        return 1;
    }
    aws_compression_library_init(allocator);
    printf("aws-c-compression library initialized: OK\n");
    aws_compression_library_clean_up();
    printf("aws-c-compression library cleaned up: OK\n");
    return 0;
}
