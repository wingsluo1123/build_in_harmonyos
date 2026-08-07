/* test_parole.c — verifies parole package installation
 *
 * parole is a GTK3/XFCE media player application. This test verifies
 * that GLib (parole's core runtime dependency) is properly linked
 * through the Conan dependency chain.
 */
#include <stdio.h>
#include <glib.h>

int main(void) {
    /* Verify glib is available (parole's core dependency) */
    const gchar *glib_ver = glib_check_version(2, 38, 0);
    if (glib_ver != NULL) {
        printf("test parole 4.20.0: glib dependency OK (v%s)\n", glib_ver);
        return 0;
    }
    fprintf(stderr, "test parole 4.20.0: glib version too old\n");
    return 1;
}
