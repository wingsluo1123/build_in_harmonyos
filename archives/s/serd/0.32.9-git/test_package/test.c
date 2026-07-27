#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <serd/serd.h>

int main(void) {
    /* Construct a URI node and verify the buffer is non-empty. */
    SerdNode node = serd_node_new_uri_from_string(
        (const uint8_t*)"http://example.org/test", NULL, NULL);
    if (!node.buf || node.buf[0] == '\0') {
        fprintf(stderr, "serd_node_new_uri_from_string produced an empty node\n");
        return 1;
    }
    printf("serd API test: OK (%s)\n", (const char*)node.buf);
    serd_node_free(&node);
    return 0;
}
