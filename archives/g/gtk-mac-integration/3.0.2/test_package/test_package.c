#include <gtkmacintegration/gtkosxapplication.h>

#include <glib.h>

int main(void)
{
    GtkosxApplication *app = gtkosx_application_get();
    if (app == NULL) {
        return 1;
    }

    gtkosx_application_set_use_quartz_accelerators(app, TRUE);
    if (!gtkosx_application_use_quartz_accelerators(app)) {
        return 2;
    }

    gchar *resource_path = gtkosx_application_get_resource_path();
    if (resource_path == NULL || resource_path[0] == '\0') {
        g_free(resource_path);
        return 3;
    }
    g_free(resource_path);
    return 0;
}
