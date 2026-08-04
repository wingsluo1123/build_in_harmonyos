#include <aws/common/allocator.h>
#include <aws/event-stream/event_stream.h>
#include <stdio.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        fprintf(stderr, "Failed to get default allocator\n");
        return 1;
    }
    aws_event_stream_library_init(allocator);
    printf("test aws-c-event-stream 0.7.0: OK\n");
    aws_event_stream_library_clean_up();
    return 0;
}
