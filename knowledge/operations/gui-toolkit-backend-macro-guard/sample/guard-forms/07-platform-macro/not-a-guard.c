/* 形态 #7（反模式）：用平台名 __OHOS__ 当守卫，不是工具包发布的后端宏。
 * 同一份源码在其它 broadway/Wayland-only 平台照样坏 → 检测器必须判 HARD
 * （另有一条 WARN platform-macro-guard 记录这个反模式）。 */
#include <gtk/gtk.h>

#ifdef __OHOS__
#include <gdk/gdkx.h>
#endif

int guard_form_platform_macro(void);
int guard_form_platform_macro(void) { return 0; }
