#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/utsname.h>
#include "linebreak.h"
#include "wordbreak.h"
#include "graphemebreak.h"

#define CHECK(x) do { ++assertions; if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)
int main(void) {
    int assertions = 0;
    char breaks[32];
    const utf32_t combining[] = {0x0041, 0x0308, 0x0042};
    const utf8_t chinese[] = {0xe4,0xb8,0xad,0xe6,0x96,0x87};
    const utf8_t ascii[] = {'A','\r','\n','B'};
    init_linebreak(); init_wordbreak(); init_graphemebreak();
    set_linebreaks_utf8(ascii, sizeof(ascii), "en", breaks);
    CHECK(breaks[1] == LINEBREAK_NOBREAK && breaks[2] == LINEBREAK_MUSTBREAK);
    set_graphemebreaks_utf32(combining, 3, NULL, breaks);
    CHECK(breaks[0] == GRAPHEMEBREAK_NOBREAK && breaks[1] == GRAPHEMEBREAK_BREAK);
    set_wordbreaks_utf8((const utf8_t *)"one two", 7, "en", breaks);
    CHECK(breaks[0] == WORDBREAK_NOBREAK && breaks[2] == WORDBREAK_BREAK);
    size_t points = set_linebreaks_utf8_per_code_point(chinese, sizeof(chinese), "zh", breaks);
    CHECK(points == 2 && breaks[0] == LINEBREAK_ALLOWBREAK);
    struct utsname platform;
    const char *expected_platform = getenv("LIBUNIBREAK_EXPECTED_SYSNAME");
    CHECK(expected_platform && uname(&platform) == 0
        && strcmp(platform.sysname, expected_platform) == 0);
    const char *tmp = getenv("TMPDIR");
    CHECK(tmp && *tmp);
    char path[1024];
    CHECK(snprintf(path, sizeof(path), "%s/unibreak-XXXXXX", tmp) < (int)sizeof(path));
    int fd = mkstemp(path);
    CHECK(fd >= 0);
    unsigned char loaded[sizeof(chinese)];
    int io_ok = write(fd, chinese, sizeof(chinese)) == sizeof(chinese)
        && pread(fd, loaded, sizeof(loaded), 0) == sizeof(loaded)
        && memcmp(loaded, chinese, sizeof(chinese)) == 0;
    int close_ok = close(fd) == 0;
    int unlink_ok = unlink(path) == 0;
    CHECK(io_ok && close_ok && unlink_ok);
    set_graphemebreaks_utf8(loaded, sizeof(loaded), "zh", breaks);
    CHECK(breaks[0] == GRAPHEMEBREAK_INSIDEACHAR
        && breaks[1] == GRAPHEMEBREAK_INSIDEACHAR
        && breaks[2] == GRAPHEMEBREAK_BREAK);
    printf("CONSUMER_1_OF_1_PASS assertions=%d\n", assertions);
    return 0;
}
