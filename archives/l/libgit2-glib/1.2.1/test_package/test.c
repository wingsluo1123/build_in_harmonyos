#include <glib.h>
#include <git2.h>
#include <libgit2-glib/ggit.h>
#include <stdio.h>

int main(void) {
    /* Initialize libgit2 */
    git_libgit2_init();

    /* Initialize libgit2-glib */
    ggit_init();

    /* Get libgit2 version */
    int major, minor, rev;
    git_libgit2_version(&major, &minor, &rev);
    printf("libgit2 version: %d.%d.%d\n", major, minor, rev);

    /* Get GLib version */
    printf("glib version: %d.%d.%d\n", glib_major_version, glib_minor_version, glib_micro_version);

    /* Shutdown libgit2 */
    git_libgit2_shutdown();
    return 0;
}
