#include <gtk/gtk.h>
#include <gdk/gdk.h>
#include <stdio.h>

/* 3.24.43.1 为 X11 后端变体：GDK_WINDOWING_X11 必须由 gdkconfig.h 定义。
 * 未定义说明构建回落到 broadway-only —— 正是 3.24.43 无法满足 X11 消费者的原因。 */
#ifndef GDK_WINDOWING_X11
#error "GDK_WINDOWING_X11 not defined: this build lacks the X11 backend"
#endif

#include <gdk/gdkx.h>

int main(int argc, char *argv[]) {
    // R34: must call tested package API, not just print string
    // Verify GTK version API (no display needed)
    unsigned int major = gtk_get_major_version();
    unsigned int minor = gtk_get_minor_version();
    unsigned int micro = gtk_get_micro_version();
    printf("GTK %u.%u.%u\n", major, minor, micro);
    // Verify GDK API
    const char *ver = gtk_check_version(3, 24, 43);
    if (ver != NULL) {
        fprintf(stderr, "gtk_check_version failed: %s\n", ver);
        return 1;
    }
    // Verify GObject type system initialized via gtk
    GType t = gtk_widget_get_type();
    if (t == 0) {
        fprintf(stderr, "gtk_widget_get_type failed\n");
        return 1;
    }
    printf("gtk_widget type: %lu\n", (unsigned long)t);

    // X11 后端实质验证：gdk_x11_display_get_type 只在 X11 后端编入 libgdk-3
    // 时存在，缺失会在链接期直接失败（比头文件检查更强的适配完整性证据）。
    GType x11_display_type = gdk_x11_display_get_type();
    if (x11_display_type == 0) {
        fprintf(stderr, "gdk_x11_display_get_type failed (X11 backend missing?)\n");
        return 1;
    }
    printf("gdk_x11_display type: %lu\n", (unsigned long)x11_display_type);
    printf("test GTK 3.24.43.1 (X11 backend): OK\n");
    return 0;
}
