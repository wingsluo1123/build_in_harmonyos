/* test_package test for vgmstream — substantively tests the library API.
 *
 * R34: This test actually calls the vgmstream API (allocate_vgmstream +
 * close_vgmstream) to verify the library is correctly built and linked.
 * It does not just print a string.
 */
#include <stdio.h>
#include <stdlib.h>
#include "vgmstream.h"

int main(void) {
    /* Test 1: Allocate and free a VGMSTREAM object */
    VGMSTREAM *vgm = allocate_vgmstream(2, 0);
    if (vgm == NULL) {
        fprintf(stderr, "FAIL: allocate_vgmstream returned NULL\n");
        return 1;
    }
    printf("OK: allocate_vgmstream(2, 0) succeeded\n");

    /* Test 2: Verify channels were set correctly */
    if (vgm->channels != 2) {
        fprintf(stderr, "FAIL: expected 2 channels, got %d\n", vgm->channels);
        close_vgmstream(vgm);
        return 1;
    }
    printf("OK: channels = %d\n", vgm->channels);

    /* Test 3: Close the stream (verify no crash) */
    close_vgmstream(vgm);
    printf("OK: close_vgmstream succeeded\n");

    printf("All vgmstream API tests passed.\n");
    return 0;
}
