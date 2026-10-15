/* test_detect_degraded.c — verifies the declared §3.6 degraded scope.
 *
 * The only API this port degrades is gweather_location_detect_nearest_city(),
 * whose upstream implementation needs geocode-glib.  Without geocode-glib the
 * symbol must still be exported, must still honour the documented async
 * contract (callback fires, finish returns NULL, error is
 * G_IO_ERROR_NOT_SUPPORTED) rather than crash or link-fail.
 */
#include <glib-object.h>
/* See test_libgweather4.c: the package installs headers under
 * include/libgweather-4.0/libgweather/. */
#include <libgweather/gweather.h>
#include <stdio.h>

typedef struct {
    int called;
    GWeatherLocation *result;
    GError *error;
} Probe;

static void
on_done (GObject *source, GAsyncResult *res, gpointer user_data)
{
    Probe *p = (Probe *) user_data;
    (void) source;

    p->called = 1;
    p->result = gweather_location_detect_nearest_city_finish (res, &p->error);
}

int
main (void)
{
    GWeatherLocation *world;
    Probe p = { 0, NULL, NULL };
    int rc = 0;

    world = gweather_location_get_world ();
    if (world == NULL) {
        printf ("FAIL - world location unavailable, cannot test degraded API\n");
        return 1;
    }

    printf ("# degraded-scope check: gweather_location_detect_nearest_city\n");

    gweather_location_detect_nearest_city (world, 51.5072, -0.1276,
                                           NULL, on_done, &p);

    /* the stub completes the task inline, so a short bounded wait is enough */
    for (int i = 0; i < 200 && !p.called; i++)
        g_main_context_iteration (NULL, FALSE);

    if (!p.called) {
        printf ("FAIL - callback never fired for the degraded async API\n");
        rc = 1;
        goto out;
    }
    printf ("ok   - async callback fired\n");

    if (p.result != NULL) {
        printf ("FAIL - expected NULL location, got '%s'\n",
                gweather_location_get_name (p.result));
        rc = 1;
    } else {
        printf ("ok   - finish() returned NULL as documented\n");
    }

    if (p.error == NULL) {
        printf ("FAIL - expected a GError, got none\n");
        rc = 1;
    } else if (!g_error_matches (p.error, G_IO_ERROR, G_IO_ERROR_NOT_SUPPORTED)) {
        /* g_quark_to_string() rather than g_error_domain(): the latter is only
         * declared under some header/feature combinations and would come out a
         * warning here plus an undefined-symbol link error. */
        printf ("FAIL - expected G_IO_ERROR_NOT_SUPPORTED, got %s: %s\n",
                g_quark_to_string (p.error->domain), p.error->message);
        rc = 1;
    } else {
        printf ("ok   - error is G_IO_ERROR_NOT_SUPPORTED (%s)\n", p.error->message);
    }

out:
    g_clear_error (&p.error);
    g_clear_object (&p.result);
    g_object_unref (world);
    return rc;
}
