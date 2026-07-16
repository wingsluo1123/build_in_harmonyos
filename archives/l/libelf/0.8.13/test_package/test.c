#include <libelf.h>
#include <stdio.h>

int main() {
    if (elf_version(EV_CURRENT) == EV_NONE) {
        fprintf(stderr, "elf_version failed\n");
        return 1;
    }
    printf("libelf version: %s\n", elf_version(EV_CURRENT) == EV_CURRENT ? "ok" : "unknown");
    return 0;
}
