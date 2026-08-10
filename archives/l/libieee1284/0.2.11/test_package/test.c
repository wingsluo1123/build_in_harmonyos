#include <stdio.h>
#include <ieee1284.h>

int main(void) {
    struct parport_list pl;
    int num_ports = ieee1284_find_ports(&pl, 0);
    if (num_ports >= 0) {
        printf("Found %d parallel port(s)\n", num_ports);
        ieee1284_free_ports(&pl);
    } else {
        printf("ieee1284_find_ports returned %d (expected on systems without parallel ports)\n", num_ports);
    }
    printf("libieee1284 API test: OK\n");
    return 0;
}
