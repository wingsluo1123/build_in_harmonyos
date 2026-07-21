#include <string.h>

#include <spice-client.h>
#include <spice-client-gtk.h>

int main(void)
{
    const char *version = spice_util_get_version_string();
    if (version == NULL || strstr(version, "0.42") == NULL) {
        return 1;
    }

    spice_util_set_debug(TRUE);
    if (!spice_util_get_debug()) {
        return 2;
    }
    spice_util_set_debug(FALSE);

    SpiceSession *session = spice_session_new();
    if (!SPICE_IS_SESSION(session)) {
        return 3;
    }

    if (spice_display_get_type() == 0) {
        g_object_unref(session);
        return 4;
    }

    g_object_unref(session);
    return 0;
}
