#include <stdio.h>
#include <gdk-pixbuf/gdk-pixbuf.h>

int main(void) {
    GdkPixbuf *pixbuf = gdk_pixbuf_new(GDK_COLORSPACE_RGB, FALSE, 8, 1, 1);
    if (pixbuf == NULL) {
        fprintf(stderr, "FAIL: gdk_pixbuf_new returned NULL\n");
        return 1;
    }
    printf("gdk-pixbuf version: %s\n", GDK_PIXBUF_VERSION);
    printf("test gdk-pixbuf 2.42.12: OK\n");
    g_object_unref(pixbuf);
    return 0;
}
