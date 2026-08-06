#include <orc/orc.h>
#include <stdio.h>

int main() {
    orc_init();
    printf("ORC version: %s\n", orc_version_string());
    return 0;
}
