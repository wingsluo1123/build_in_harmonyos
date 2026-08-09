#include <aws/event-stream/event_stream.h>
#include <aws/common/common.h>
#include <stdio.h>
int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    aws_common_library_init(allocator);
    aws_event_stream_library_init(allocator);
    printf("aws-c-event-stream library initialized: OK\n");
    aws_event_stream_library_clean_up();
    printf("aws-c-event-stream library cleaned up: OK\n");
    aws_common_library_clean_up();
    return 0;
}
