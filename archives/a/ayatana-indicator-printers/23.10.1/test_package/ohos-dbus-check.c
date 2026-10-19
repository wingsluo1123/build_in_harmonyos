/*
 * ohos-dbus-check.c — D-Bus peer used by the ayatana-indicator-printers
 * test_package on HarmonyOS.
 *
 * The printers indicator is a D-Bus daemon: it subscribes to the CUPS
 * notification interface (org.cups.cupsd.Notifier) on the system bus and
 * exports its indicator menu (org.gtk.Actions / org.gtk.Menus) on the session
 * bus. This helper provides both sides of that conversation against the
 * private test buses started by test.sh:
 *
 *   probe  <bus-address> <bus-name> <object-path> <interface>...
 *       Connects to <bus-address>, asks the bus daemon whether <bus-name> has
 *       an owner and introspects <object-path> on it. Exits 0 only when the
 *       name is owned and every listed interface is exported by that object.
 *
 *   notify <bus-address>
 *       Connects to <bus-address>, claims org.cups.cupsd.Notifier and emits
 *       PrinterStateChanged — i.e. plays the CUPS notification peer the
 *       daemon subscribes to.
 */
#include <gio/gio.h>
#include <stdio.h>
#include <string.h>

static GDBusConnection *open_bus (const gchar *address, GError **error)
{
    return g_dbus_connection_new_for_address_sync (
        address,
        G_DBUS_CONNECTION_FLAGS_AUTHENTICATION_CLIENT |
            G_DBUS_CONNECTION_FLAGS_MESSAGE_BUS_CONNECTION,
        NULL, NULL, error);
}

static gint probe (const gchar *address, const gchar *name, const gchar *path,
                   gint n_interfaces, const gchar *const *interfaces)
{
    GError *error = NULL;
    GDBusConnection *connection = open_bus (address, &error);

    if (!connection)
    {
        fprintf (stderr, "[probe] cannot connect to %s: %s\n", address, error->message);
        g_clear_error (&error);
        return 1;
    }

    GVariant *reply = g_dbus_connection_call_sync (
        connection, "org.freedesktop.DBus", "/org/freedesktop/DBus",
        "org.freedesktop.DBus", "NameHasOwner", g_variant_new ("(s)", name),
        G_VARIANT_TYPE ("(b)"), G_DBUS_CALL_FLAGS_NONE, 10000, NULL, &error);

    if (!reply)
    {
        fprintf (stderr, "[probe] NameHasOwner(%s) failed: %s\n", name, error->message);
        g_clear_error (&error);
        g_object_unref (connection);
        return 1;
    }

    gboolean owned = FALSE;
    g_variant_get (reply, "(b)", &owned);
    g_variant_unref (reply);
    printf ("[probe] NameHasOwner(%s) = %s\n", name, owned ? "true" : "false");

    if (!owned)
    {
        g_object_unref (connection);
        return 1;
    }

    reply = g_dbus_connection_call_sync (
        connection, name, path, "org.freedesktop.DBus.Introspectable",
        "Introspect", NULL, G_VARIANT_TYPE ("(s)"), G_DBUS_CALL_FLAGS_NONE,
        10000, NULL, &error);

    if (!reply)
    {
        fprintf (stderr, "[probe] Introspect(%s%s) failed: %s\n", name, path, error->message);
        g_clear_error (&error);
        g_object_unref (connection);
        return 1;
    }

    const gchar *xml = NULL;
    g_variant_get (reply, "(&s)", &xml);

    gint missing = 0;

    for (gint i = 0; i < n_interfaces; i++)
    {
        if (strstr (xml, interfaces[i]))
        {
            printf ("[probe] %s exports %s\n", path, interfaces[i]);
        }
        else
        {
            printf ("[probe] %s does NOT export %s\n", path, interfaces[i]);
            missing++;
        }
    }

    g_variant_unref (reply);
    g_object_unref (connection);
    return missing == 0 ? 0 : 1;
}

static gint notify (const gchar *address)
{
    GError *error = NULL;
    GDBusConnection *connection = open_bus (address, &error);

    if (!connection)
    {
        fprintf (stderr, "[notify] cannot connect to %s: %s\n", address, error->message);
        g_clear_error (&error);
        return 1;
    }

    GVariant *reply = g_dbus_connection_call_sync (
        connection, "org.freedesktop.DBus", "/org/freedesktop/DBus",
        "org.freedesktop.DBus", "RequestName",
        g_variant_new ("(su)", "org.cups.cupsd.Notifier", 0u),
        G_VARIANT_TYPE ("(u)"), G_DBUS_CALL_FLAGS_NONE, 10000, NULL, &error);

    if (!reply)
    {
        fprintf (stderr, "[notify] RequestName(org.cups.cupsd.Notifier) failed: %s\n",
                 error->message);
        g_clear_error (&error);
        g_object_unref (connection);
        return 1;
    }

    g_variant_unref (reply);
    printf ("[notify] claimed org.cups.cupsd.Notifier as %s\n",
            g_dbus_connection_get_unique_name (connection));

    /* Same argument list as the upstream org.cups.cupsd.Notifier XML:
     * text (s), printer_uri (s), printer_name (s), printer_state (u),
     * printer_state_reasons (s), printer_is_accepting_jobs (b). */
    gboolean emitted = g_dbus_connection_emit_signal (
        connection, NULL, "/org/cups/cupsd/Notifier", "org.cups.cupsd.Notifier",
        "PrinterStateChanged",
        g_variant_new ("(sssusb)", "Printer state changed!", "ipp://localhost/printers/test",
                       "test-printer", 5u, "toner-low", FALSE),
        &error);

    if (!emitted)
    {
        fprintf (stderr, "[notify] emit PrinterStateChanged failed: %s\n", error->message);
        g_clear_error (&error);
        g_object_unref (connection);
        return 1;
    }

    printf ("[notify] emitted org.cups.cupsd.Notifier.PrinterStateChanged\n");
    g_object_unref (connection);
    return 0;
}

int main (int argc, char **argv)
{
    if (argc >= 5 && strcmp (argv[1], "probe") == 0)
    {
        return probe (argv[2], argv[3], argv[4], argc - 5, (const gchar *const *) &argv[5]);
    }

    if (argc == 3 && strcmp (argv[1], "notify") == 0)
    {
        return notify (argv[2]);
    }

    fprintf (stderr,
             "usage: %s probe <bus-address> <bus-name> <object-path> <interface>...\n"
             "       %s notify <bus-address>\n",
             argv[0], argv[0]);
    return 2;
}
