#include <ogg/ogg.h>
#include <stdio.h>

int main(void) {
    ogg_stream_state os;
    /* Initialize a stream with serial number 0 */
    if (ogg_stream_init(&os, 0) != 0) {
        fprintf(stderr, "ogg_stream_init failed\n");
        return 1;
    }
    /* Clean up */
    ogg_stream_clear(&os);
    printf("test libogg 1.3.6: OK\n");
    return 0;
}
