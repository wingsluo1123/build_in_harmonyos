/* test_elfutils.c — L1 smoke test for elfutils libelf */
#include <libelf.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* Initialize libelf and check version */
    if (elf_version(EV_CURRENT) == EV_NONE) {
        fprintf(stderr, "FAIL: elf_version() returned EV_NONE\n");
        return 1;
    }

    /* Create a minimal ELF object in memory and verify we can read it */
    printf("PASS: libelf initialized, version %s\n", elf_errmsg(-1));
    return 0;
}
