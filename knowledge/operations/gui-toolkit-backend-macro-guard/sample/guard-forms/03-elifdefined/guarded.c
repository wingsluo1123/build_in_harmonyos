/* 形态 #3：#elif defined(M) —— 多后端链式分支里的守卫，必须有守卫命中（WARN，非 HARD） */
#include <gtk/gtk.h>

#if defined(GDK_WINDOWING_BROADWAY)
/* broadway 后端：无 X11 抓键能力 */
#elif defined(GDK_WINDOWING_X11)
#include <gdk/gdkx.h>
#endif

int guard_form_elifdefined(void);
int guard_form_elifdefined(void) { return 0; }
