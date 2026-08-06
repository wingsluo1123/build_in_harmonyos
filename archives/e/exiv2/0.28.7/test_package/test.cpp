#include <exiv2/exiv2.hpp>
#include <cstdio>

int main(void) {
    // R34: test must actually call the package's API
    const char *ver = Exiv2::version();
    if (!ver || ver[0] == '\0') {
        fprintf(stderr, "FAIL: exiv2 version() returned empty\n");
        return 1;
    }
    printf("exiv2 version: %s\n", ver);
    printf("OK\n");
    return 0;
}
