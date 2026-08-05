#include <stdio.h>

/* Forward-declare the aws-c-io API to verify the library links
 * correctly and functions are callable. */
struct aws_allocator;
extern void aws_io_library_init(struct aws_allocator *allocator);
extern void aws_io_library_clean_up(void);
/* Forward-declare aws_default_allocator from aws-c-common */
extern struct aws_allocator *aws_default_allocator(void);

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (!allocator) {
        printf("ERROR: default allocator is NULL\n");
        return 1;
    }
    aws_io_library_init(allocator);
    printf("aws-c-io library initialized: OK\n");
    aws_io_library_clean_up();
    printf("aws-c-io library cleaned up: OK\n");
    return 0;
}
