#include <stdio.h>

/* Forward-declare the aws-c-compression API to verify the library links
 * correctly and functions are callable. */
struct aws_allocator;
extern void aws_compression_library_init(struct aws_allocator *alloc);
extern void aws_compression_library_clean_up(void);

int main(void) {
    aws_compression_library_init((void *)0);
    printf("aws-c-compression library initialized: OK\n");
    aws_compression_library_clean_up();
    printf("aws-c-compression library cleaned up: OK\n");
    return 0;
}
