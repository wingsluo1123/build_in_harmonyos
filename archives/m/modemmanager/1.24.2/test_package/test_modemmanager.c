#include <stdio.h>
#include <string.h>

#include <glib.h>
#include <ModemManager.h>
#include <libmm-glib.h>

/* Consumer-side smoke test for the libmm-glib package (modemmanager 1.24.2).
 *
 * The ModemManager daemon is not built for HarmonyOS PC (no D-Bus system bus
 * / udev / systemd), so this verifies what a client application consumes:
 * the installed headers, the type registrations of the core Mm* objects, the
 * enum values shared with the daemon and the version macros of the package.
 */

int main(void)
{
    int failures = 0;

    /* 1-7: core object type registrations (GType system) */
    GType types[] = {
        mm_modem_get_type(),
        mm_manager_get_type(),
        mm_object_get_type(),
        mm_sim_get_type(),
        mm_bearer_get_type(),
        mm_sms_get_type(),
        mm_call_get_type(),
    };
    const char *names[] = {
        "mm_modem_get_type", "mm_manager_get_type", "mm_object_get_type",
        "mm_sim_get_type", "mm_bearer_get_type", "mm_sms_get_type",
        "mm_call_get_type",
    };
    for (unsigned i = 0; i < sizeof(types) / sizeof(types[0]); i++) {
        if (types[i] == 0) {
            fprintf(stderr, "FAIL: %s returned GType 0\n", names[i]);
            failures++;
        } else {
            g_print("PASS: %s = %lu (%s)\n", names[i], (unsigned long) types[i], g_type_name(types[i]));
        }
    }

    /* 8: enum value shared with the daemon (ModemManager-enums.h) */
    if (MM_MODEM_STATE_REGISTERED == 8) {
        g_print("PASS: MM_MODEM_STATE_REGISTERED == 8\n");
    } else {
        fprintf(stderr, "FAIL: MM_MODEM_STATE_REGISTERED == %d\n", (int) MM_MODEM_STATE_REGISTERED);
        failures++;
    }

    /* 9-11: version macros of the packaged release (ModemManager-version.h) */
    if (MM_MAJOR_VERSION == 1 && MM_MINOR_VERSION == 24 && MM_MICRO_VERSION == 2) {
        g_print("PASS: MM_VERSION = %d.%d.%d\n", MM_MAJOR_VERSION, MM_MINOR_VERSION, MM_MICRO_VERSION);
    } else {
        fprintf(stderr, "FAIL: MM_VERSION = %d.%d.%d\n", MM_MAJOR_VERSION, MM_MINOR_VERSION, MM_MICRO_VERSION);
        failures++;
    }
    if (MM_CHECK_VERSION(1, 24, 2)) {
        g_print("PASS: MM_CHECK_VERSION(1, 24, 2)\n");
    } else {
        fprintf(stderr, "FAIL: MM_CHECK_VERSION(1, 24, 2)\n");
        failures++;
    }
    if (!MM_CHECK_VERSION(1, 24, 3)) {
        g_print("PASS: !MM_CHECK_VERSION(1, 24, 3)\n");
    } else {
        fprintf(stderr, "FAIL: MM_CHECK_VERSION(1, 24, 3) unexpectedly true\n");
        failures++;
    }

    /* 12: error domain registration (mm-errors-types, mm_core_error_quark) */
    {
        GQuark quark = mm_core_error_quark();
        if (quark != 0) {
            g_print("PASS: mm_core_error_quark = %u\n", (unsigned) quark);
        } else {
            fprintf(stderr, "FAIL: mm_core_error_quark returned 0\n");
            failures++;
        }
    }

    /* 13: generated enum type registration (mm-enums-types) */
    {
        GType enum_type = mm_modem_capability_get_type();
        if (enum_type != 0) {
            g_print("PASS: mm_modem_capability_get_type = %lu\n", (unsigned long) enum_type);
        } else {
            fprintf(stderr, "FAIL: mm_modem_capability_get_type returned 0\n");
            failures++;
        }
    }

    if (failures == 0) {
        g_print("ALL %d CHECKS PASSED\n", 13);
        return 0;
    }
    g_print("TEST_FAILURE (%d failed)\n", failures);
    return 1;
}
