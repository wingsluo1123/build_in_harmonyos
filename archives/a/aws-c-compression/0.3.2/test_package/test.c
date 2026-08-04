#include <stdio.h>
#include <stdlib.h>

#include <aws/common/allocator.h>
#include <aws/compression/compression.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    aws_compression_library_init(allocator);
    aws_compression_library_clean_up();
    printf("test aws-c-compression 0.3.2: OK\n");
    return 0;
}
