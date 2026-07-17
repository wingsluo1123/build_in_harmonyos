#include "gtkosxapplication.h"

#include <glib.h>

struct _GtkosxApplication {
    GObject parent_instance;
    gboolean use_quartz_accelerators;
};

struct _GtkosxApplicationClass {
    GObjectClass parent_class;
};

G_DEFINE_TYPE(GtkosxApplication, gtkosx_application, G_TYPE_OBJECT)

static void gtkosx_application_class_init(GtkosxApplicationClass *klass)
{
    (void)klass;
}

static void gtkosx_application_init(GtkosxApplication *self)
{
    self->use_quartz_accelerators = FALSE;
}

GtkosxApplication *gtkosx_application_get(void)
{
    static gsize instance_value;

    if (g_once_init_enter(&instance_value)) {
        GtkosxApplication *instance = g_object_new(GTKOSX_TYPE_APPLICATION, NULL);
        g_once_init_leave(&instance_value, (gsize)instance);
    }
    return (GtkosxApplication *)instance_value;
}

void gtkosx_application_ready(GtkosxApplication *self)
{
    (void)self;
}

void gtkosx_application_set_use_quartz_accelerators(
    GtkosxApplication *self, gboolean enabled
)
{
    if (self != NULL) {
        self->use_quartz_accelerators = enabled;
    }
}

gboolean gtkosx_application_use_quartz_accelerators(GtkosxApplication *self)
{
    return self != NULL && self->use_quartz_accelerators;
}

#define GTKOSX_NOOP_1(name, type1) \
    void name(GtkosxApplication *self, type1 value) \
    { \
        (void)self; \
        (void)value; \
    }

GTKOSX_NOOP_1(gtkosx_application_set_menu_bar, GtkMenuShell *)
GTKOSX_NOOP_1(gtkosx_application_set_about_item, GtkWidget *)
GTKOSX_NOOP_1(gtkosx_application_set_window_menu, GtkMenuItem *)
GTKOSX_NOOP_1(gtkosx_application_set_help_menu, GtkMenuItem *)
GTKOSX_NOOP_1(gtkosx_application_set_dock_menu, GtkMenuShell *)
GTKOSX_NOOP_1(gtkosx_application_set_dock_icon_pixbuf, GdkPixbuf *)

void gtkosx_application_sync_menubar(GtkosxApplication *self)
{
    (void)self;
}

void gtkosx_application_insert_app_menu_item(
    GtkosxApplication *self, GtkWidget *menu_item, gint index
)
{
    (void)self;
    (void)menu_item;
    (void)index;
}

void gtkosx_application_set_dock_icon_resource(
    GtkosxApplication *self,
    const gchar *name,
    const gchar *type,
    const gchar *subdir
)
{
    (void)self;
    (void)name;
    (void)type;
    (void)subdir;
}

gint gtkosx_application_attention_request(
    GtkosxApplication *self, GtkosxApplicationAttentionType type
)
{
    (void)self;
    (void)type;
    return 0;
}

void gtkosx_application_cancel_attention_request(
    GtkosxApplication *self, gint id
)
{
    (void)self;
    (void)id;
}

gchar *gtkosx_application_get_bundle_path(void)
{
    return g_get_current_dir();
}

gchar *gtkosx_application_get_resource_path(void)
{
    return g_strdup(g_get_user_data_dir());
}

gchar *gtkosx_application_get_executable_path(void)
{
    gchar *path = g_file_read_link("/proc/self/exe", NULL);
    if (path == NULL) {
        const gchar *name = g_get_prgname();
        path = g_strdup(name != NULL ? name : "");
    }
    return path;
}

gchar *gtkosx_application_get_bundle_id(void)
{
    return NULL;
}

gchar *gtkosx_application_get_bundle_info(const gchar *key)
{
    (void)key;
    return NULL;
}
