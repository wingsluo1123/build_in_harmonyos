/* test_package/test.c — libxfce4ui consumer smoke (no display needed). */
#include <libxfce4ui/libxfce4ui.h>
#include <glib-object.h>
#include <stdio.h>

int main(void)
{
    /* 1. version macros: headers must report 4.20.0. */
    printf("libxfce4ui version: %d.%d.%d\n",
           LIBXFCE4UI_MAJOR_VERSION, LIBXFCE4UI_MINOR_VERSION,
           LIBXFCE4UI_MICRO_VERSION);
    if (LIBXFCE4UI_MAJOR_VERSION != 4 || LIBXFCE4UI_MINOR_VERSION != 20) {
        printf("FAIL: unexpected version %d.%d\n",
               LIBXFCE4UI_MAJOR_VERSION, LIBXFCE4UI_MINOR_VERSION);
        return 1;
    }

    /* 2. GType registration round-trip: xfce_titled_dialog_get_type()
     * registers the XfceTitledDialog class on first call — exercises the
     * GObject class_init chain (and the gtk/libxfce4util linkage)
     * without creating a window. */
    GType t = xfce_titled_dialog_get_type();
    if (t == 0) {
        printf("FAIL: xfce_titled_dialog_get_type() == 0\n");
        return 1;
    }
    printf("XfceTitledDialog GType: %lu\n", (unsigned long) t);

    /* 3. version check macro consistency. */
    if (!LIBXFCE4UI_CHECK_VERSION(4, 20, 0)) {
        printf("FAIL: CHECK_VERSION(4,20,0) false\n");
        return 1;
    }

    printf("ok: libxfce4ui loaded, version 4.20.0, GType round-trip\n");
    return 0;
}
