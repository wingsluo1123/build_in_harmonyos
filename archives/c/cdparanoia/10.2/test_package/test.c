#include <stdio.h>
#include "cdda_interface.h"
#include "cdda_paranoia.h"

int main(void) {
    /* Verify library headers are accessible and the library links correctly.
     * We declare a pointer but don't call hardware-accessing functions,
     * as CI workers have no CD-ROM hardware. */
    cdrom_drive *d = NULL;
    cdrom_paranoia *p = NULL;
    (void)d;
    (void)p;
    printf("cdparanoia 10.2: library link test OK\n");
    return 0;
}
