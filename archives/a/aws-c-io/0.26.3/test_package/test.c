#include <stdio.h>

/* Forward-declare the aws-c-io API to verify the library links
 * correctly and functions are callable. */
struct aws_allocator;
extern void aws_io_library_init(struct aws_allocator *allocator);
extern void aws_io_library_clean_up(void);

int main(void) {
    aws_io_library_init((void *)0);
    printf("aws-c-io library initialized: OK\n");
    aws_io_library_clean_up();
    printf("aws-c-io library cleaned up: OK\n");
    return 0;
}
