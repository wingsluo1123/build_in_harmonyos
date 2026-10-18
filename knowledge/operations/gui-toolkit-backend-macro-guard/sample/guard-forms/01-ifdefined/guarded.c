/* 形态 #1：#if defined(M) —— 最常见的守卫写法，必须有守卫命中（WARN，非 HARD） */
#include <gtk/gtk.h>

#if defined(GDK_WINDOWING_X11)
#include <gdk/gdkx.h>
#endif

int guard_form_ifdefined(void);
int guard_form_ifdefined(void) { return 0; }
