#include <stdio.h>
#include <stdlib.h>
#include <serd/serd.h>

int main(void) {
    SerdNode node = serd_node_new_uri_from_string(
        (const uint8_t*)"http://example.org/test", NULL, NULL);
    if (!node.buf) {
        fprintf(stderr, "serd_node_new_uri_from_string failed\n");
        return 1;
    }
    printf("serd API test: OK (%s)\n", (const char*)node.buf);
    serd_node_free(&node);
    return 0;
}
