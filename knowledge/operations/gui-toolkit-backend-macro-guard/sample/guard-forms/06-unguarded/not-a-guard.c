/* 形态 #6（基线）：完全无守卫，无条件 include 后端专用头。检测器必须判 HARD。 */
#include <gtk/gtk.h>
#include <gdk/gdkx.h>

int guard_form_unguarded(void);
int guard_form_unguarded(void)
{
    return GDK_DISPLAY_XDISPLAY(gdk_display_get_default()) != 0;
}
