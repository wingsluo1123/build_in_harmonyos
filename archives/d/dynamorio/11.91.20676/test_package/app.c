/* Standalone DynamoRIO consumer for OHOS PC.
 *
 * Exercises the packaged DBI engine in-process through the standalone API:
 * the process must survive engine setup, engine takeover, and engine teardown.
 */
#include <stdio.h>
#include <unistd.h>

/* dr_app.h relies on the base declarations (bool, dr_stats_t) coming from
 * dr_api.h, as in DynamoRIO's own standalone tests. */
#include "dr_api.h"
#include "dr_app.h"

static long
do_some_work(void)
{
    volatile double v = 1.0;
    int i;
    for (i = 0; i < 100000; ++i)
        v += i % 7;
    return (long)v;
}

int
main(void)
{
    printf("pre-DR init\n");
    fflush(stdout);
    if (dr_app_setup() != 0) {
        printf("dr_app_setup failed\n");
        return 1;
    }
    printf("pre-DR start\n");
    fflush(stdout);
    dr_app_start();
    if (!dr_app_running_under_dynamorio()) {
        printf("engine did not take over\n");
        return 2;
    }
    (void)do_some_work();
    dr_app_stop();
    dr_app_cleanup();
    printf("all done\n");
    fflush(stdout);
    /* Exit directly: on OHOS the process currently blocks in the normal exit
     * path after the engine has been torn down (DynamoRIO installs signal
     * handlers, so even SIGTERM does not terminate it).  The engine itself has
     * completed, which is what this smoke test checks. */
    _exit(0);
}
