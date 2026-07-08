#include <stdio.h>
#include <stdlib.h>
#include <libserdes/serdes.h>

int main(void) {
    /* Simple smoke test: call serdes_err2str which doesn't require network */
    const char *errstr = serdes_err2str(SERDES_ERR_OK);
    if (errstr != NULL) {
        printf("test libserdes 8.3.0: OK (err2str=%s)\n", errstr);
        return 0;
    }
    fprintf(stderr, "test libserdes 8.3.0: FAIL (err2str returned NULL)\n");
    return 1;
}
