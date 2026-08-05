/* Stub implementation of aws_tls_handler_protocol.
 *
 * aws-c-io built with BYO_CRYPTO=ON does not compile this function,
 * but aws-c-http references it. This stub provides a safe fallback
 * that returns an empty byte_buf.
 */
#include <stddef.h>

typedef struct {
    size_t len;
    size_t capacity;
    unsigned char *buffer;
    void *allocator;
} aws_byte_buf_stub;

aws_byte_buf_stub aws_tls_handler_protocol(void *handler) {
    aws_byte_buf_stub empty = {0, 0, NULL, NULL};
    return empty;
}
