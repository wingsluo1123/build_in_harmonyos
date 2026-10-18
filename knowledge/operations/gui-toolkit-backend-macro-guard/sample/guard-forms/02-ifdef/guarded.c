/* 形态 #2：#ifdef M —— 工具包自身写法（gtk/gtkplug.h:34 就是 #ifdef GDK_WINDOWING_X11），
 * 与 #if defined(M) 语义等价，必须有守卫命中（WARN，非 HARD）。 */
#include <gtk/gtk.h>

#ifdef GDK_WINDOWING_X11
#include <gdk/gdkx.h>
#endif

int guard_form_ifdef(void);
int guard_form_ifdef(void) { return 0; }
