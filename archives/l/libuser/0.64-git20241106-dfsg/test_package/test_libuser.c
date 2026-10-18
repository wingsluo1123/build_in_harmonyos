/* Consumer test for libuser — 6 groups calling the real library API.
 *
 * No mocks, no stubs: lu_start() really dlopens the packaged files/shadow
 * back ends (moduledir comes from LIBUSER_CONF, written by the test_package
 * recipe), lu_user_default()/lu_group_default() really fill entities, and
 * the entity/config accessors round-trip real values. Each group prints
 * exactly one "PASS:" line on success; the recipe counts those lines.
 */
#include <stdio.h>
#include <string.h>

#include <stdlib.h>

#include <libuser/config.h>
#include <libuser/entity.h>
#include <libuser/error.h>
#include <libuser/user.h>

#define TOTAL_GROUPS 6

static int passes = 0;
static int failures = 0;

#define CHECK(name, cond) \
    do { \
        if (cond) { \
            printf("PASS: %s\n", name); \
            passes++; \
        } else { \
            printf("FAIL: %s\n", name); \
            failures++; \
        } \
    } while (0)

int main(void)
{
    struct lu_error *error = NULL;
    struct lu_context *ctx;
    struct lu_ent *uent = NULL;
    struct lu_ent *gent = NULL;
    const char *mods;
    const char *uname;
    const char *gname;
    const char *moddir;
    int ok;

    /* Group 1: context startup loads the packaged back-end modules. */
    ctx = lu_start("hmbs-test", lu_user, "files shadow", "files shadow",
                   NULL, NULL, &error);
    CHECK("context_start", ctx != NULL);
    if (ctx == NULL) {
        const char *emsg = (error != NULL) ? lu_strerror(error) : "(no error struct)";
        int ecode = (error != NULL) ? (int)error->code : -1;
        const char *conf = getenv("LIBUSER_CONF");
        printf("DIAG: lu_start failed code=%d msg=%s\n", ecode, emsg ? emsg : "(null)");
        printf("DIAG: LIBUSER_CONF=%s\n", conf ? conf : "(unset)");
        if (conf != NULL) {
            FILE *f = fopen(conf, "r");
            if (f != NULL) {
                char buf[512];
                printf("DIAG: conf head:\n");
                while (fgets(buf, sizeof(buf), f) != NULL)
                    printf("DIAG: | %s", buf);
                fclose(f);
            } else {
                printf("DIAG: conf unreadable\n");
            }
        }
        printf("RESULT: %d/%d passed\n", passes, TOTAL_GROUPS);
        return 1;
    }

    /* Group 2: the requested modules are really loaded. */
    mods = lu_get_modules(ctx);
    CHECK("modules_loaded",
          mods != NULL && strstr(mods, "files") != NULL);

    /* Group 3: user defaults for a regular account. */
    uent = lu_ent_new();
    ok = (uent != NULL) && lu_user_default(ctx, "hmbsuser", 0, uent);
    uname = ok ? lu_ent_get_first_string(uent, LU_USERNAME) : NULL;
    CHECK("user_default",
          ok && uname != NULL && strcmp(uname, "hmbsuser") == 0);

    /* Group 4: group defaults. */
    gent = lu_ent_new();
    ok = (gent != NULL) && lu_group_default(ctx, "hmbsgroup", 0, gent);
    gname = ok ? lu_ent_get_first_string(gent, LU_GROUPNAME) : NULL;
    CHECK("group_default",
          ok && gname != NULL && strcmp(gname, "hmbsgroup") == 0);

    /* Group 5: entity id attribute round-trip through the library. */
    if (uent != NULL)
        lu_ent_set_id(uent, LU_UIDNUMBER, (id_t) 12345);
    CHECK("ent_id_roundtrip",
          uent != NULL
          && lu_ent_get_first_id(uent, LU_UIDNUMBER) == (id_t) 12345);

    /* Group 6: config plumbing honors LIBUSER_CONF (moduledir readable). */
    moddir = lu_cfg_read_single(ctx, "defaults/moduledir", NULL);
    CHECK("config_moduledir",
          moddir != NULL && strlen(moddir) > 0);

    if (uent != NULL)
        lu_ent_free(uent);
    if (gent != NULL)
        lu_ent_free(gent);
    lu_end(ctx);

    printf("RESULT: %d/%d passed\n", passes, TOTAL_GROUPS);
    return failures == 0 ? 0 : 1;
}
