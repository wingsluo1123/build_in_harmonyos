#include <stdio.h>
#include <efivar.h>

int main() {
    uint32_t ver = efi_get_libefivar_version();
    printf("efivar library version: %u\n", ver);
    return (ver > 0) ? 0 : 1;
}
