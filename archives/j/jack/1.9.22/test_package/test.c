#include <stdio.h>
#include <jack/jack.h>

int main(void) {
    /* Call jack_client_name_size() — a simple function that doesn't
       require a running JACK server, proving the library is correctly
       linked and functional. */
    int name_size = jack_client_name_size();
    printf("jack client name size: %d\n", name_size);
    if (name_size > 0) {
        printf("test jack: OK\n");
        return 0;
    }
    fprintf(stderr, "test jack: FAIL (name_size=%d)\n", name_size);
    return 1;
}
