/* 形态 #5（反义）：#if !defined(M) —— 与 #ifndef 等价，不是守卫。检测器必须判 HARD。 */
#include <gtk/gtk.h>

#if !defined(GDK_WINDOWING_X11)
#include <gdk/gdkx.h>
#endif

int guard_form_not_defined(void);
int guard_form_not_defined(void) { return 0; }
