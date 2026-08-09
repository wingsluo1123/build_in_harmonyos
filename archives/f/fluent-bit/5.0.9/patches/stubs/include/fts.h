#ifndef _FTS_H_
#define _FTS_H_

/* HarmonyOS stub: BSD fts(3) for musl-lacking environments.
   Based on BSD <fts.h> — provides minimal types for compilation. */

typedef struct __fts_ent FTSENT;
typedef struct __fts FTS;

/* FTS options for fts_open */
#define FTS_COMFOLLOW  0x0001
#define FTS_LOGICAL    0x0002
#define FTS_NOCHDIR    0x0004
#define FTS_NOSTAT     0x0008
#define FTS_PHYSICAL   0x0010
#define FTS_SEEDOT     0x0020
#define FTS_XDEV       0x0040
#define FTS_WHITEOUT   0x0080
#define FTS_OPTIONMASK 0x00FF

/* FTSINFO flags returned by fts_info field */
#define FTS_D          0x001
#define FTS_DC         0x002
#define FTS_DEFAULT    0x003
#define FTS_DNR        0x004
#define FTS_DOT        0x005
#define FTS_DP         0x006
#define FTS_ERR        0x007
#define FTS_F          0x008
#define FTS_INIT       0x009
#define FTS_NS         0x00a
#define FTS_NSOK       0x00b
#define FTS_SL         0x00c
#define FTS_SLNONE     0x00d

struct __fts_ent {
    char *fts_accpath;    /* access path */
    char *fts_path;       /* root path */
    int   fts_errno;      /* errno */
    char *fts_name;       /* filename */
    int   fts_info;       /* FTS_* flags */
    int   fts_level;      /* depth (-1 for root) */
    int   fts_flags;      /* private flags */
    char *fts_parentname; /* parent filename (non-standard, for compat) */
    void *fts_ent;        /* private pointer */
};

struct __fts {
    void *fts_cur;        /* current node */
    FTSENT *fts_array;    /* sorted array of entries */
    void *fts_priv;       /* private data */
    int   fts_options;    /* options passed to fts_open */
};

static inline FTS *fts_open(char * const *path_argv, int options,
                            int (*compar)(const FTSENT **, const FTSENT **)) {
    (void)path_argv; (void)options; (void)compar;
    return NULL;
}

static inline FTSENT *fts_read(FTS *ftsp) {
    (void)ftsp;
    return NULL;
}

static inline FTSENT *fts_children(FTS *ftsp, int options) {
    (void)ftsp; (void)options;
    return NULL;
}

static inline int fts_set(FTS *ftsp, FTSENT *f, int options) {
    (void)ftsp; (void)f; (void)options;
    return 0;
}

static inline int fts_close(FTS *ftsp) {
    (void)ftsp;
    return 0;
}
#endif
