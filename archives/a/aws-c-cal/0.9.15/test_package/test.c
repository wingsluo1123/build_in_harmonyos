#include <stdio.h>
#include <aws/common/common.h>
#include <aws/common/allocator.h>
#include <aws/cal/cal.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        fprintf(stderr, "FAIL: aws_default_allocator() returned NULL\n");
        return 1;
    }

    aws_common_library_init(allocator);
    aws_cal_library_init(allocator);
    printf("aws-c-cal library initialized successfully\n");

    aws_cal_library_clean_up();
    aws_common_library_clean_up();
    printf("aws-c-cal library cleaned up successfully\n");
    return 0;
}
