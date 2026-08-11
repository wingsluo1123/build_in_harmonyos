/* Consumer smoke test for gtk/3.24.38.
 *
 * Genuinely links against libgtk-3 / libgdk-3 and calls GTK+ API:
 *  - version query functions (gtk_get_major_version etc.)
 *  - gtk_init_check()  — returns FALSE on a headless host (no broadway
 *    server), which is the expected behaviour here and must not crash.
 *  - widget construction (GtkLabel) to exercise GObject type registration.
 */
#include <gtk/gtk.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    guint major = gtk_get_major_version();
    guint minor = gtk_get_minor_version();
    guint micro = gtk_get_micro_version();

    printf("gtk %u.%u.%u\n", major, minor, micro);

    if (major != 3 || minor != 24) {
        fprintf(stderr, "unexpected gtk version %u.%u.%u\n", major, minor, micro);
        return 1;
    }

    /* headless: expected to be FALSE on this build host, but must not abort */
    if (gtk_init_check(NULL, NULL)) {
        printf("gtk_init_check: display available\n");
    } else {
        printf("gtk_init_check: no display (expected on headless OHOS)\n");
    }

    GtkWidget *label = gtk_label_new("hello from conan gtk");
    if (!GTK_IS_LABEL(label)) {
        fprintf(stderr, "gtk_label_new returned a non-label widget\n");
        return 1;
    }
    g_object_ref_sink(G_OBJECT(label));
    g_object_unref(G_OBJECT(label));

    printf("gtk smoke test OK\n");
    return 0;
}
