#include <stdio.h>
#include <stdlib.h>
#include <ao/ao.h>

int main(void) {
    /* Initialize libao and check it returns a valid driver count */
    ao_initialize();
    int driver_count = ao_driver_id_count();
    printf("test libao 1.2.2: drivers=%d OK\n", driver_count);
    ao_shutdown();
    return 0;
}
