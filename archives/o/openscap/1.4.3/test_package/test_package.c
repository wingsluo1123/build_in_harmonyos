#include <openscap/oscap.h>
#include <stdio.h>

int main() {
    const char *ver = oscap_get_version();
    printf("OpenSCAP version: %s\n", ver ? ver : "unknown");
    if (ver) {
        return 0;
    }
    return 1;
}
