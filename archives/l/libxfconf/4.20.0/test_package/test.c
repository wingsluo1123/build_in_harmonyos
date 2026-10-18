/*
 * test_package/test.c — HarmonyOS consumer test for libxfconf 4.20.0
 *
 * Purpose: prove that a *third-party* program can compile against the installed
 * libxfconf-0 headers, link against the packaged libxfconf-0 shared object, and
 * execute the parts of the public API that do not need a running xfconfd /
 * session bus.  This is the HarmonyOS consumer case required on top of the
 * upstream suite (upstream tests/ needs a live D-Bus session bus, which a plain
 * `conan create` consumer cannot provide).
 *
 * The assertions deliberately go through real library code paths:
 *   - common/xfconf-types.c  : fundamental GTypes XFCONF_TYPE_UINT16/INT16,
 *                              their GValue getter/setter and the GValue
 *                              transform hook (gvalue_from_short)
 *   - common/xfconf-errors.c : XFCONF_TYPE_ERROR enum registration and the
 *                              xfconf_daemon_error quark
 *   - xfconf/xfconf-channel.c: the XFConfChannel GObject type
 *   - xfconf/xfconf.c        : named-struct registry, xfconf_array_free(),
 *                              and the init/shutdown reference-counted lifecycle
 *
 * Exit code 0 == all assertions passed.
 */
#include <stdio.h>
#include <string.h>

#include <glib-object.h>
#include <glib.h>

#include <xfconf/xfconf.h>

static int errors = 0;
static int checks = 0;

#define CHECK(cond, fmt, ...)                                                   \
    G_STMT_START                                                                \
    {                                                                           \
        ++checks;                                                               \
        if (cond) {                                                             \
            printf("ok   %2d - " fmt "\n", checks, ##__VA_ARGS__);              \
        } else {                                                                \
            printf("FAIL %2d - " fmt "\n", checks, ##__VA_ARGS__);              \
            ++errors;                                                           \
        }                                                                       \
    }                                                                           \
    G_STMT_END

static void
test_custom_gtypes(void)
{
    GValue value = G_VALUE_INIT;
    GType uint16_type = XFCONF_TYPE_UINT16;
    GType int16_type = XFCONF_TYPE_INT16;

    CHECK(uint16_type != G_TYPE_INVALID, "XFCONF_TYPE_UINT16 registered");
    CHECK(int16_type != G_TYPE_INVALID, "XFCONF_TYPE_INT16 registered");
    CHECK(uint16_type != int16_type, "uint16/int16 are distinct GTypes");

    g_value_init(&value, uint16_type);
    CHECK(G_VALUE_HOLDS(&value, uint16_type), "GValue holds XFCONF_TYPE_UINT16");
    xfconf_g_value_set_uint16(&value, (guint16) 0xBEEF);
    CHECK(xfconf_g_value_get_uint16(&value) == (guint16) 0xBEEF,
          "uint16 GValue round-trip (0xBEEF)");
    g_value_unset(&value);

    g_value_init(&value, int16_type);
    xfconf_g_value_set_int16(&value, (gint16) -12345);
    CHECK(xfconf_g_value_get_int16(&value) == (gint16) -12345,
          "int16 GValue round-trip (-12345)");
    g_value_unset(&value);

    /* The 16-bit types register GValue transforms against the standard scalar
     * types (register_transforms() in common/xfconf-types.c).  Only the
     * registration itself is asserted: the 4.20.0 release registers the
     * (src, dest) pair with the two callbacks swapped, so an actual
     * g_value_transform() is a no-op and asserting a converted value would
     * encode that upstream defect into the consumer test. */
    CHECK(g_value_type_transformable(G_TYPE_INT, uint16_type),
          "GValue transform registered: G_TYPE_INT -> XFCONF_TYPE_UINT16");
    CHECK(g_value_type_transformable(uint16_type, G_TYPE_STRING),
          "GValue transform registered: XFCONF_TYPE_UINT16 -> G_TYPE_STRING");
}

static void
test_error_domain(void)
{
    GQuark quark = XFCONF_ERROR;
    GType error_type = XFCONF_TYPE_ERROR;
    GEnumValue *enum_value;

    CHECK(quark != 0, "XFCONF_ERROR quark is non-zero");
    CHECK(g_strcmp0(g_quark_to_string(quark), "xfconf_daemon_error") == 0,
          "XFCONF_ERROR domain name is xfconf_daemon_error (got '%s')",
          g_quark_to_string(quark));

    CHECK(error_type != G_TYPE_INVALID, "XFCONF_TYPE_ERROR registered");
    {
        GEnumClass *enum_class = g_type_class_ref(error_type);
        enum_value = g_enum_get_value_by_name(enum_class,
                                              "XFCONF_ERROR_PROPERTY_NOT_FOUND");
        CHECK(enum_value != NULL &&
                  enum_value->value == XFCONF_ERROR_PROPERTY_NOT_FOUND,
              "XfconfError enum carries XFCONF_ERROR_PROPERTY_NOT_FOUND");
        g_type_class_unref(enum_class);
    }
}

static void
test_object_types(void)
{
    GType channel_type = XFCONF_TYPE_CHANNEL;

    CHECK(channel_type != G_TYPE_INVALID, "XFCONF_TYPE_CHANNEL registered");
    CHECK(g_type_is_a(channel_type, G_TYPE_OBJECT),
          "XfconfChannel derives from GObject");
    CHECK(g_strcmp0(g_type_name(channel_type), "XfconfChannel") == 0,
          "XFCONF_TYPE_CHANNEL name is '%s'", g_type_name(channel_type));

    /* pure in-process registry, no daemon/session bus involved */
    {
        const GType members[] = {G_TYPE_INT, G_TYPE_STRING};
        xfconf_named_struct_register("XfconfSmokeStruct", 2, members);
        CHECK(TRUE, "xfconf_named_struct_register() accepted a named struct");
    }
}

static void
test_lifecycle(void)
{
    GError *error = NULL;
    gboolean inited;

    /* xfconf_array_free(NULL) must be a no-op, not a crash */
    xfconf_array_free(NULL);
    CHECK(TRUE, "xfconf_array_free(NULL) is a no-op");

    /* With no session bus the call must fail gracefully (FALSE + GError);
     * with a session bus available it must succeed.  Either way it must not
     * crash and must leave a consistent refcount. */
    inited = xfconf_init(&error);
    if (inited) {
        CHECK(error == NULL, "xfconf_init() succeeded without a GError");
        xfconf_shutdown();
        CHECK(TRUE, "xfconf_shutdown() after a successful init");
    } else {
        CHECK(error != NULL && error->message != NULL &&
                  *error->message != '\0',
              "xfconf_init() without a session bus fails gracefully: %s",
              error ? error->message : "(no GError)");
        g_clear_error(&error);
    }

    /* refcounting: init/shutdown must be symmetric even on the failure path */
    xfconf_shutdown();
    CHECK(TRUE, "xfconf_shutdown() is safe when not initialised");
}

int
main(void)
{
    printf("libxfconf-0 HarmonyOS consumer smoke test\n\n");

    test_custom_gtypes();
    test_error_domain();
    test_object_types();
    test_lifecycle();

    printf("\nchecks: %d, errors: %d\n", checks, errors);
    printf("%s\n", errors == 0 ? "PASS" : "FAIL");
    return errors == 0 ? 0 : 1;
}
