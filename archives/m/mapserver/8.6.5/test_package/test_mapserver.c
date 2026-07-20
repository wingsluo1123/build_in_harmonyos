#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mapserver.h"

static void require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "MapServer test failed: %s\n", message);
        exit(1);
    }
}

int main(void)
{
    char *version = msGetVersion();
    require_true(version != NULL, "version string is available");
    require_true(strstr(version, "MapServer version") != NULL, "version string has expected prefix");
    require_true(msGetVersionInt() == 80605, "version integer is 80605");
    return 0;
}
