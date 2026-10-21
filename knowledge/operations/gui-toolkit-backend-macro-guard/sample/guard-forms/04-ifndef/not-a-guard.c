/* 形态 #4（反义）：#ifndef M —— 代码只在宏「未定义」时编译，等于「后端缺失时必炸」，
 * 不是守卫。检测器必须判 HARD。 */
#include <gtk/gtk.h>

#ifndef GDK_WINDOWING_X11
#include <gdk/gdkx.h>
#endif

int guard_form_ifndef(void);
int guard_form_ifndef(void) { return 0; }
