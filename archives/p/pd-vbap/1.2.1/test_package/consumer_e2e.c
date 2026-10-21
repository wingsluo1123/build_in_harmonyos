/* pd-vbap OHOS consumer end-to-end test.
 *
 * Acts as a Pd plugin host on top of libpd: it loads the three built externals
 * (vbap / rvbap / define_loudspeakers) exactly the way a Pd host does, then
 * drives them through a patch and checks the resulting VBAP gain distribution.
 *
 *   1. dlopen(libpd.so, RTLD_GLOBAL) + dlsym of the libpd C API
 *      (deliberately no link-time dependency: on musl/OHOS a DT_NEEDED libpd
 *      is not part of the dlopen() global symbol scope, so an external
 *      relocating against gensym()/pd_error() would fail to load)
 *   2. dlopen each <name>.pd_linux + dlsym <name>_setup() + call it
 *   3. open the consumer patch ([r lssetup] -> [vbap] -> [s gains])
 *   4. loudspeaker setup + panning direction -> verify energy conservation and
 *      nearest-speaker concentration of the gain vector
 *   5. the Pd console must stay clean during load and run
 *
 * usage: consumer_e2e <external_dir> <patch_dir> <libpd.so>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <math.h>
#include <z_libpd.h>

#define MAX_SPK 8

/* ---------- libpd C API, resolved at runtime ---------- */

struct libpd_api {
    int   (*init)(void);
    int   (*init_audio)(int, int, int);
    void *(*openfile)(const char *, const char *);
    void  (*closefile)(void *);
    void *(*bind)(const char *);
    int   (*bang)(const char *);
    int   (*float_msg)(const char *, float);
    int   (*start_message)(int);
    void  (*add_float)(float);
    int   (*finish_message)(const char *, const char *);
    void  (*set_printhook)(const t_libpd_printhook);
    void  (*set_listhook)(const t_libpd_listhook);
    float (*get_float)(t_atom *);
    int   (*is_float)(t_atom *);
};
static struct libpd_api L;

#define LOAD_SYM(handle, field, name)                                  \
    do {                                                               \
        *(void **)(&L.field) = dlsym(handle, name);                    \
        if (!L.field) {                                                \
            fprintf(stderr, "libpd symbol not found: %s (%s)\n",       \
                    name, dlerror());                                  \
            /* boolean convention of load_libpd(): 0 == failure (the   \
             * caller tests !load_libpd()); any non-zero would be      \
             * mistaken for success. */                                \
            return 0;                                                  \
        }                                                              \
    } while (0)

static int load_libpd(const char *so) {
    void *h = dlopen(so, RTLD_NOW | RTLD_GLOBAL);
    if (!h) {
        fprintf(stderr, "dlopen(%s): %s\n", so, dlerror());
        return 0;
    }
    printf("  [PASS] dlopen %s (RTLD_NOW|RTLD_GLOBAL)\n", so);
    LOAD_SYM(h, init,           "libpd_init");
    LOAD_SYM(h, init_audio,     "libpd_init_audio");
    LOAD_SYM(h, openfile,       "libpd_openfile");
    LOAD_SYM(h, closefile,      "libpd_closefile");
    LOAD_SYM(h, bind,           "libpd_bind");
    LOAD_SYM(h, bang,           "libpd_bang");
    LOAD_SYM(h, float_msg,      "libpd_float");
    LOAD_SYM(h, start_message,  "libpd_start_message");
    LOAD_SYM(h, add_float,      "libpd_add_float");
    LOAD_SYM(h, finish_message, "libpd_finish_message");
    LOAD_SYM(h, set_printhook,  "libpd_set_printhook");
    LOAD_SYM(h, set_listhook,   "libpd_set_listhook");
    LOAD_SYM(h, get_float,      "libpd_get_float");
    LOAD_SYM(h, is_float,       "libpd_is_float");
    return 1;
}

/* ---------- bookkeeping ---------- */

static float g_gain[MAX_SPK];
static int   g_seen[MAX_SPK];
static int   g_pd_errors = 0;
static int   checks = 0;
static int   failures = 0;

static void printhook(const char *s) {
    printf("    [pd] %s\n", s);
    if (strstr(s, "couldn't create") || strstr(s, "can't load") ||
        strstr(s, "error") || strstr(s, "failed"))
        g_pd_errors++;
}

static void listhook(const char *recv, int argc, t_atom *argv) {
    /* [vbap] banged emits one "speakerIndex gain" list per speaker on outlet 0 */
    if (strcmp(recv, "gains") != 0 || argc < 2) return;
    if (!L.is_float(argv) || !L.is_float(argv + 1)) return;
    {
        int idx = (int)L.get_float(argv);
        float val = L.get_float(argv + 1);
        if (idx >= 0 && idx < MAX_SPK) {
            g_gain[idx] = val;
            g_seen[idx] = 1;
        }
    }
}

/* ---------- helpers ---------- */

static void check(int cond, const char *what) {
    checks++;
    if (cond) {
        printf("  [PASS] %s\n", what);
    } else {
        failures++;
        printf("  [FAIL] %s\n", what);
    }
}

static void reset_gains(void) {
    memset(g_gain, 0, sizeof(g_gain));
    memset(g_seen, 0, sizeof(g_seen));
}

/* dlopen <dir>/<name>.pd_linux, call its <name>_setup() entry point */
static void load_external(const char *dir, const char *name) {
    char path[2048];
    char sym[256];
    void *h;
    typedef void (*setup_t)(void);
    setup_t setup_fn;

    snprintf(path, sizeof(path), "%s/%s.pd_linux", dir, name);
    h = dlopen(path, RTLD_NOW | RTLD_GLOBAL);
    if (!h) {
        checks++; failures++;
        printf("  [FAIL] dlopen %s: %s\n", path, dlerror());
        return;
    }
    snprintf(sym, sizeof(sym), "%s_setup", name);
    setup_fn = (setup_t)dlsym(h, sym);
    if (!setup_fn) {
        checks++; failures++;
        printf("  [FAIL] dlsym %s: %s\n", sym, dlerror());
        return;
    }
    setup_fn();
    checks++;
    printf("  [PASS] dlopen %s + dlsym %s + setup()\n", path, sym);
}

/* send "define_loudspeakers <args...>" to the patch's [r lssetup] */
static void send_setup(const float *args, int n) {
    int i;
    L.start_message(n);
    for (i = 0; i < n; i++) L.add_float(args[i]);
    L.finish_message("lssetup", "define_loudspeakers");
}

static int n_seen(void) {
    int i, n = 0;
    for (i = 0; i < MAX_SPK; i++) if (g_seen[i]) n++;
    return n;
}

static double energy(int n) {
    int i;
    double e = 0.0;
    for (i = 0; i < n; i++) e += (double)g_gain[i] * g_gain[i];
    return e;
}

static int peak_index(int n) {
    int i, best = 0;
    for (i = 1; i < n; i++) if (g_gain[i] > g_gain[best]) best = i;
    return best;
}

static void print_gains(const char *label, int n) {
    int i;
    printf("    %s gains =", label);
    for (i = 0; i < n; i++) printf(" %+.4f", g_gain[i]);
    printf("  (energy %.4f, peak speaker %d)\n", energy(n), peak_index(n));
}

/* ---------- main ---------- */

int main(int argc, char **argv) {
    const char *extdir, *pdir, *libpd_so;
    void *patch;
    float a2[3], a5[6];
    float azi[3];
    float pair[3][2];
    int i;

    if (argc < 4) {
        fprintf(stderr, "usage: %s <external_dir> <patch_dir> <libpd.so>\n", argv[0]);
        return 2;
    }
    extdir = argv[1];
    pdir = argv[2];
    libpd_so = argv[3];

    printf("-- 0) Pd engine (libpd)\n");
    if (!load_libpd(libpd_so)) {
        printf("\nchecks=0 failures=1\nRESULT: FAIL\n");
        return 1;
    }
    L.set_printhook(printhook);
    L.set_listhook(listhook);
    if (L.init() != 0) {            /* libpd_init() returns 0 on success */
        fprintf(stderr, "libpd_init() failed\n");
        return 2;
    }
    if (L.init_audio(0, 5, 48000) != 0) {
        fprintf(stderr, "libpd_init_audio(0,5,48000) failed\n");
        return 2;
    }
    L.bind("gains");
    printf("  [PASS] libpd_init + libpd_init_audio(0 in / 5 out @ 48000 Hz) + bind(\"gains\")\n");

    /* 1) external loading */
    printf("-- 1) load built Pd externals\n");
    load_external(extdir, "vbap");
    load_external(extdir, "rvbap");
    load_external(extdir, "define_loudspeakers");

    /* 2) consumer patch */
    printf("-- 2) open consumer patch\n");
    patch = L.openfile("pdvbap_consumer.pd", pdir);
    check(patch != NULL, "libpd_openfile(pdvbap_consumer.pd)");
    if (!patch) {
        printf("\nchecks=%d failures=%d\nRESULT: FAIL\n", checks, failures);
        return 1;
    }

    /* 3) 2D pair (-45 / +45), panning sweep */
    printf("-- 3) 2D pair setup (2 -45 45) + azimuth sweep\n");
    a2[0] = 2; a2[1] = -45; a2[2] = 45;
    send_setup(a2, 3);
    azi[0] = -45.0f; azi[1] = 0.0f; azi[2] = 45.0f;
    for (i = 0; i < 3; i++) {
        char label[64];
        reset_gains();
        L.float_msg("azim", azi[i]);
        L.bang("bang");
        snprintf(label, sizeof(label), "azimuth %+.0f", azi[i]);
        print_gains(label, 2);
        pair[i][0] = g_gain[0];
        pair[i][1] = g_gain[1];
        check(g_seen[0] && g_seen[1], "both speakers report a gain");
    }
    for (i = 0; i < 3; i++) {
        char label[96];
        double e = (double)pair[i][0] * pair[i][0] + (double)pair[i][1] * pair[i][1];
        snprintf(label, sizeof(label), "energy conservation at azimuth %+.0f", azi[i]);
        check(fabs(e - 1.0) < 0.02, label);
    }
    check(pair[0][0] > pair[0][1], "azimuth -45 favours speaker 0");
    check(fabs(pair[1][0] - pair[1][1]) < 0.05, "azimuth 0 splits equally (0.7071/0.7071)");
    check(pair[2][1] > pair[2][0], "azimuth +45 favours speaker 1");

    /* 4) 5.1 setup, panning to the centre speaker */
    printf("-- 4) 5.1 setup (2 -135 -45 0 45 135), azimuth 0\n");
    a5[0] = 2; a5[1] = -135; a5[2] = -45; a5[3] = 0; a5[4] = 45; a5[5] = 135;
    send_setup(a5, 6);
    reset_gains();
    L.float_msg("azim", 0.0f);
    L.bang("bang");
    print_gains("5.1 @ 0 deg", 5);
    check(n_seen() == 5, "all five speakers report a gain");
    check(peak_index(5) == 2, "peak gain on centre speaker (index 2)");
    check(fabs(energy(5) - 1.0) < 0.02, "energy conservation over five speakers");

    reset_gains();
    L.float_msg("azim", -135.0f);
    L.bang("bang");
    print_gains("5.1 @ -135 deg", 5);
    check(peak_index(5) == 0, "peak gain on speaker 0 at azimuth -135");

    /* 5) console cleanliness */
    printf("-- 5) Pd console\n");
    check(g_pd_errors == 0, "no Pd console errors during load/run");

    L.closefile(patch);
    printf("\nchecks=%d failures=%d\n", checks, failures);
    printf("RESULT: %s\n", failures == 0 ? "PASS" : "FAIL");
    return failures == 0 ? 0 : 1;
}
