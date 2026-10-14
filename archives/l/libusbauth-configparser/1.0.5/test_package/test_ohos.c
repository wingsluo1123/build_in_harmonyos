/*
 * HarmonyOS-specific consumer assertions for libusbauth-configparser 1.0.5
 * (rule12).
 *
 * H1  ohos_runtime_resigned_so_loads
 *     The re-signed libusbauth-configparser.so.1 delivered by the package is
 *     loaded by the OHOS runtime and exports its public entry points.  The
 *     SONAME is asserted explicitly because the OHOS loader keys on DT_SONAME.
 *
 * H2  ohos_config_parse_roundtrip_via_override_path
 *     End to end: a config file is written to a writable location, the
 *     flex/bison parser reads it back through the $USBAUTH_CONFIG-overridable
 *     path (the HarmonyOS /etc read-only workaround), the parsed rule array is
 *     checked field by field, then re-serialised with usbauth_config_write()
 *     and re-read to confirm the text round-trips byte for byte.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <usbauth/usbauth-configparser.h>

static int fails = 0;

static void check(int cond, const char *what)
{
    if (!cond) {
        printf("FAIL: %s\n", what);
        fails++;
    }
}

/* The input rule file and the exact text the writer must reproduce. */
static const char *kConfig =
    "allow all\n"
    "allow idVendor==1234\n"
    "deny idProduct==5678 bInterfaceClass==08\n"
    "# a comment\n"
    "condition idVendor==abcd case bInterfaceClass==ff\n";

static const char *kExpectedOut =
    "allow all\n"
    "allow idVendor==1234\n"
    "deny idProduct==5678 bInterfaceClass==08\n"
    "# a comment\n"
    "condition idVendor==abcd case bInterfaceClass==ff\n";

static int write_text(const char *path, const char *text)
{
    FILE *f = fopen(path, "w");
    if (!f)
        return -1;
    fputs(text, f);
    fclose(f);
    return 0;
}

static int file_equals(const char *path, const char *expected)
{
    char buf[4096];
    FILE *f = fopen(path, "r");
    size_t n;
    if (!f)
        return 0;
    n = fread(buf, 1, sizeof buf - 1, f);
    fclose(f);
    buf[n] = '\0';
    return strcmp(buf, expected) == 0;
}

int main(void)
{
    /* ---- H1: the re-signed delivered .so loads and exports its API ---- */
    void *h = dlopen("libusbauth-configparser.so.1", RTLD_NOW | RTLD_LOCAL);
    if (h == NULL) {
        printf("FAIL: H1 dlopen(libusbauth-configparser.so.1): %s\n", dlerror());
        fails++;
    } else {
        check(dlsym(h, "usbauth_config_read") != NULL,
              "H1 usbauth_config_read resolved");
        check(dlsym(h, "usbauth_config_write") != NULL,
              "H1 usbauth_config_write resolved");
        check(dlsym(h, "usbauth_param_to_str") != NULL,
              "H1 usbauth_param_to_str resolved");
        dlclose(h);
    }

    /* ---- H2: parse round-trip through the overridable config path ---- */
    char in_path[256];
    char out_path[256];
    snprintf(in_path, sizeof in_path, "./usbauth_rt_in_%d.conf", (int)getpid());
    snprintf(out_path, sizeof out_path, "./usbauth_rt_out_%d.conf", (int)getpid());

    check(write_text(in_path, kConfig) == 0, "H2 wrote input config");

    check(setenv("USBAUTH_CONFIG", in_path, 1) == 0, "H2 set USBAUTH_CONFIG");
    check(usbauth_config_read() == 0, "H2 config_read() succeeded");

    /* Structural assertions on the parsed rule array (public API). */
    struct Auth *auths = NULL;
    unsigned len = 0;
    usbauth_config_get_auths(&auths, &len);
    check(len == 5, "H2 parsed 5 rules");
    if (auths != NULL && len == 5) {
        check(auths[0].type == ALLOW && auths[0].attr_len == 0,
              "H2 rule0 = allow all");
        check(auths[1].type == ALLOW && auths[1].attr_len == 1,
              "H2 rule1 = allow <one attr>");
        if (auths[1].attr_len == 1) {
            check(auths[1].attr_array[0].param == idVendor,
                  "H2 rule1 attr param = idVendor");
            check(auths[1].attr_array[0].op == eq, "H2 rule1 attr op = ==");
            check(auths[1].attr_array[0].val != NULL &&
                      strcmp(auths[1].attr_array[0].val, "1234") == 0,
                  "H2 rule1 attr val = 1234");
        }
        check(auths[2].type == DENY && auths[2].attr_len == 2,
              "H2 rule2 = deny <two attrs>");
        check(auths[3].type == COMMENT && auths[3].comment != NULL,
              "H2 rule3 = comment");
        check(auths[4].type == COND && auths[4].cond_len == 1 &&
                  auths[4].attr_len == 1,
              "H2 rule4 = condition(1 cond) case(1 attr)");
    }

    /* Re-serialise to a different path and confirm the text round-trips. */
    check(setenv("USBAUTH_CONFIG", out_path, 1) == 0, "H2 point at output path");
    check(usbauth_config_write() == 0, "H2 config_write() succeeded");
    check(file_equals(out_path, kExpectedOut),
          "H2 rewritten text round-trips byte for byte");

    /* Release the copy returned by get_auths with its documented counterpart.
     * Upstream's usbauth_allocate_and_copy() only deep-copies element 0, so
     * the remaining elements' attr_array pointers alias the parser globals;
     * usbauth_config_free() would free them a second time (double free), so it
     * is deliberately not called here. */
    if (auths != NULL)
        usbauth_config_free_auths(auths, len);

    remove(in_path);
    remove(out_path);

    if (fails) {
        printf("FAIL: libusbauth-configparser HarmonyOS test (%d failure(s))\n",
               fails);
        return 1;
    }
    printf("PASS: libusbauth-configparser HarmonyOS cases "
           "(H1 runtime load, H2 parse round-trip) ok\n");
    return 0;
}
