#include <maxminddb.h>

#include <string.h>

int main(void) {
    const char *version = MMDB_lib_version();
    if (version == NULL || version[0] == '\0') {
        return 1;
    }
    return strstr(version, "1.11.0") != NULL ? 0 : 2;
}
