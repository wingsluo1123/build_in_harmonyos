#include <stdio.h>
#include "cdda_interface.h"

int main(void) {
    /* Call cdda_find_a_cdrom: scans for CD-ROM drives.
     * Returns NULL on systems without CD-ROM hardware (expected on OHOS).
     * This verifies the library links and the function is callable. */
    cdrom_drive *d = cdda_find_a_cdrom(0, NULL);
    printf("cdparanoia test: cdda_find_a_cdrom returned %p (NULL expected without CD-ROM)\n", (void *)d);
    printf("cdparanoia 10.2: OK\n");
    return 0;
}
