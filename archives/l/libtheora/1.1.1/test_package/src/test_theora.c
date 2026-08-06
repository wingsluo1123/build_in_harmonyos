/* Test program for libtheora package verification.
 * Calls theora_version_string() to verify the library is correctly linked.
 */
#include <stdio.h>
#include <theora/theora.h>

int main(void) {
    const char *ver = theora_version_string();
    printf("libtheora version: %s\n", ver);

    /* Initialize a theora_info struct to verify API symbols are present */
    theora_info info;
    theora_info_init(&info);
    theora_info_clear(&info);

    printf("theora_info_init/clear: OK\n");
    return 0;
}
