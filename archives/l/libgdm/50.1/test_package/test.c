/* test_package smoke test for libgdm 50.1 (HarmonyOS PC).
 * Calls the real libgdm public API and verifies the library links and runs.
 * gdm-client.h is installed under include/gdm (upstream convention). */
#include <gdm/gdm-client.h>
#include <gio/gio.h>
#include <stdio.h>

int
main (void)
{
        GdmClient *client;

        client = gdm_client_new ();
        if (client == NULL) {
                fprintf (stderr, "libgdm smoke: gdm_client_new() returned NULL\n");
                return 1;
        }

        printf ("libgdm 50.1 smoke: gdm_client_new() OK\n");
        g_object_unref (client);
        return 0;
}
