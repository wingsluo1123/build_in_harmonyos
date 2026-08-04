#include <aws/common/allocator.h>
#include <aws/cal/cal.h>
#include <stdio.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        fprintf(stderr, "Failed to get default allocator\n");
        return 1;
    }

    aws_cal_library_init(allocator);
    aws_cal_library_clean_up();

    printf("aws-c-cal 0.9.13 test: OK\n");
    return 0;
}
