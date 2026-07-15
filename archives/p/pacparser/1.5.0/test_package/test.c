#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "pacparser.h"

int main(void) {
    /* Initialize pacparser */
    if (!pacparser_init()) {
        fprintf(stderr, "pacparser_init failed\n");
        return 1;
    }

    /* Parse a simple PAC string */
    const char *pac_str =
        "function FindProxyForURL(url, host) {"
        "  return \"DIRECT\";"
        "}";
    if (!pacparser_parse_pac_string((char *)pac_str)) {
        fprintf(stderr, "pacparser_parse_pac_string failed\n");
        pacparser_cleanup();
        return 1;
    }

    /* Find proxy for a test URL */
    char *proxy = pacparser_find_proxy("http://www.example.com", "www.example.com");
    if (proxy == NULL) {
        fprintf(stderr, "pacparser_find_proxy returned NULL\n");
        pacparser_cleanup();
        return 1;
    }

    /* Verify the result */
    if (strstr(proxy, "DIRECT") == NULL) {
        fprintf(stderr, "Expected DIRECT, got: %s\n", proxy);
        pacparser_cleanup();
        return 1;
    }

    printf("pacparser test passed: %s\n", proxy);
    pacparser_cleanup();
    return 0;
}
