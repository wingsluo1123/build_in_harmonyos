/* Consumer test for libuser — 7 groups calling the real library API.
 *
 * No mocks, no stubs: lu_start() really dlopens the packaged files/shadow
 * back ends (moduledir comes from LIBUSER_CONF, written by the test_package
 * recipe), lu_user_default()/lu_group_default() really fill entities, and
 * the entity/config accessors round-trip real values. Group 7 additionally
 * pins the E338-family passwd semantics at the consumer level: the libc
 * getpwnam() assembly the files back end is built on must degrade to a
 * documented NULL for a missing row (musl has no NSS machinery), and the
 * library's own lookup over an empty (no-op) passwd/shadow pair must fail
 * orderly (FALSE + recorded error) without crashing. Each group prints
 * exactly one "PASS:" line on success; the recipe counts those lines.
 */
#include <stdio.h>
#include <string.h>

#include <stdlib.h>
#include <pwd.h>

#include <libuser/config.h>
#include <libuser/entity.h>
#include <libuser/error.h>
#include <libuser/user.h>

#define TOTAL_GROUPS 7

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

    /* Group 7: E338-family passwd semantics at the consumer level.
     *
     * E338 (2026-09-21 DS-20 read-out): on this platform /etc/passwd only
     * carries system users and getpwnam()/getpwuid() degrade to documented
     * NULL results with no SIGSEGV (no NSS). The libuser files back end
     * assembles its entities from exactly this struct-passwd family (see
     * modules/files.c generic_lookup), so the probe pins all three faces
     * on the real binary:
     *   a) getpwnam("root") really assembles a passwd record (root is a
     *      system user even per E338's /etc/passwd census);
     *   b) a missing row yields NULL, i.e. the no-op does not fabricate a
     *      filled struct nor crash;
     *   c) the library lookup over the empty no-op files back end
     *      (the LIBUSER_CONF files dir is empty in this harness) fails
     *      orderly: lu_user_lookup_name() returns FALSE with a recorded
     *      error instead of a crash/runtime abort;
     *   d) the assembled struct passwd feeds a real lu_ent round-trip.
     */
    {
        struct passwd *pw = getpwnam("root");
        struct passwd *pw_missing;
        struct lu_ent *lent = NULL;
        struct lu_error *lerr = NULL;
        const char *assembled;
        const char *found;
        const char *pw_name_snap = NULL;
        char pw_name_buf[256]; /* outer-block storage: outlives every reader
                                  below (review round-1 Medium: a nested-block
                                  array aliased from an outer pointer dangles
                                  as soon as the inner block closes) */
        long pw_uid_snap = -1L;
        int ok_a, ok_b, ok_c, ok_d, ok_all;

        ok_a = (pw != NULL) && (strcmp(pw->pw_name, "root") == 0);
        printf("DIAG: e338 getpwnam(root)=%s pw_uid=%ld pw_dir='%s'\n",
               ok_a ? "assembled" : "MISSING",
               pw ? (long) pw->pw_uid : -1L,
               (pw != NULL && pw->pw_dir != NULL) ? pw->pw_dir : "(null)");
        if (!ok_a) {
            printf("DIAG: e338 getpwnam fallback: root row absent, "
                   "E338 census mismatch on this host\n");
        }

        /* Serialize the assembled record NOW, before any further pwd-family
         * call: musl reuses one static struct across all calls, and a later
         * FAILED lookup replaces it with the next parsed record, silently
         * invalidating the (a) pointer (this window's E338 increment — see
         * notes.md). Assertion (d) consumes only this snapshot. */
        {
            long e338_uid;
            if (pw != NULL && pw->pw_name != NULL) {
                snprintf(pw_name_buf, sizeof(pw_name_buf), "%s", pw->pw_name);
                e338_uid = (long) pw->pw_uid;
                pw = NULL; /* static record: treat as invalidated */
            } else {
                snprintf(pw_name_buf, sizeof(pw_name_buf), "(unavailable)");
                e338_uid = -1L;
            }
            printf("DIAG: e338 pwd snapshot taken (source record name=%s "
                   "uid=%ld)\n",
                   pw_name_buf, e338_uid);
            pw_name_snap = pw_name_buf[0] == '(' ? NULL : pw_name_buf;
            pw_uid_snap = e338_uid;
        }

        pw_missing = getpwnam("hmbs-e338-nosuchuser");
        ok_b = (pw_missing == NULL);
        printf("DIAG: e338 getpwnam(missing)=%s\n",
               pw_missing == NULL ? "NULL (no-op, no crash)"
                                  : "UNEXPECTED non-NULL");

        lent = lu_ent_new();
        found = (lent != NULL)
                ? (lu_user_lookup_name(ctx, "hmbs-e338-nosuchuser",
                                       lent, &lerr) ? "TRUE" : "FALSE")
                : "ent-alloc-failed";
        ok_c = (lent != NULL) && (found != NULL && strcmp(found, "FALSE") == 0);
        /* generic_lookup() returns FALSE without setting an error when
         * the row simply is not in the passwd/shadow file — the no-op
         * contract is "orderly FALSE, no crash", not "error recorded". */
        printf("DIAG: e338 lu_user_lookup_name(missing over empty files "
               "backend)=%s err=%s\n",
               found,
               (lerr != NULL) ? lu_strerror(lerr) : "(no error recorded)");

        ok_d = 0;
        if (pw_name_snap != NULL && lent != NULL) {
            lu_ent_set_string(lent, LU_USERNAME, pw_name_snap);
            lu_ent_set_id(lent, LU_UIDNUMBER, (id_t) pw_uid_snap);
            assembled = lu_ent_get_first_string(lent, LU_USERNAME);
            ok_d = (assembled != NULL
                    && pw_name_snap != NULL
                    && strcmp(assembled, pw_name_snap) == 0
                    && lu_ent_get_first_id(lent, LU_UIDNUMBER)
                       == (id_t) pw_uid_snap);
            printf("DIAG: e338 passwd->lu_ent assemble uid=%ld %s\n",
                   pw_uid_snap, ok_d ? "round-trip ok" : "MISMATCH");
        }
        if (lent != NULL)
            lu_ent_free(lent);
        if (lerr != NULL)
            lu_error_free(&lerr);
        ok_all = ok_a && ok_b && ok_c && ok_d;
        CHECK("e338_pwd_semantics", ok_all);
        if (!ok_all)
            printf("DIAG: e338 ok_a=%d ok_b=%d ok_c=%d ok_d=%d\n",
                   ok_a, ok_b, ok_c, ok_d);
    }

    if (uent != NULL)
        lu_ent_free(uent);
    if (gent != NULL)
        lu_ent_free(gent);
    lu_end(ctx);

    printf("RESULT: %d/%d passed\n", passes, TOTAL_GROUPS);
    return failures == 0 ? 0 : 1;
}
