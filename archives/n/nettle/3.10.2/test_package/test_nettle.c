#include <stdio.h>
#include <nettle/nettle-types.h>
#include <nettle/version.h>

int main() {
    printf("Nettle version: %s\n", nettle_version_string());
    return 0;
}