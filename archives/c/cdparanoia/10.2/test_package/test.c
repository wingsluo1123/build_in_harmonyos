#include <stdio.h>
#include "cdda_interface.h"

int main(void) {
    /* Include the header and verify the library links.
     * cdda_find_a_cdrom scans for CD-ROM drives.
     * On systems without CD-ROM hardware, it returns NULL (expected on OHOS).
     * This test verifies the library links and the function is callable. */
    cdrom_drive *d = cdda_find_a_cdrom(0, NULL);
    (void)d; /* NULL expected without CD-ROM, no assertion needed */
    printf("cdparanoia 10.2: library link test OK\n");
    return 0;
}
